# -*- coding: utf-8 -*-
"""
F207 ① "수집한 문서에 적합한 내용 추출 방식" 실험

같은 내용을 세 가지 표현으로 두고 검색 품질을 비교한다.
  md_raw     현행. 마크다운 표에 <br>/&nbsp;/백틱이 그대로 남아 한 줄이 1,083자
  txt_plain  제공된 평문판. <br>가 실제 개행으로 풀려 있음
  md_norm    직접 만든 정규화. <br>→개행, 엔티티 제거, 표 헤더를 각 행 앞에 주입
"""
import os, sys, json, re
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\SSAFY\chatbot-project_lab")
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv(ROOT / "servers" / ".env")
sys.path.insert(0, str(ROOT / "experiments"))
from run_retrieval import embed, QUESTIONS, ANCHORS, split_recursive, tok, rrf, metrics
from rank_bm25 import BM25Okapi

OUT = ROOT / "experiments" / "results"
MD = (ROOT / "data" / "SSAFY_GUIDE.md").read_text(encoding="utf-8")
TXT = (ROOT / "clients" / "sample_data" / "SSAFY_GUIDE.txt").read_text(encoding="utf-8")

def normalize_markdown(text: str) -> str:
    """표를 사람이 읽는 문장에 가깝게 편다. 표 헤더를 각 데이터 행에 붙여 맥락을 남긴다."""
    out, header = [], None
    for line in text.split("\n"):
        s = line.replace("<br>", "\n").replace("&nbsp;", " ")
        s = s.replace("`", "").replace("**", "")
        if re.match(r"^\s*\|[\s:\-|]+\|\s*$", s):       # 표 구분선은 버린다
            continue
        if s.strip().startswith("|"):
            cells = [c.strip() for c in s.strip().strip("|").split("|")]
            if header is None:
                header = cells                            # 첫 행을 헤더로 기억
                out.append(" / ".join(cells))
                continue
            pairs = []
            for i, c in enumerate(cells):
                if not c:
                    continue
                label = header[i] if i < len(header) and header[i] else ""
                pairs.append(f"{label}: {c}" if label else c)
            out.append("\n".join(pairs))
        else:
            if not s.strip():
                header = None                             # 빈 줄이면 표가 끝난 것으로 본다
            out.append(s)
    return "\n".join(out)

VARIANTS = {
    "md_raw":    MD,
    "txt_plain": TXT,
    "md_norm":   normalize_markdown(MD),
}

qs = [q["question"] for q in QUESTIONS]
QV = embed(qs, "text-embedding-3-small"); QV /= np.linalg.norm(QV, axis=1, keepdims=True)

report = {}
for name, text in VARIANTS.items():
    chunks = split_recursive(text, 500)
    gold, missing = [], []
    for a in ANCHORS:
        hit = [i for i, c in enumerate(chunks) if a in c]
        gold.append(hit[0] if hit else -1)
        if not hit:
            missing.append(a)
    if missing:
        print(f"  ! {name}: 앵커 미발견 {missing}")
    M = embed(chunks, "text-embedding-3-small"); M /= np.linalg.norm(M, axis=1, keepdims=True)
    BM = BM25Okapi([tok(c) for c in chunks])
    lens = [len(c) for c in chunks]
    d, b, h = [], [], []
    for i in range(len(qs)):
        if gold[i] < 0:
            continue
        do = list(np.argsort(-(M @ QV[i])))
        bo = list(np.argsort(-BM.get_scores(tok(qs[i]))))
        ho = rrf([bo, do], [0.5, 0.5])
        d.append(do.index(gold[i]) + 1)
        b.append(bo.index(gold[i]) + 1)
        h.append(ho.index(gold[i]) + 1)
    report[name] = dict(
        chars=len(text), chunks=len(chunks),
        len_med=int(np.median(lens)), len_max=max(lens),
        max_source_line=max(len(l) for l in text.split("\n")),
        dense=metrics(d), bm25=metrics(b), hybrid=metrics(h),
        gold_ranks_dense=d, gold_ranks_hybrid=h)
    print(f"\n### {name}  {len(text):,}자 / 청크 {len(chunks)}개 "
          f"(median {int(np.median(lens))}, 원문 최장 줄 {report[name]['max_source_line']:,}자)")
    for kind in ("dense", "bm25", "hybrid"):
        m = report[name][kind]
        print(f"  {kind:7s} R@1 {m['recall@1']:.2f}  R@3 {m['recall@3']:.2f}  "
              f"R@5 {m['recall@5']:.2f}  MRR {m['MRR']:.3f}")

(OUT / "extraction_report.json").write_text(json.dumps(report, ensure_ascii=False, indent=2),
                                            encoding="utf-8")
(ROOT / "experiments" / "corpus" / "SSAFY_GUIDE_normalized.md").write_text(
    VARIANTS["md_norm"], encoding="utf-8")
print(f"\n저장: {OUT / 'extraction_report.json'}")
