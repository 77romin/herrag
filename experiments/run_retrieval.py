# -*- coding: utf-8 -*-
"""
검색 단계 실험 하네스 (LLM 심사 없이 결정론적으로 측정)

정답 청크를 앵커 문자열로 라벨링해 두고, 청킹 방식 / 임베딩 모델 / 검색 방식별로
"정답 청크가 몇 위에 오는가"를 잰다. Ragas 는 LLM 심사라 실행마다 흔들리지만
이 지표는 같은 입력에 항상 같은 값이 나온다.
"""
import os, sys, json, math, hashlib, re
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\SSAFY\chatbot-project_lab")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "servers"))

from dotenv import load_dotenv
load_dotenv(ROOT / "servers" / ".env")

from langchain_text_splitters import (
    RecursiveCharacterTextSplitter, MarkdownHeaderTextSplitter)
from langchain_openai import OpenAIEmbeddings
from rank_bm25 import BM25Okapi
import numpy as np

GUIDE = ROOT / "data" / "SSAFY_GUIDE.md"
OUT = ROOT / "experiments" / "results"
CACHE = ROOT / "experiments" / "results" / "_emb_cache.json"

# ---------------------------------------------------------------- 테스트셋
QUESTIONS = json.loads((ROOT / "servers" / "test_cases.json").read_text(encoding="utf-8"))
# 각 질문의 정답이 실제로 적혀 있는 위치를 가리키는 앵커 문자열.
# 원문에서 전부 1회만 등장하는 것으로 확인했다.
ANCHORS = [
    "예비군/민방위 등", "본인 결혼 (5일)", "지각/조퇴/외출 3회", "09:00 ~ 18:00",
    "외부 음식 반입 및 취식 금지", "16,500", "봉인", "6회 이상 Pass",
    "Job-Fair 시작 후 3~4주차", "18:30",
]

# ---------------------------------------------------------------- 청킹 설정
def split_recursive(text, size, overlap=50):
    sp = RecursiveCharacterTextSplitter(
        chunk_size=size, chunk_overlap=overlap,
        separators=["\n\n", "\n", ".", " ", ""], length_function=len)
    return sp.split_text(text)

def split_markdown_aware(text, size=500, overlap=50):
    """헤더로 먼저 자르고, 각 조각 앞에 헤더 경로를 붙인 뒤 크기로 재분할."""
    md = MarkdownHeaderTextSplitter(
        headers_to_split_on=[("#", "h1"), ("##", "h2"), ("###", "h3")],
        strip_headers=False)
    parts = md.split_text(text)
    sp = RecursiveCharacterTextSplitter(
        chunk_size=size, chunk_overlap=overlap,
        separators=["\n\n", "\n", ".", " ", ""], length_function=len)
    out = []
    for p in parts:
        path = " > ".join(p.metadata.get(k, "") for k in ("h1", "h2", "h3") if p.metadata.get(k))
        for c in sp.split_text(p.page_content):
            out.append(f"[{path}]\n{c}" if path else c)
    return out

CONFIGS = {
    "recursive-300":  lambda t: split_recursive(t, 300),
    "recursive-500":  lambda t: split_recursive(t, 500),   # 현재 운영값
    "recursive-1000": lambda t: split_recursive(t, 1000),
    "markdown-500":   lambda t: split_markdown_aware(t, 500),
}

# ---------------------------------------------------------------- 임베딩(캐시)
_cache = json.loads(CACHE.read_text(encoding="utf-8")) if CACHE.exists() else {}

def embed(texts, model):
    key_of = lambda s: hashlib.sha1((model + "\x00" + s).encode("utf-8")).hexdigest()
    todo = [t for t in texts if key_of(t) not in _cache]
    if todo:
        cli = OpenAIEmbeddings(model=model, api_key=os.getenv("API_KEY"),
                               base_url=os.getenv("base_url"))
        for i in range(0, len(todo), 64):
            batch = todo[i:i + 64]
            for t, v in zip(batch, cli.embed_documents(batch)):
                _cache[key_of(t)] = v
        CACHE.write_text(json.dumps(_cache), encoding="utf-8")
    return np.array([_cache[key_of(t)] for t in texts], dtype=np.float64)

# ---------------------------------------------------------------- 검색 방식
def tok(s):
    return re.sub(r"[^\w\s]", " ", s).split()

def dense_rank(qv, M):
    """단위벡터 가정. 코사인 내림차순 = L2 오름차순 (순서 동일)."""
    return np.argsort(-(M @ qv))

def bm25_rank(chunks, q):
    bm = BM25Okapi([tok(c) for c in chunks])
    return np.argsort(-bm.get_scores(tok(q)))

def rrf(rank_lists, weights, c=60):
    """LangChain EnsembleRetriever 와 같은 가중 RRF."""
    score = {}
    for order, w in zip(rank_lists, weights):
        for r, idx in enumerate(order, start=1):
            score[idx] = score.get(idx, 0.0) + w / (c + r)
    return [i for i, _ in sorted(score.items(), key=lambda kv: -kv[1])]

def metrics(gold_ranks):
    n = len(gold_ranks)
    out = {f"recall@{k}": sum(1 for r in gold_ranks if r <= k) / n for k in (1, 3, 5, 10)}
    out["MRR"] = sum(1.0 / r for r in gold_ranks) / n
    return out

# ---------------------------------------------------------------- 실행
def run():
    text = GUIDE.read_text(encoding="utf-8")
    qs = [q["question"] for q in QUESTIONS]
    report = {}

    for cfg_name, fn in CONFIGS.items():
        chunks = fn(text)
        gold = []
        for a in ANCHORS:
            hit = [i for i, c in enumerate(chunks) if a in c]
            gold.append(hit[0] if hit else -1)
        lens = [len(c) for c in chunks]
        info = {
            "chunks": len(chunks),
            "len_min": min(lens), "len_med": int(np.median(lens)), "len_max": max(lens),
            "over_size": sum(1 for L in lens if L > (1000 if "1000" in cfg_name else
                                                     300 if "300" in cfg_name else 500)),
            "anchor_missing": sum(1 for g in gold if g < 0),
        }

        for model in (["text-embedding-3-small", "text-embedding-3-large"]
                      if cfg_name == "recursive-500" else ["text-embedding-3-small"]):
            M = embed(chunks, model)
            M = M / np.linalg.norm(M, axis=1, keepdims=True)
            Q = embed(qs, model)
            Q = Q / np.linalg.norm(Q, axis=1, keepdims=True)

            d_ranks, b_ranks, h_ranks, detail = [], [], [], []
            for i, q in enumerate(qs):
                g = gold[i]
                dorder = list(dense_rank(Q[i], M))
                border = list(bm25_rank(chunks, q))
                horder = rrf([border, dorder], [0.5, 0.5])
                dr = dorder.index(g) + 1
                br = border.index(g) + 1
                hr = horder.index(g) + 1
                d_ranks.append(dr); b_ranks.append(br); h_ranks.append(hr)
                cos = float(M[g] @ Q[i])
                detail.append({
                    "q": q[:40], "gold_chunk": g,
                    "dense": dr, "bm25": br, "hybrid": hr,
                    "cos": round(cos, 4),
                    "relevance_l2": round(1 - (2 - 2 * cos) / math.sqrt(2), 4),
                    "relevance_cos": round(cos, 4),
                })
            tag = f"{cfg_name}|{model.split('-')[-1]}"
            report[tag] = {
                "info": info,
                "dense": metrics(d_ranks),
                "bm25": metrics(b_ranks),
                "hybrid": metrics(h_ranks),
                "detail": detail,
            }
            print(f"\n### {tag}  청크 {info['chunks']}개 "
                  f"(len {info['len_min']}/{info['len_med']}/{info['len_max']})")
            for name in ("dense", "bm25", "hybrid"):
                m = report[tag][name]
                print(f"  {name:7s} R@1 {m['recall@1']:.2f}  R@3 {m['recall@3']:.2f}  "
                      f"R@5 {m['recall@5']:.2f}  R@10 {m['recall@10']:.2f}  MRR {m['MRR']:.3f}")

    (OUT / "retrieval_report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"\n저장: {OUT / 'retrieval_report.json'}")
    return report

if __name__ == "__main__":
    run()
