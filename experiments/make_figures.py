# -*- coding: utf-8 -*-
"""보고서용 그림 생성. 색은 dataviz 검증기(validate_palette.js)를 통과한 조합을 사용한다."""
import sys, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(r"C:\SSAFY\chatbot-project_lab\experiments\figures")
OUT.mkdir(exist_ok=True)

plt.rcParams.update({
    "font.family": "Malgun Gothic",
    "axes.unicode_minus": False,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "savefig.facecolor": "white",
})

C1, C2, C3 = "#008C72", "#C26A12", "#5560C4"     # 검증 통과 3계열
INK, MUTED, GRID = "#1B2A24", "#5E6862", "#DDE3DF"
DOWN, SOFT, BAND = "#A8452F", "#F1F4F0", "#E6ECE8"


def tidy(ax, ylab=None, xlab=None, grid="y"):
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    for s in ("left", "bottom"):
        ax.spines[s].set_color(GRID); ax.spines[s].set_linewidth(1)
    ax.tick_params(colors=MUTED, labelsize=9, length=3, width=1)
    if grid:
        ax.grid(axis=grid, color=GRID, linewidth=0.8, alpha=.9)
        ax.set_axisbelow(True)
    if ylab: ax.set_ylabel(ylab, color=MUTED, fontsize=9.5, labelpad=8)
    if xlab: ax.set_xlabel(xlab, color=MUTED, fontsize=9.5, labelpad=8)


def box(ax, x, y, w, h, label, sub=None, fc="white", ec=INK, lw=1.2, fs=10, tc=INK):
    ax.add_patch(FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc=fc, ec=ec, lw=lw, zorder=2))
    ax.text(x + w / 2, y + h * (0.62 if sub else 0.5), label, ha="center", va="center",
            fontsize=fs, color=tc, fontweight="bold", zorder=3)
    if sub:
        ax.text(x + w / 2, y + h * 0.26, sub, ha="center", va="center",
                fontsize=fs - 2, color=MUTED, zorder=3)


def arrow(ax, p0, p1, color=INK, lw=1.2, style="-|>", conn="arc3,rad=0"):
    ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle=style, mutation_scale=11,
                                 color=color, lw=lw, connectionstyle=conn, zorder=2))


def save(fig, name):
    fig.savefig(OUT / name, dpi=200, bbox_inches="tight", pad_inches=0.12)
    plt.close(fig)
    print("  ", name)


# ══════════════════ 그림 1. 호출 구조 ══════════════════
fig, ax = plt.subplots(figsize=(9.2, 4.0))
ax.set_xlim(0, 100); ax.set_ylim(0, 46); ax.axis("off")

box(ax, 1, 14, 13, 8, "브라우저", ":5500")
box(ax, 18, 12, 16, 12, "FastAPI", ":8000  ·  API 키 보관")
box(ax, 39, 15, 8, 6, "START", fs=9)
box(ax, 51, 27, 20, 8, "retrieve", "376 ms")
box(ax, 51, 2, 20, 8, "generate", "3,897 ms")
box(ax, 51, 38, 20, 6, "Chroma  (로컬 디스크)", fs=9)
box(ax, 78, 27, 21, 8, "임베딩 API", "text-embedding-3-small", fc=BAND, ec=C1, tc=C1)
box(ax, 78, 2, 21, 8, "Chat Completions", "in 1,120 / out 274 tok", fc=BAND, ec=C1, tc=C1)

arrow(ax, (14, 18), (17.4, 18))
ax.text(16, 11.2, "POST /chat", ha="center", fontsize=7.5, color=MUTED)
arrow(ax, (34, 18), (38.4, 18))
arrow(ax, (43, 21), (50.4, 31), conn="angle,angleA=90,angleB=180,rad=3")
ax.text(45.5, 27.5, "use_rag=true", ha="center", fontsize=7.5, color=MUTED)
arrow(ax, (43, 15), (50.4, 6), conn="angle,angleA=-90,angleB=180,rad=3")
ax.text(45.5, 9.5, "use_rag=false", ha="center", fontsize=7.5, color=MUTED)
arrow(ax, (61, 27), (61, 10.6), conn="arc3,rad=0")
ax.text(62.5, 18, "context 1,701자", fontsize=7.5, color=MUTED, va="center")
arrow(ax, (61, 35), (61, 37.4))
ax.text(62.5, 36.2, "벡터 검색", fontsize=7.5, color=MUTED, va="center")
arrow(ax, (71, 31), (77.4, 31), color=C1, lw=1.4)
arrow(ax, (71, 6), (77.4, 6), color=C1, lw=1.4)
ax.text(74.2, 32.6, "1회", ha="center", fontsize=7.5, color=C1, fontweight="bold")
ax.text(74.2, 7.6, "1회", ha="center", fontsize=7.5, color=C1, fontweight="bold")
ax.add_patch(Rectangle((76.5, 0.5), 23.5, 36.5, fill=False, ec=C1, lw=1,
                       ls=(0, (4, 4)), alpha=.55, zorder=1))
ax.text(88.2, 38.2, "외부 네트워크 · 프록시 → OpenAI", ha="center", fontsize=7.5,
        color=C1, fontweight="bold")
save(fig, "fig1_call_flow.png")

# ══════════════════ 그림 2. Ragas 지표 관계 ══════════════════
fig, ax = plt.subplots(figsize=(9.2, 4.2))
ax.set_xlim(0, 100); ax.set_ylim(0, 53); ax.axis("off")

# 파이프라인이 만들어 내는 네 가지 재료를 한 줄로 늘어놓는다.
nodes = [(2, "질문", "user_input", SOFT),
         (26, "검색된 컨텍스트", "retrieved_contexts", "white"),
         (50, "생성된 답변", "response", "white"),
         (74, "정답", "reference · 사람이 작성", SOFT)]
cx = {}
for x, name, sub, fc in nodes:
    box(ax, x, 38, 22, 9, name, sub, fc=fc, fs=10)
    cx[name] = x + 11
arrow(ax, (24, 42.5), (25.4, 42.5), color=MUTED)
arrow(ax, (48, 42.5), (49.4, 42.5), color=MUTED)
ax.text(24.7, 47.6, "검색", ha="center", fontsize=8, color=MUTED)
ax.text(48.7, 47.6, "생성", ha="center", fontsize=8, color=MUTED)

# 각 지표가 무엇과 무엇을 견주는지 괄호로 묶어 보인다.
brackets = [
    (30, "검색된 컨텍스트", "생성된 답변", "Faithfulness",
     "답변의 각 주장이 컨텍스트로 뒷받침되는가  ·  낮으면 지어낸 것", C1),
    (21, "질문", "생성된 답변", "AnswerRelevancy",
     "답변이 질문에 대한 답이 되는가  ·  낮으면 동문서답이거나 너무 짧음", C2),
    (12, "검색된 컨텍스트", "정답", "ContextRecall",
     "정답에 필요한 내용이 컨텍스트에 다 들어왔는가  ·  낮으면 검색이 놓침", C3),
    (3, "검색된 컨텍스트", "정답", "ContextPrecision",
     "관련 있는 청크가 위쪽 순위에 있는가  ·  낮으면 노이즈가 섞임", INK),
]
for y, a, b, name, desc, col in brackets:
    x0, x1 = sorted((cx[a], cx[b]))
    # 괄호는 위쪽 상자를 향해 열려야 한다. 끝이 위로 서고 가로선이 아래에 놓인다.
    ax.plot([x0, x0, x1, x1], [y + 5.2, y + 3.4, y + 3.4, y + 5.2],
            color=col, lw=1.6, solid_capstyle="round", zorder=3)
    ax.text((x0 + x1) / 2, y + 2.7, name, ha="center", va="top", fontsize=9.5,
            color=col, fontweight="bold")
    ax.text((x0 + x1) / 2, y + 0.8, desc, ha="center", va="top", fontsize=8, color=MUTED)
ax.text(2, 51.4, "앞의 두 지표는 생성 품질을, 뒤의 두 지표는 검색 품질을 잰다.",
        fontsize=8.5, color=INK, fontweight="bold")
save(fig, "fig2_ragas_metrics.png")

# ══════════════════ 그림 3. L2 변환과 음수 점수 ══════════════════
fig, ax = plt.subplots(figsize=(8.2, 4.0))
cos = np.linspace(0, 1, 400)
d = 2 - 2 * cos                       # Chroma 가 돌려주는 제곱 L2
score = 1 - d / math.sqrt(2)          # langchain-chroma 의 변환식
ax.axhspan(-0.5, 0, color=DOWN, alpha=.07, zorder=0)
ax.plot(cos, score, color=C1, lw=2.2, zorder=3)
ax.axhline(0, color=MUTED, lw=1, ls="--", zorder=2)
zero = 1 - math.sqrt(2) / 2
ax.plot([zero], [0], "o", ms=7, color=C1, mec="white", mew=1.6, zorder=4)
ax.annotate(f"코사인 {zero:.3f} 아래는 전부 음수", (zero, 0), (0.40, -0.24),
            fontsize=9, color=DOWN, fontweight="bold",
            arrowprops=dict(arrowstyle="-", color=DOWN, lw=1))
for c, s, lab, col in [(0.5734, 0.3967, "관측 최고  0.397", C1),
                       (0.0758, -0.3070, "관측 최저  -0.307", DOWN)]:
    ax.plot([c], [s], "o", ms=7, color=col, mec="white", mew=1.6, zorder=4)
    ax.annotate(lab, (c, s), (c + 0.05, s + 0.09), fontsize=9, color=col, fontweight="bold")
ax.set_xlim(0, 1); ax.set_ylim(-0.5, 1.05)
tidy(ax, "relevance_score  (1 - d/√2)", "두 벡터의 코사인 유사도", grid="y")
ax.text(0.02, 0.93, "score = 1 - d/√2,   d = 2 - 2*cos", fontsize=9,
        color=INK, family="Consolas")
save(fig, "fig3_l2_negative.png")

# ══════════════════ 그림 4. 청크 크기별 반응 ══════════════════
fig, ax = plt.subplots(figsize=(8.2, 4.0))
x = [300, 500, 1000]
series = [("dense (밀집 검색)", [0.867, 0.742, 0.646], C1, "o"),
          ("BM25 (어휘 검색)", [0.750, 0.867, 0.883], C2, "s"),
          ("hybrid (두 결과 결합)", [0.808, 0.850, 0.775], C3, "^")]
for name, y, col, mk in series:
    ax.plot(x, y, color=col, lw=2, marker=mk, ms=7, mec="white", mew=1.5,
            label=name, zorder=3)
    ax.annotate(name, (x[-1], y[-1]), (8, 0), textcoords="offset points",
                fontsize=8.5, color=col, fontweight="bold", va="center")
ax.axvline(500, color=GRID, lw=6, zorder=0)
ax.text(500, 0.905, "현행", ha="center", fontsize=8.5, color=MUTED)
ax.set_xticks(x); ax.set_xticklabels(["300자\n(49청크)", "500자\n(30청크)", "1000자\n(13청크)"])
ax.set_xlim(230, 1230); ax.set_ylim(0.60, 0.93)
tidy(ax, "MRR  (높을수록 정답이 상위)", "청크 크기")
save(fig, "fig4_chunk_size.png")

# ══════════════════ 그림 5. Ragas A/B/C ══════════════════
fig, ax = plt.subplots(figsize=(9.0, 3.9))
metrics = ["Faithfulness", "AnswerRelevancy", "ContextRecall", "ContextPrecision"]
data = {"A  현행": ([.954, .537, .900, .671], [.031, .027, .000, .005], C1),
        "B  프롬프트 수정": ([.941, .632, .900, .666], [.052, .014, .000, .028], C2),
        "C  하이브리드+프롬프트": ([.967, .565, 1.000, .819], [.016, .019, .000, .005], C3)}
xi = np.arange(len(metrics)); w = 0.26
for i, (name, (vals, errs, col)) in enumerate(data.items()):
    pos = xi + (i - 1) * w
    ax.bar(pos, vals, w * 0.88, color=col, label=name, zorder=3,
           yerr=errs, error_kw=dict(ecolor=INK, lw=1, capsize=3, alpha=.75))
    for px, v, e in zip(pos, vals, errs):
        ax.text(px, v + e + 0.035, f"{v:.3f}", ha="center", fontsize=7.6, color=INK)
ax.set_xticks(xi); ax.set_xticklabels(metrics, fontsize=9.5)
ax.set_ylim(0, 1.16); ax.set_yticks([0, .25, .5, .75, 1.0])
tidy(ax, "점수  (10문항 × 3회 평균, 오차막대 = 표준편차)")
ax.legend(frameon=False, fontsize=9, ncol=3, loc="upper center",
          bbox_to_anchor=(0.5, 1.16), labelcolor=INK)
save(fig, "fig5_ragas_ab.png")

# ══════════════════ 그림 6. 지연 구성 ══════════════════
fig, ax = plt.subplots(figsize=(8.6, 2.3))
rows = [("일반 경로\nuse_rag = false", 0, 9710),
        ("RAG 경로\nuse_rag = true", 376, 3897)]
for i, (name, ret, gen) in enumerate(rows):
    if ret:
        ax.barh(i, ret, height=.46, color=C1, alpha=.35, zorder=3)
        ax.text(ret / 2, i, f"{ret:,}", ha="center", va="center", fontsize=8, color=INK)
    ax.barh(i, gen, height=.46, left=ret, color=C1, zorder=3)
    ax.text(ret + gen / 2, i, f"generate  {gen:,} ms", ha="center", va="center",
            fontsize=9, color="white", fontweight="bold")
    ax.text(ret + gen + 180, i, f"총 {ret+gen:,} ms", va="center", fontsize=9,
            color=INK, fontweight="bold")
ax.set_yticks([0, 1]); ax.set_yticklabels([r[0] for r in rows], fontsize=9)
ax.set_xlim(0, 11800); ax.set_ylim(-0.6, 1.6)
tidy(ax, xlab="지연 (ms)", grid="x")
ax.text(376 / 2, 1.42, "retrieve", ha="center", fontsize=8, color=MUTED)
save(fig, "fig6_latency.png")

print("완료:", OUT)
