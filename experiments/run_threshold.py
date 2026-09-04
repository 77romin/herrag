# -*- coding: utf-8 -*-
"""
F208 ② "유사도 기준이 결과에 미친 영향" 실험

1) Chroma 의 hnsw:space 미지정(L2) 상태에서 relevance_score 가 어떻게 계산되는지
2) 그 점수에 임계값을 걸면 무엇이 통과하고 무엇이 잘리는지
3) space 를 cosine 으로 바꾸면 점수와 순위가 각각 어떻게 달라지는지
"""
import os, sys, json, math, hashlib, re
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\SSAFY\chatbot-project_lab")
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv(ROOT / "servers" / ".env")
from langchain_text_splitters import RecursiveCharacterTextSplitter

sys.path.insert(0, str(ROOT / "experiments"))
from run_retrieval import embed, ANCHORS, QUESTIONS, split_recursive

OUT = ROOT / "experiments" / "results"
text = (ROOT / "data" / "SSAFY_GUIDE.md").read_text(encoding="utf-8")
chunks = split_recursive(text, 500)
qs = [q["question"] for q in QUESTIONS]
gold = [next(i for i, c in enumerate(chunks) if a in c) for a in ANCHORS]

M = embed(chunks, "text-embedding-3-small"); M /= np.linalg.norm(M, axis=1, keepdims=True)
Q = embed(qs, "text-embedding-3-small");     Q /= np.linalg.norm(Q, axis=1, keepdims=True)

SQRT2 = math.sqrt(2)
rel_l2  = lambda cos: 1 - (2 - 2 * cos) / SQRT2   # Chroma l2(제곱L2) + LangChain 변환
rel_cos = lambda cos: cos                          # Chroma cosine + LangChain 변환

# ---------------------------------------------------------- 1) 순위 불변 확인
same = True
for i in range(len(qs)):
    cos = M @ Q[i]
    if list(np.argsort(-np.vectorize(rel_l2)(cos))) != list(np.argsort(-np.vectorize(rel_cos)(cos))):
        same = False
print(f"[1] L2 점수 기준 순위 == 코사인 점수 기준 순위 ? -> {same}")

# ---------------------------------------------------------- 2) 점수 분포
print("\n[2] 질문별 점수 분포 (l2 변환식 기준)")
print(f"{'Q':<30}{'1위':>8}{'5위':>8}{'정답':>8}{'정답순위':>9}{'1위-정답':>10}")
rows = []
for i, q in enumerate(qs):
    cos = M @ Q[i]
    order = np.argsort(-cos)
    r = list(order).index(gold[i]) + 1
    s1, s5, sg = rel_l2(cos[order[0]]), rel_l2(cos[order[4]]), rel_l2(cos[gold[i]])
    rows.append(dict(q=q, rank=r, top1=s1, top5=s5, goldscore=sg,
                     scores=[float(rel_l2(c)) for c in cos]))
    print(f"{q[:28]:<30}{s1:>8.4f}{s5:>8.4f}{sg:>8.4f}{r:>9}{s1-sg:>10.4f}")

allsc = np.array([s for r_ in rows for s in r_["scores"]])
print(f"\n전체 점수 범위: {allsc.min():.4f} ~ {allsc.max():.4f}   음수 비율 {100*(allsc<0).mean():.1f}%")

# ---------------------------------------------------------- 3) 임계값 스윕
print("\n[3] score_threshold 스윕 (k=5 로 자르기 전, 임계값만 적용)")
print(f"{'threshold':>10}{'통과 청크 평균':>14}{'정답 통과 질문수':>18}{'정답 차단 질문수':>18}")
sweep = []
for th in [0.00, 0.05, 0.10, 0.15, 0.20, 0.25]:
    passed, goldpass = [], 0
    for i, r_ in enumerate(rows):
        sc = np.array(r_["scores"])
        passed.append(int((sc >= th).sum()))
        if sc[gold[i]] >= th:
            goldpass += 1
    sweep.append(dict(threshold=th, avg_passed=float(np.mean(passed)),
                      gold_pass=goldpass, gold_blocked=len(rows) - goldpass))
    print(f"{th:>10.2f}{np.mean(passed):>14.1f}{goldpass:>18}{len(rows)-goldpass:>18}")

# ---------------------------------------------------------- 4) k 스윕
print("\n[4] k 값에 따른 정답 포함률 (dense 단독)")
for k in (3, 5, 8, 10):
    hit = sum(1 for i, r_ in enumerate(rows) if r_["rank"] <= k)
    print(f"  k={k:<3} 정답 포함 {hit}/10   컨텍스트 길이 평균 {k*340:,}자 내외")

(OUT / "threshold_report.json").write_text(json.dumps(
    dict(rank_invariant=same,
         score_min=float(allsc.min()), score_max=float(allsc.max()),
         negative_ratio=float((allsc < 0).mean()),
         per_question=[{k: v for k, v in r_.items() if k != "scores"} for r_ in rows],
         sweep=sweep), ensure_ascii=False, indent=2), encoding="utf-8")
print(f"\n저장: {OUT / 'threshold_report.json'}")
