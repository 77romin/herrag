# -*- coding: utf-8 -*-
"""3회 반복 Ragas 결과를 평균±표준편차로 집계한다."""
import sys, json, glob, re
from pathlib import Path
import pandas as pd, numpy as np

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(r"C:\SSAFY\chatbot-project_lab\experiments\results")
COLS = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
LABEL = {"A_baseline": "A 현행", "B_prompt_fix": "B 프롬프트만 수정",
         "C_hybrid+prompt": "C 하이브리드 검색 + 프롬프트"}

runs = {}
for f in glob.glob(str(OUT / "ragas_*.csv")):
    m = re.match(r"ragas_(.+?)(?:_r(\d))?\.csv$", Path(f).name)
    cond, r = m.group(1), m.group(2) or "1"
    df = pd.read_csv(f)
    runs.setdefault(cond, {})[r] = {c: float(df[c].mean()) for c in COLS if c in df}

agg = {}
print(f"{'조건':<30}" + "".join(f"{c[:14]:>18}" for c in COLS) + f"{'n':>4}")
for cond in ["A_baseline", "B_prompt_fix", "C_hybrid+prompt"]:
    if cond not in runs:
        continue
    vals = {c: [runs[cond][r][c] for r in sorted(runs[cond])] for c in COLS}
    agg[cond] = {c: dict(mean=float(np.mean(v)), std=float(np.std(v, ddof=1)) if len(v) > 1 else 0.0,
                         n=len(v), runs=v) for c, v in vals.items()}
    line = f"{LABEL[cond]:<30}"
    for c in COLS:
        a = agg[cond][c]
        line += f"{a['mean']:>11.3f}±{a['std']:.3f}"
    print(line + f"{agg[cond][COLS[0]]['n']:>4}")

print("\n변화량 (A 대비, 평균 기준)")
if "A_baseline" in agg:
    for cond in ["B_prompt_fix", "C_hybrid+prompt"]:
        if cond not in agg:
            continue
        line = f"{LABEL[cond]:<30}"
        for c in COLS:
            d = agg[cond][c]["mean"] - agg["A_baseline"][c]["mean"]
            pooled = max(agg[cond][c]["std"], agg["A_baseline"][c]["std"])
            sig = "유의" if abs(d) > 2 * pooled and abs(d) >= 0.05 else "노이즈"
            line += f"{d:>+11.3f}({sig[:2]})"
        print(line)

(OUT / "ragas_aggregate.json").write_text(json.dumps(agg, ensure_ascii=False, indent=2),
                                          encoding="utf-8")
print(f"\n저장: {OUT / 'ragas_aggregate.json'}")
