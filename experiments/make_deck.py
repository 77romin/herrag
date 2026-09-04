# -*- coding: utf-8 -*-
"""발표 자료(.pptx) 생성 — 대학원 세미나 톤, 분석체."""
import sys
from pathlib import Path
from pptx import Presentation
from pptx.util import Inches as In, Pt, Emu
from pptx.dml.color import RGBColor as C
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR

sys.stdout.reconfigure(encoding="utf-8")
OUTP = Path(r"C:\SSAFY\chatbot-project_lab\ChatBot_고찰발표.pptx")

INK, MUTED, ACCENT = C(0x1B, 0x2A, 0x24), C(0x5E, 0x68, 0x62), C(0x0E, 0x6A, 0x57)
RULE, SOFT, BAND = C(0xD3, 0xD9, 0xD2), C(0xF1, 0xF4, 0xF0), C(0xE6, 0xEC, 0xE8)
DOWN, WHITE = C(0xA8, 0x45, 0x2F), C(0xFF, 0xFF, 0xFF)
KR, NUM = "맑은 고딕", "Consolas"

prs = Presentation()
prs.slide_width, prs.slide_height = In(13.333), In(7.5)
BLANK = prs.slide_layouts[6]
W = 13.333


def tb(slide, l, t, w, h, align=PP_ALIGN.LEFT):
    box = slide.shapes.add_textbox(In(l), In(t), In(w), In(h))
    tf = box.text_frame
    tf.word_wrap = True
    tf.margin_left = tf.margin_right = tf.margin_top = tf.margin_bottom = 0
    tf.paragraphs[0].alignment = align
    return tf


def run(p, text, size, color=INK, bold=False, font=KR, space_after=0, space_before=0):
    r = p.add_run(); r.text = text
    r.font.size, r.font.color.rgb, r.font.bold, r.font.name = Pt(size), color, bold, font
    p.space_after, p.space_before = Pt(space_after), Pt(space_before)
    return r


def line(slide, l, t, w, color=RULE, h=0.012):
    s = slide.shapes.add_shape(1, In(l), In(t), In(w), In(h))
    s.fill.solid(); s.fill.fore_color.rgb = color; s.line.fill.background(); s.shadow.inherit = False
    return s


def base(eyebrow, title, n):
    s = prs.slides.add_slide(BLANK)
    tf = tb(s, 0.85, 0.52, 11.6, 0.3)
    run(tf.paragraphs[0], eyebrow, 11, ACCENT, True)
    tf = tb(s, 0.85, 0.86, 11.6, 0.6)
    run(tf.paragraphs[0], title, 26, INK, True)
    line(s, 0.85, 1.62, 11.63)
    tf = tb(s, 12.1, 6.92, 0.5, 0.25, PP_ALIGN.RIGHT)
    run(tf.paragraphs[0], f"{n:02d}", 10, C(0xA8, 0xB0, 0xAB), font=NUM)
    return s


def takeaway(slide, text):
    bar = slide.shapes.add_shape(1, In(0.85), In(6.18), In(11.63), In(0.52))
    bar.fill.solid(); bar.fill.fore_color.rgb = BAND
    bar.line.fill.background(); bar.shadow.inherit = False
    tf = tb(slide, 1.08, 6.31, 11.2, 0.3)
    run(tf.paragraphs[0], text, 13, ACCENT, True)


def bullets(slide, items, top=1.95, size=15, gap=13, left=0.85, width=11.6):
    tf = tb(slide, left, top, width, 4.0)
    first = True
    for it in items:
        txt, lvl = (it if isinstance(it, tuple) else (it, 0))
        p = tf.paragraphs[0] if first else tf.add_paragraph()
        first = False
        if lvl == 0:
            run(p, "— ", size, ACCENT, True)
            run(p, txt, size, INK, space_after=gap, space_before=0 if first else 4)
        else:
            p.level = 1
            run(p, "     " + txt, size - 1.5, MUTED, space_after=gap - 3)
    return tf


def table(slide, rows, top=2.05, left=0.85, width=11.63, colw=None,
          rh=0.34, size=12, head_size=10.5, hl=None, right_cols=None):
    nr, nc = len(rows), len(rows[0])
    shp = slide.shapes.add_table(nr, nc, In(left), In(top), In(width), In(rh * nr))
    t = shp.table
    t.first_row = False; t.horz_banding = False
    if colw:
        tot = sum(colw)
        for i, cw in enumerate(colw):
            t.columns[i].width = Emu(int(In(width) * cw / tot))
    right_cols = right_cols or []
    for ri, row in enumerate(rows):
        t.rows[ri].height = In(rh if ri else rh * 1.05)
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            cell.margin_left = In(0.12); cell.margin_right = In(0.12)
            cell.margin_top = In(0.04); cell.margin_bottom = In(0.04)
            cell.vertical_anchor = MSO_ANCHOR.MIDDLE
            cell.fill.solid()
            if ri == 0:
                cell.fill.fore_color.rgb = SOFT
            elif hl is not None and ri == hl:
                cell.fill.fore_color.rgb = BAND
            else:
                cell.fill.fore_color.rgb = WHITE
            tf = cell.text_frame; tf.word_wrap = True
            p = tf.paragraphs[0]
            p.alignment = PP_ALIGN.RIGHT if (ci in right_cols and ri > 0) else PP_ALIGN.LEFT
            if ri == 0:
                p.alignment = PP_ALIGN.RIGHT if ci in right_cols else PP_ALIGN.LEFT
            txt = str(val)
            mark = None
            if txt.startswith("!"):
                txt, mark = txt[1:], DOWN
            elif txt.startswith("*"):
                txt, mark = txt[1:], ACCENT
            r = p.add_run(); r.text = txt
            r.font.size = Pt(head_size if ri == 0 else size)
            r.font.name = NUM if (ci in right_cols and ri > 0 and
                                  txt.replace(".", "").replace(",", "").replace("±", "")
                                     .replace("+", "").replace("−", "").replace("−", "")
                                     .replace(" ", "").replace("/", "").isdigit()) else KR
            r.font.bold = (ri == 0) or (mark is not None)
            r.font.color.rgb = mark or (MUTED if ri == 0 else INK)
    return t


# ═══════════════════════════════════════════ 01 표지
s = prs.slides.add_slide(BLANK)
line(s, 0.9, 2.28, 1.7, ACCENT, 0.035)
tf = tb(s, 0.9, 2.62, 11.4, 1.5)
run(tf.paragraphs[0], "문서 기반 질의응답 시스템의\n검색 병목 규명과 개선", 38, INK, True)
tf = tb(s, 0.9, 4.28, 11.4, 0.4)
run(tf.paragraphs[0], "ChatBot 관통 프로젝트 · 요구사항 F207 · F208", 15, MUTED)
line(s, 0.9, 5.05, 11.53)
tf = tb(s, 0.9, 5.28, 11.4, 1.0)
p = tf.paragraphs[0]
run(p, "실험일 2026-09-04    |    생성 모델 gpt-5-mini    |    "
       "임베딩 text-embedding-3-small", 12, MUTED, font=KR)
p2 = tf.add_paragraph()
run(p2, "테스트셋 10문항 · 조건별 3회 반복 측정", 12, MUTED, space_before=6)

# ═══════════════════════════════════════════ 02 발표 순서
s = base("발표 순서", "논의의 흐름", 2)
rows = [["", "내용", "핵심 질문"],
        ["1", "문제 관찰과 측정 체계 재정립", "무엇을 재고 있었는가"],
        ["2", "가설 수립과 반증", "실패의 원인은 분할인가 검색인가"],
        ["3", "조건별 실험 결과 (추출·청킹·검색·프롬프트)", "어떤 조치가 어떤 지표를 움직이는가"],
        ["4", "호출 구조 계측", "요청 한 건은 무엇으로 분해되는가"],
        ["5", "논의: 관측된 RAG의 한계", "무엇을 일반화할 수 있는가"],
        ["6", "연구의 한계와 향후 과제", "무엇을 주장할 수 없는가"]]
table(s, rows, top=2.15, colw=[0.5, 5.6, 5.4], rh=0.5, size=13.5)
takeaway(s, "성능 개선의 서술이 아니라, 무엇이 병목이었는지를 규명한 과정의 보고이다.")

# ═══════════════════════════════════════════ 03 시스템 구성
s = base("배경", "대상 시스템의 구성", 3)
bullets(s, [
    "FastAPI 서버가 LangGraph 워크플로를 호출하고, 사내 프록시를 경유해 OpenAI API에 접근한다.",
    ("브라우저 → FastAPI(:8000) → LangGraph[ START → retrieve → generate → END ] → 프록시 → OpenAI", 1),
    "retrieve 노드는 Chroma 벡터스토어에서 상위 k=5개 청크를 조회하여 컨텍스트를 조립한다.",
    "대상 문서는 교육생 생활 규정 1종이며, 9,153자를 500자 단위로 분할해 30개 청크를 색인하였다.",
    ("표 내부에 <br> 태그가 116개 존재하여 원문 최장 줄이 615자에 이른다.", 1),
    "평가에는 Ragas 4개 지표(Faithfulness, AnswerRelevancy, ContextRecall, ContextPrecision)를 사용하였다.",
], top=2.05, gap=17)
takeaway(s, "기능 요구사항 F201–F206은 이미 충족된 상태에서 심화 요구사항만을 대상으로 하였다.")

# ═══════════════════════════════════════════ 04 문제 관찰
s = base("1. 문제 관찰", "특정 질의에서 검색이 완전히 실패하였다", 4)
tf = tb(s, 0.85, 2.05, 11.6, 0.4)
run(tf.paragraphs[0], "질의:  “교육 명찰을 분실했을 때는 어떻게 해야 하나요? 재발급 비용이 있나요?”",
    15, INK, True)
rows = [["지표", "값", "해석"],
        ["ContextRecall", "!0.000", "정답 근거가 컨텍스트에 전혀 포함되지 않음"],
        ["ContextPrecision", "!0.000", "검색된 5개 청크 중 관련 문서 없음"],
        ["Faithfulness", "1.000", "거절 응답 자체는 컨텍스트에 충실"],
        ["AnswerRelevancy", "!0.111", "질문에 대한 답이 되지 못함"]]
table(s, rows, top=2.68, colw=[2.6, 1.6, 7.4], rh=0.44, right_cols=[1])
tf = tb(s, 0.85, 4.85, 11.6, 0.8)
p = tf.paragraphs[0]
run(p, "응답:  ", 14, MUTED)
run(p, "“문의 사항은 참고 문서에 없습니다.”", 14, DOWN, True)
p2 = tf.add_paragraph()
run(p2, "그러나 원문에는 «재발급 비용 약 16,500원 본인 부담»이 명시되어 있다.",
    14, INK, space_before=8)
takeaway(s, "문서에 존재하는 정보를 시스템이 찾지 못하였다. 원인 규명이 필요하다.")

# ═══════════════════════════════════════════ 05 측정 도구 결함
s = base("1. 문제 관찰", "선행 확인: 측정 도구가 먼저 잘못되어 있었다", 5)
rows = [["결함", "원인", "영향"],
        ["10문항이 아닌 3문항으로 평가", "테스트셋 경로를 실행 위치 기준으로 탐색하여 로드 실패", "표본이 하드코딩 fallback으로 축소"],
        ["ContextPrecision이 순위에 무감각", "청크 5개를 연결한 문자열 1개를 전달하여 K=1로 고정", "정답이 1위든 5위든 동일 점수"],
        ["색인이 종료 시 소멸", "lifespan에서 저장소 디렉토리를 삭제", "전·후 비교의 재현성 상실"],
        ["임베딩 설정이 미반영", "환경변수 키 이름 불일치 (EMBEDDING_MODEL vs …_NAME)", "차원 1536으로 기본값이 사용됨"]]
table(s, rows, top=2.05, colw=[3.3, 5.0, 3.3], rh=0.72, size=12)
takeaway(s, "성능을 논하기 이전에 측정을 신뢰할 수 없는 상태였다. 다섯 항목을 수정한 뒤 재측정하였다.")

# ═══════════════════════════════════════════ 06 연구 질문
s = base("연구 질문", "세 가지를 묻는다", 6)
qs = [("RQ 1", "검색 실패의 원인은 문서 분할에 있는가, 검색 순위에 있는가?"),
      ("RQ 2", "각 개선 조치는 어떤 지표를 움직이며, 그 변화는 노이즈와 구별되는가?"),
      ("RQ 3", "유사도 점수는 관련성 판정의 기준으로 사용할 수 있는가?")]
top = 2.25
for tag, q in qs:
    bar = s.shapes.add_shape(1, In(0.85), In(top), In(11.63), In(1.02))
    bar.fill.solid(); bar.fill.fore_color.rgb = SOFT
    bar.line.fill.background(); bar.shadow.inherit = False
    tf = tb(s, 1.15, top + 0.16, 1.4, 0.3)
    run(tf.paragraphs[0], tag, 13, ACCENT, True, font=NUM)
    tf = tb(s, 1.15, top + 0.5, 10.8, 0.4)
    run(tf.paragraphs[0], q, 16, INK)
    top += 1.24
takeaway(s, "각 질문에 대해 LLM 심사에 의존하지 않는 측정을 우선 설계하였다.")

# ═══════════════════════════════════════════ 07 실험 설계 1
s = base("2. 실험 설계", "결정론적 검색 지표의 도입", 7)
bullets(s, [
    "Ragas는 LLM을 심사자로 사용하므로 동일 입력에도 실행마다 점수가 변동한다.",
    "검색 단계의 비교를 위해 LLM에 의존하지 않는 지표를 별도로 구성하였다.",
    "10개 질문 각각에 대해 정답이 기재된 위치를 앵커 문자열로 라벨링하였다.",
    ("예: 「16,500」, 「봉인」, 「6회 이상 Pass」, 「Job-Fair 시작 후 3~4주차」", 1),
    ("모든 앵커가 원문에서 정확히 1회만 출현함을 사전 확인하였다.", 1),
    "이 라벨을 기준으로 Recall@k 및 MRR을 산출하였다. 동일 입력에 대해 항상 동일한 값을 반환한다.",
], top=2.05, gap=15)
takeaway(s, "검색 품질과 생성 품질을 분리하여 측정함으로써 조치의 귀속을 명확히 하였다.")

# ═══════════════════════════════════════════ 08 실험 설계 2
s = base("2. 실험 설계", "조건 구성과 유의성 판정 기준", 8)
rows = [["축", "조건 수", "구성"],
        ["내용 추출", "3", "원본 마크다운 / 평문판 / 표 헤더 주입 정규화"],
        ["청크 크기", "4", "300 · 500(현행) · 1000 · 마크다운 헤더 분할"],
        ["임베딩 모델", "2", "text-embedding-3-small(1536) / -large(3072)"],
        ["검색 방식", "3", "dense / BM25 / 하이브리드(RRF, 가중 0.5·0.5)"],
        ["유사도 임계값", "6", "0.00 · 0.05 · 0.10 · 0.15 · 0.20 · 0.25"],
        ["종합 평가", "3 × 3회", "A 현행 / B 프롬프트 수정 / C 하이브리드 + 프롬프트"]]
table(s, rows, top=2.05, colw=[2.5, 1.5, 7.6], rh=0.52, size=13, right_cols=[1])
tf = tb(s, 0.85, 5.62, 11.6, 0.4)
run(tf.paragraphs[0], "유의성 판정:  변화량의 절대값이 표준편차의 2배를 초과하고, "
                      "동시에 0.05 이상일 때에만 유의한 것으로 간주하였다.", 13, INK, True)
takeaway(s, "조건은 한 번에 하나씩만 변경하여 효과의 귀속이 가능하도록 하였다.")

# ═══════════════════════════════════════════ 09 가설과 반증
s = base("3. 가설 검증", "초기 가설은 반증되었다", 9)
tf = tb(s, 0.85, 2.02, 11.6, 0.5)
p = tf.paragraphs[0]
run(p, "가설:  ", 15, ACCENT, True)
run(p, "615자에 이르는 표 행이 500자 단위 분할에서 절단되어 재발급 비용 정보가 소실되었다.",
    15, INK)
rows = [["검증 항목", "관측값", "판정"],
        ["총 청크 수", "30", "—"],
        ["청크 길이 (최소 / 중앙 / 최대)", "40 / 340 / 492", "—"],
        ["500자 초과 청크", "0", "절단 없음"],
        ["정답 청크 길이", "401", "헤더 포함 온전"],
        ["정답 청크 내 「16,500」 포함", "포함", "*소실되지 않음"]]
table(s, rows, top=2.72, colw=[4.6, 3.4, 3.6], rh=0.46, size=13, right_cols=[1], hl=5)
tf = tb(s, 0.85, 5.55, 11.6, 0.5)
run(tf.paragraphs[0], "정답 청크는 상위 헤더까지 포함하여 온전히 보존되어 있었다. "
                      "실패 시점의 순위는 6위로, k=5에서 절단된 것이다.", 14, INK)
takeaway(s, "병목은 분할이 아니라 순위였다. 가설을 기각하고 검색 방식으로 조사를 전환하였다.")

# ═══════════════════════════════════════════ 10 결과 1 추출
s = base("4. 결과 (1)", "내용 추출 방식 — 평문 표현이 우세하였다", 10)
rows = [["표현", "문자수", "청크", "최장 줄", "dense", "BM25", "hybrid"],
        ["원본 마크다운 (현행)", "9,153", "30", "615", "0.742", "0.867", "0.850"],
        ["평문판", "7,592", "18", "95", "0.708", "0.850", "*0.933"],
        ["표 헤더 주입 정규화", "8,258", "24", "95", "0.734", "!0.750", "0.800"]]
table(s, rows, top=2.12, colw=[3.4, 1.35, 1.0, 1.2, 1.3, 1.3, 1.4],
      rh=0.5, size=13, right_cols=[1, 2, 3, 4, 5, 6], hl=2)
tf = tb(s, 0.85, 4.15, 11.6, 1.6)
p = tf.paragraphs[0]
run(p, "<br> 태그가 실제 개행으로 전개되면서 분할기가 항목 경계에서 절단할 수 있게 되었고, "
       "청크 수가 30에서 18로 감소하였다.", 14, INK, space_after=10)
p = tf.add_paragraph()
run(p, "반면 표 헤더를 각 데이터 행에 주입한 정규화는 BM25를 0.867에서 0.750으로 저하시켰다. "
       "「구분」·「비고」 등 헤더 어휘가 전 청크에 반복 삽입되어 변별에 기여하지 못한 채 "
       "정보 밀도만 낮춘 것으로 해석된다.", 14, INK)
takeaway(s, "맥락을 추가하면 개선된다는 직관은 본 문서에서 성립하지 않았다. (MRR, 10문항)")

# ═══════════════════════════════════════════ 11 결과 2 청킹
s = base("4. 결과 (2)", "청크 크기 — dense와 BM25는 상반된 방향을 보였다", 11)
rows = [["설정", "청크", "dense MRR", "BM25 MRR", "hybrid MRR", "명찰 질의 순위"],
        ["recursive-300", "49", "*0.867", "0.750", "0.808", "*1위"],
        ["recursive-500 (현행)", "30", "0.742", "0.867", "*0.850", "!6위"],
        ["recursive-1000", "13", "!0.646", "0.883", "0.775", "3위"],
        ["markdown-500 (헤더 분할)", "30", "!0.645", "0.883", "0.850", "3위"]]
table(s, rows, top=2.12, colw=[3.5, 1.1, 1.8, 1.8, 1.9, 2.0],
      rh=0.5, size=13, right_cols=[1, 2, 3, 4, 5], hl=2)
tf = tb(s, 0.85, 4.25, 11.6, 1.5)
p = tf.paragraphs[0]
run(p, "청크가 작을수록 dense가 향상되고(0.646 → 0.742 → 0.867), BM25는 정확히 반대 방향을 "
       "보인다(0.750 → 0.867 → 0.883).", 14, INK, space_after=10)
p = tf.add_paragraph()
run(p, "밀집 벡터는 청크가 커질수록 여러 주제가 평균되어 변별력이 감소하는 반면, "
       "어휘 매칭은 청크가 커질수록 관련 용어를 더 많이 포함하여 유리해진다. "
       "두 방향이 상쇄되어 하이브리드의 최적점은 500자에 형성되었다.", 14, INK)
takeaway(s, "최적 청크 크기는 문서만으로 결정되지 않으며 검색 방식과 함께 정해진다.")

# ═══════════════════════════════════════════ 12 결과 3 검색
s = base("4. 결과 (3)", "검색 방식 — 어휘 매칭의 결합이 병목을 해소하였다", 12)
rows = [["방식", "R@1", "R@3", "R@5", "MRR", "명찰 질의"],
        ["dense (현행)", "0.60", "0.80", "0.90", "0.742", "!6위"],
        ["BM25 단독", "*0.80", "1.00", "1.00", "*0.867", "*1위"],
        ["하이브리드 (RRF 0.5·0.5)", "0.70", "*1.00", "*1.00", "0.850", "*2위"]]
table(s, rows, top=2.12, colw=[3.6, 1.4, 1.4, 1.4, 1.6, 2.2],
      rh=0.52, size=13, right_cols=[1, 2, 3, 4, 5], hl=3)
tf = tb(s, 0.85, 4.05, 11.6, 1.9)
p = tf.paragraphs[0]
run(p, "정답 청크에만 존재하는 「명찰」·「재발급」·「16,500」·「분실」을 어휘 매칭이 "
       "정확히 포착하였다. 밀집 벡터에서는 「교육명찰 상시 패용」·「명찰 임의 대여 금지」 등 "
       "동일 어휘를 공유하는 다른 규정이 상위를 점유하였다.", 14, INK, space_after=10)
p = tf.add_paragraph()
run(p, "한국어 조사 처리를 위한 토크나이저를 별도로 검토하였으나, 공백 분리만으로도 "
       "이미 1위였다. 조사 분리는 동일 토큰을 중복 삽입하여 점수를 0.47에서 8.52로 "
       "증폭시켰을 뿐 순위를 변경하지 못하여 채택하지 않았다.", 14, INK)
takeaway(s, "rank_bm25는 requirements.txt에 이미 포함되어 있었으나 사용되지 않고 있었다.")

# ═══════════════════════════════════════════ 13 결과 4 임베딩
s = base("4. 결과 (4)", "임베딩 모델 — 평균의 개선이 개별의 개선을 보장하지 않는다", 13)
rows = [["모델", "차원", "dense MRR", "R@5", "R@10", "명찰 질의 순위"],
        ["text-embedding-3-small", "1,536", "0.742", "0.90", "*1.00", "6위"],
        ["text-embedding-3-large", "3,072", "*0.788", "0.90", "!0.90", "!23위"]]
table(s, rows, top=2.15, colw=[4.0, 1.3, 1.9, 1.3, 1.3, 2.2],
      rh=0.56, size=13.5, right_cols=[1, 2, 3, 4, 5])
tf = tb(s, 0.85, 3.65, 11.6, 2.2)
p = tf.paragraphs[0]
run(p, "차원을 두 배로 확장한 모델에서 전체 MRR은 0.742에서 0.788로 상승하였다. "
       "그러나 동일 조건에서 명찰 질의의 정답 순위는 6위에서 23위로 하락하였고, "
       "Recall@10 또한 1.00에서 0.90으로 감소하였다.", 14, INK, space_after=12)
p = tf.add_paragraph()
run(p, "즉 집계 지표의 개선이 개별 질의의 개선을 함의하지 않는다. "
       "호출 비용이 두 배 이상인 점을 고려하여 채택하지 않았다.", 14, INK)
takeaway(s, "모델 규모의 확대는 이 과제에서 개선 근거가 되지 못하였다.")

# ═══════════════════════════════════════════ 14 결과 5 유사도
s = base("4. 결과 (5)", "유사도 점수는 관련성 판정의 기준이 되지 못한다  [RQ 3]", 14)
bullets(s, [
    "Chroma는 hnsw:space가 미지정이면 L2 거리를 사용한다. 본 시스템의 컬렉션 메타데이터는 비어 있었다.",
    "langchain-chroma는 L2에 대해 1 − d/√2 변환을 적용하므로, d > √2인 문서에서 점수가 음수가 된다.",
    ("관측 범위 −0.3070 ~ 0.3967 · 전체 점수의 50.7%가 음수 · Chroma 경고 발생", 1),
    "거리 척도를 cosine으로 변경하면 점수는 0~1로 정규화되나 순위는 변하지 않는다.",
    ("단위 벡터에서 두 척도는 단조 관계이며, 10문항 전체에서 순위가 완전히 일치함을 확인하였다.", 1),
], top=2.02, gap=13)
rows = [["임계값", "0.00", "0.05", "0.10", "0.15", "0.20", "0.25"],
        ["통과 청크 (평균)", "14.8", "10.7", "7.4", "4.9", "2.4", "1.5"],
        ["정답 차단 질의 수", "0", "0", "0", "0", "!2", "!3"]]
table(s, rows, top=4.72, colw=[2.9, 1.45, 1.45, 1.45, 1.45, 1.45, 1.45],
      rh=0.4, size=12.5, right_cols=[1, 2, 3, 4, 5, 6])
takeaway(s, "임계값을 상향하면 노이즈보다 정답이 먼저 차단된다. 정적 필터링은 성립하지 않는다.")

# ═══════════════════════════════════════════ 15 결과 6 임계값과 k
s = base("4. 결과 (6)", "임계값과 k는 서로를 대체하지 않는다", 15)
tf = tb(s, 0.85, 2.02, 11.6, 0.9)
p = tf.paragraphs[0]
run(p, "임계값 0.15에서 평균 4.9개가 통과하며 10문항 모두 정답이 통과한다. "
       "그러나 명찰 질의의 정답은 이 시점에도 6위이며, k=5에서 절단된다.", 14.5, INK)
rows = [["k", "정답 포함", "컨텍스트 길이", "비고"],
        ["3", "8 / 10", "약 1,020자", "—"],
        ["5 (현행)", "9 / 10", "약 1,700자", "명찰 질의 누락"],
        ["8", "*10 / 10", "약 2,720자", "노이즈 청크 증가"],
        ["10", "*10 / 10", "약 3,400자", "노이즈 청크 증가"]]
table(s, rows, top=2.95, colw=[1.6, 2.2, 2.8, 5.03], rh=0.5, size=13,
      right_cols=[1, 2], hl=3)
tf = tb(s, 0.85, 5.35, 11.6, 0.7)
run(tf.paragraphs[0], "임계값은 점수가 낮은 항목을 제거할 뿐 순위를 변경하지 못한다. "
                      "정답을 상위 k 안으로 이동시키는 것은 검색 방식의 역할이며, "
                      "하이브리드는 k=5에서 이미 10/10을 달성하였다.", 14, INK)
takeaway(s, "필터링과 랭킹은 서로 다른 문제이며, 전자로 후자를 해결할 수 없다.")

# ═══════════════════════════════════════════ 16 결과 7 프롬프트
s = base("4. 결과 (7)", "환각 방지 지시가 정상 응답을 훼손하였다", 16)
tf = tb(s, 0.85, 2.02, 11.6, 0.45)
run(tf.paragraphs[0], "현행 지시:  「[참고문서]에 없는 내용은 ‘문의 사항은 참고 문서에 없습니다.’ "
                      "라고만 답하세요.」", 14, MUTED)
bar = s.shapes.add_shape(1, In(0.85), In(2.58), In(11.63), In(0.95))
bar.fill.solid(); bar.fill.fore_color.rgb = SOFT
bar.line.fill.background(); bar.shadow.inherit = False
tf = tb(s, 1.1, 2.74, 11.1, 0.7)
p = tf.paragraphs[0]
run(p, "관측된 응답:  ", 13, DOWN, True)
run(p, "“예비군 훈련은 국가 관련 소집으로 공가로 처리됩니다. … 장기간 부재는 교육 담당자와 "
       "사전 면담 필요 ", 13.5, INK)
run(p, "문의 사항은 참고 문서에 없습니다.”", 13.5, DOWN, True)
rows = [["프롬프트", "거절 문구 등장", "단독 거절", "정상 응답 후미에 부착"],
        ["A 현행", "3 / 10", "1", "!2"],
        ["B 항목별 규칙으로 분리", "*0 / 10", "0", "*0"]]
table(s, rows, top=3.78, colw=[4.2, 2.6, 2.0, 2.83], rh=0.5, size=13,
      right_cols=[1, 2, 3], hl=2)
tf = tb(s, 0.85, 5.35, 11.6, 0.7)
run(tf.paragraphs[0], "복합 질의에서 문서에 일부 항목의 근거만 존재할 때, 모델은 정상 응답을 "
                      "생성한 뒤 거절 문구를 후미에 부착하였다. 안전장치로 도입된 제약이 "
                      "그 자체로 결함이 된 사례이다.", 14, INK)
takeaway(s, "지시를 항목별 규칙으로 분리한 결과 부착 현상은 완전히 소거되었다.")

# ═══════════════════════════════════════════ 17 결과 8 Ragas
s = base("4. 결과 (8)", "종합 평가 — 10문항 × 3회, 평균 ± 표준편차  [RQ 2]", 17)
rows = [["조건", "Faithfulness", "AnswerRelevancy", "ContextRecall", "ContextPrecision"],
        ["A  현행", "0.954 ± .031", "0.537 ± .027", "0.900 ± .000", "0.671 ± .005"],
        ["B  프롬프트만 수정", "0.941 ± .052", "*0.632 ± .014", "0.900 ± .000", "0.666 ± .028"],
        ["C  하이브리드 + 프롬프트", "0.967 ± .016", "0.565 ± .019", "*1.000 ± .000", "*0.819 ± .005"]]
table(s, rows, top=2.06, colw=[3.6, 2.0, 2.1, 1.95, 1.98], rh=0.45, size=12.5,
      right_cols=[1, 2, 3, 4], hl=3)
rows2 = [["A 대비 변화량", "Faithfulness", "AnswerRelevancy", "ContextRecall", "ContextPrecision"],
         ["B", "−0.013  노이즈", "*+0.094  유의", "±0.000  노이즈", "−0.005  노이즈"],
         ["C", "+0.012  노이즈", "+0.028  노이즈", "*+0.100  유의", "*+0.149  유의"]]
table(s, rows2, top=4.26, colw=[3.6, 2.0, 2.1, 1.95, 1.98], rh=0.45, size=12.5,
      right_cols=[1, 2, 3, 4])
tf = tb(s, 0.85, 5.72, 11.6, 0.4)
run(tf.paragraphs[0], "B는 검색을 변경하지 않았으므로 ContextRecall이 표준편차 0.000으로 "
                      "동일하다. Faithfulness는 세 조건 모두 노이즈 범위이다.", 13.5, INK)
takeaway(s, "C의 AnswerRelevancy는 B보다 낮다. 검색 개선이 모든 지표를 동반 상승시키지는 않는다.")

# ═══════════════════════════════════════════ 18 결과 9 호출 계측
s = base("4. 결과 (9)", "호출 구조 계측 — 지연은 출력 토큰이 지배한다", 18)
bullets(s, [
    "LangChain 콜백 핸들러를 실제 파이프라인에 부착하여 요청 한 건의 실행 트리를 계측하였다.",
    ("LangSmith와 동일한 인터페이스이며, 결과를 외부로 전송하지 않고 로컬에 기록하였다.", 1),
], top=2.02, gap=10)
rows = [["경로", "외부 호출", "프롬프트", "입력 토큰", "출력 토큰", "지연"],
        ["RAG (use_rag = true)", "2회", "1,909자", "1,120", "274", "*4,275 ms"],
        ["일반 (use_rag = false)", "1회", "106자", "70", "!792", "!9,711 ms"]]
table(s, rows, top=3.02, colw=[3.6, 1.6, 1.8, 1.7, 1.6, 1.93], rh=0.54, size=13.5,
      right_cols=[1, 2, 3, 4, 5])
tf = tb(s, 0.85, 4.55, 11.6, 1.5)
p = tf.paragraphs[0]
run(p, "RAG 경로의 지연 4,275 ms 중 3,897 ms(91%)가 생성 단계이며, retrieve는 376 ms이다. "
       "LangGraph 자체의 오버헤드는 0.0~0.2 ms로 무시 가능하다.", 14, INK, space_after=10)
p = tf.add_paragraph()
run(p, "검색을 부가한 경로가 오히려 2.3배 빨랐다. 입력 토큰이 16배 증가하였음에도 "
       "출력 토큰이 792에서 274로 감소하였기 때문이다. 생성은 토큰 단위로 순차 수행되고 "
       "입력은 일괄 처리된다.", 14, INK)
takeaway(s, "참고 문서의 제공은 정확도뿐 아니라 응답 지연과 출력 비용도 함께 감소시켰다.")

# ═══════════════════════════════════════════ 19 결과 10 문서 교체
s = base("4. 결과 (10)", "참조 문서만 교체하였을 때의 응답 변화", 19)
tf = tb(s, 0.85, 2.0, 11.6, 0.4)
run(tf.paragraphs[0], "질의: “국토교통부 청년월세 한시 특별지원은 최대 몇 개월 동안 "
                      "총 얼마까지 받을 수 있나요?”  (실제: 24개월 · 480만원)", 14, MUTED)
rows = [["상태", "응답", "판정"],
        ["S1  RAG 미사용", "“흔히 3~6개월 … 수십만 원에서 100만원대”", "!그럴듯하나 오류"],
        ["S2  규정집만 색인", "“문의 사항은 참고 문서에 없습니다.”", "*정확한 거절"],
        ["S3  청년월세 문서 업로드", "“최대 24개월간, 총 480만원(월 최대 20만원)”", "*정확"]]
table(s, rows, top=2.55, colw=[3.3, 5.9, 2.43], rh=0.56, size=13, hl=3)
tf = tb(s, 0.85, 4.5, 11.6, 1.5)
p = tf.paragraphs[0]
run(p, "질의·모델·프롬프트를 고정하고 참조 가능한 문서만 변경하였다. "
       "S1의 응답은 확신을 유보하는 표현을 사용하였으나 그것이 오류를 방지하지는 못하였다.",
    14, INK, space_after=10)
p = tf.add_paragraph()
run(p, "다만 S3에서 인접 절의 오염이 관측되었다. 인천 지역 질의에 대한 응답에 "
       "문서상 서울시 절에만 기재된 연락처가 부착되었다.", 14, DOWN)
takeaway(s, "검색이 정답을 포함하더라도 함께 검색된 이웃이 응답을 오염시킬 수 있다.")

# ═══════════════════════════════════════════ 20 논의
s = base("5. 논의", "관측에 근거한 RAG의 한계", 20)
bullets(s, [
    "밀집 벡터는 고유 어휘의 변별력을 희석한다. 정답에만 존재하는 고유명사·수치가 6위로 밀렸다.",
    "유사도 점수는 관련성 판정의 기준이 되지 못한다. 절반이 음수였고 동적 범위가 지나치게 좁다.",
    "함께 검색된 이웃 문서가 응답을 오염시킨다. 정답의 포함이 정답만의 반영을 보장하지 않는다.",
    "환각 방지를 위한 배타적 지시가 정상 응답을 훼손한다. 안전장치 자체가 결함원이 될 수 있다.",
    "집계 지표의 개선이 개별 질의의 개선을 함의하지 않는다. 임베딩 확장이 이를 보여준다.",
    "평가 도구 또한 조용히 오작동한다. 지표가 값을 산출한다는 것이 그 값의 유효성을 뜻하지 않는다.",
], top=2.05, size=14.5, gap=16)
takeaway(s, "여섯 항목 모두 본 실험에서 직접 관측된 것으로, 일반론적 서술을 배제하였다.")

# ═══════════════════════════════════════════ 21 한계
s = base("6. 한계와 향후 과제", "본 연구가 주장할 수 없는 것", 21)
tf = tb(s, 0.85, 2.0, 5.55, 3.6)
p = tf.paragraphs[0]
run(p, "연구의 한계", 15, ACCENT, True, space_after=12)
for t in ["문서 1종·질의 10문항의 소표본이며 도메인 일반화는 불가하다.",
          "임베딩은 OpenAI 계열 2종만 비교하였다.",
          "반복은 3회로, Faithfulness의 변동을 분리하기에 부족하다.",
          "앵커 라벨링은 정답 위치를 1개로 가정하며 복수 근거 질의를 반영하지 못한다.",
          "재순위화와 폴백 라우팅은 예산상 검증하지 못하였다."]:
    p = tf.add_paragraph()
    run(p, "· " + t, 13.5, INK, space_after=11)
tf = tb(s, 6.95, 2.0, 5.53, 3.6)
p = tf.paragraphs[0]
run(p, "향후 과제", 15, ACCENT, True, space_after=12)
for t in ["교차 인코더 재순위화로 Recall@1(0.70) 개선 여지를 검증한다.",
          "검색 실패 판정을 어휘 매칭 점수 기반으로 설계하여 F206을 충족한다.",
          "응답 스트리밍을 도입하여 체감 지연을 개선한다.",
          "클라이언트의 HTTP 상태 코드 처리를 보완한다.",
          "검색 근거를 화면에 노출하여 판단 과정을 검증 가능하게 한다."]:
    p = tf.add_paragraph()
    run(p, "· " + t, 13.5, INK, space_after=11)
line(s, 6.72, 2.05, 0.008, RULE, 3.4)
takeaway(s, "측정 가능한 범위를 넘어서는 주장은 제시하지 않는다.")

# ═══════════════════════════════════════════ 22 결론
s = base("결론", "요약", 22)
rows = [["질문", "결론"],
        ["RQ 1  실패의 원인은 분할인가 검색인가",
         "분할이 아니다. 정답 청크는 온전하였고 순위가 6위여서 절단되었다."],
        ["RQ 2  각 조치는 어떤 지표를 움직이는가",
         "프롬프트 수정은 AnswerRelevancy(+0.094), 하이브리드 검색은 "
         "ContextRecall(+0.100)과 ContextPrecision(+0.149)을 유의하게 개선하였다."],
        ["RQ 3  유사도 점수를 판정에 쓸 수 있는가",
         "사용할 수 없다. 점수의 50.7%가 음수였고, 임계값 상향 시 정답이 먼저 차단되었다."]]
table(s, rows, top=2.15, colw=[4.2, 7.43], rh=0.95, size=13.5)
tf = tb(s, 0.85, 5.4, 11.6, 0.6)
run(tf.paragraphs[0], "가장 크게 개선된 것은 검색 방식이었고, 가장 크게 잘못되어 있던 것은 "
                      "성능이 아니라 측정 체계였다.", 15.5, INK, True)
takeaway(s, "실험 스크립트와 원자료는 experiments/ 에 있으며 재현 가능하다.")

prs.save(OUTP)
print(f"저장: {OUTP}  ({len(prs.slides.__iter__.__self__._sldIdLst)} 슬라이드)")
