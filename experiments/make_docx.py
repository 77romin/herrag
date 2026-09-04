# -*- coding: utf-8 -*-
"""고찰 보고서(.docx) 생성 — 명세 1.6 산출물 3) 고찰 보고서."""
import sys
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor as C
from docx.enum.text import WD_ALIGN_PARAGRAPH as AL, WD_BREAK
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

sys.stdout.reconfigure(encoding="utf-8")
OUTP = Path(r"C:\SSAFY\chatbot-project_lab\ChatBot_고찰보고서.docx")
FIG = Path(r"C:\SSAFY\chatbot-project_lab\experiments\figures")

INK, MUTED, ACCENT = C(0x1B, 0x2A, 0x24), C(0x5E, 0x68, 0x62), C(0x0E, 0x6A, 0x57)
DOWN = C(0xA8, 0x45, 0x2F)
KR, MONO = "맑은 고딕", "Consolas"

doc = Document()
sec = doc.sections[0]
sec.page_width, sec.page_height = Cm(21.0), Cm(29.7)
sec.top_margin = sec.bottom_margin = Cm(1.27)
sec.left_margin = sec.right_margin = Cm(1.27)
CW = 21.0 - 1.27 * 2


def set_font(style, name=KR, size=10.5, color=INK, bold=False):
    style.font.name = name
    style.font.size = Pt(size)
    style.font.color.rgb = color
    style.font.bold = bold
    style.element.rPr.rFonts.set(qn("w:eastAsia"), name)


st = doc.styles["Normal"]
set_font(st, KR, 10.5)
st.paragraph_format.line_spacing = 1.5
st.paragraph_format.space_after = Pt(6)

for _name, _size, _color, _before, _after in [
    ("Heading 1", 17, INK, 26, 10),
    ("Heading 2", 13, INK, 20, 7),
    ("Heading 3", 11.5, ACCENT, 14, 5),
]:
    _s = doc.styles[_name]
    set_font(_s, KR, _size, _color, True)
    _s.paragraph_format.space_before = Pt(_before)
    _s.paragraph_format.space_after = Pt(_after)
    _s.paragraph_format.keep_with_next = True


def shade(el, hexcolor):
    sh = OxmlElement("w:shd")
    sh.set(qn("w:val"), "clear")
    sh.set(qn("w:fill"), hexcolor)
    el.append(sh)


def p(text="", style=None, size=None, color=None, bold=False, align=None,
      space_before=None, space_after=None, font=KR, indent=None):
    par = doc.add_paragraph(style=style)
    if align is not None:
        par.alignment = align
    if space_before is not None:
        par.paragraph_format.space_before = Pt(space_before)
    if space_after is not None:
        par.paragraph_format.space_after = Pt(space_after)
    if indent is not None:
        par.paragraph_format.left_indent = Cm(indent)
    if text:
        r = par.add_run(text)
        r.font.name = font
        r._element.rPr.rFonts.set(qn("w:eastAsia"), font)
        if size:
            r.font.size = Pt(size)
        if color:
            r.font.color.rgb = color
        r.font.bold = bold
    return par


def rich(par, parts, size=10.5):
    for t, b, c in parts:
        r = par.add_run(t)
        r.font.name = KR
        r._element.rPr.rFonts.set(qn("w:eastAsia"), KR)
        r.font.size = Pt(size)
        r.font.bold = b
        if c:
            r.font.color.rgb = c
    return par


def quote(parts, size=10):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Cm(0.5)
    par.paragraph_format.space_before = Pt(6)
    par.paragraph_format.space_after = Pt(10)
    shade(par._p.get_or_add_pPr(), "F1F4F0")
    return rich(par, parts, size)


def num(items, start=1):
    for i, t in enumerate(items, start):
        par = doc.add_paragraph()
        par.paragraph_format.left_indent = Cm(0.75)
        par.paragraph_format.first_line_indent = Cm(-0.45)
        par.paragraph_format.space_after = Pt(4)
        par.paragraph_format.line_spacing = 1.45
        rich(par, [(f"{i}. ", True, ACCENT), (t, False, None)])


def bullet(text, sub=False):
    par = doc.add_paragraph(style="List Bullet")
    par.paragraph_format.left_indent = Cm(1.1 if sub else 0.6)
    par.paragraph_format.space_after = Pt(4)
    par.paragraph_format.line_spacing = 1.45
    r = par.add_run(text)
    r.font.name = KR
    r._element.rPr.rFonts.set(qn("w:eastAsia"), KR)
    r.font.size = Pt(10 if sub else 10.5)
    if sub:
        r.font.color.rgb = MUTED
    return par


def code(lines):
    par = doc.add_paragraph()
    par.paragraph_format.left_indent = Cm(0.5)
    par.paragraph_format.space_before = Pt(6)
    par.paragraph_format.space_after = Pt(10)
    par.paragraph_format.line_spacing = 1.25
    shade(par._p.get_or_add_pPr(), "F1F4F0")
    r = par.add_run("\n".join(lines))
    r.font.name = MONO
    r._element.rPr.rFonts.set(qn("w:eastAsia"), KR)
    r.font.size = Pt(9)
    r.font.color.rgb = INK
    return par


def caption(text):
    return p(text, size=9, color=MUTED, space_before=2, space_after=12)


_fig = [0]


def figure(name, cap, width=17.4):
    par = doc.add_paragraph()
    par.alignment = AL.CENTER
    par.paragraph_format.space_before = Pt(10)
    par.paragraph_format.space_after = Pt(3)
    par.add_run().add_picture(str(FIG / name), width=Cm(width))
    _fig[0] += 1
    return p(f"[그림 {_fig[0]}]  {cap}", size=9, color=MUTED, align=AL.CENTER,
             space_before=0, space_after=14)


def table(rows, widths=None, right_cols=None, hl=None, size=9.5, head=True):
    right_cols = right_cols or []
    t = doc.add_table(rows=len(rows), cols=len(rows[0]))
    t.style = "Table Grid"
    t.alignment = WD_TABLE_ALIGNMENT.CENTER
    t.autofit = False
    total = sum(widths) if widths else len(rows[0])
    for ri, row in enumerate(rows):
        for ci, val in enumerate(row):
            cell = t.cell(ri, ci)
            if widths:
                cell.width = Cm(CW * widths[ci] / total)
            par = cell.paragraphs[0]
            par.paragraph_format.space_before = Pt(2)
            par.paragraph_format.space_after = Pt(2)
            par.paragraph_format.line_spacing = 1.2
            par.alignment = AL.RIGHT if ci in right_cols else AL.LEFT
            txt, col, bold = str(val), None, False
            if txt.startswith("!"):
                txt, col, bold = txt[1:], DOWN, True
            elif txt.startswith("*"):
                txt, col, bold = txt[1:], ACCENT, True
            r = par.add_run(txt)
            r.font.name = KR
            r._element.rPr.rFonts.set(qn("w:eastAsia"), KR)
            r.font.size = Pt(size)
            if ri == 0 and head:
                r.font.bold = True
                r.font.color.rgb = MUTED
                shade(cell._tc.get_or_add_tcPr(), "F1F4F0")
            else:
                r.font.bold = bold
                r.font.color.rgb = col or INK
                if hl is not None and ri == hl:
                    shade(cell._tc.get_or_add_tcPr(), "E6ECE8")
    doc.add_paragraph().paragraph_format.space_after = Pt(0)
    return t


def field(par, instr):
    for tag, txt in (("begin", None), ("instrText", instr), ("separate", None),
                     ("t", "…"), ("end", None)):
        if tag == "instrText":
            e = OxmlElement("w:instrText")
            e.set(qn("xml:space"), "preserve")
            e.text = txt
        elif tag == "t":
            e = OxmlElement("w:t")
            e.text = txt
        else:
            e = OxmlElement("w:fldChar")
            e.set(qn("w:fldCharType"), tag)
        par.add_run()._element.append(e)


def pagebreak():
    doc.add_paragraph().add_run().add_break(WD_BREAK.PAGE)


# ═══════════════════════════════════════════════════════ 표지
p("", space_after=120)
p("ChatBot Project 고찰 보고서", size=24, color=INK, bold=True, space_after=8)
p("문서 기반 질의응답 시스템의 검색 병목 규명과 개선", size=13, color=MUTED, space_after=40)
p("요구사항 F207 · F208", size=11, color=ACCENT, bold=True, space_after=60)
table([
    ["실험 일자", "2026-09-04"],
    ["생성 모델", "gpt-5-mini (SSAFY GMS 프록시 경유)"],
    ["임베딩 모델", "text-embedding-3-small (1,536차원)"],
    ["대상 문서", "SSAFY_GUIDE.md · YOUTH_RENT_GUIDE.md (직접 수집)"],
    ["평가 규모", "10문항 × 3회 반복 + 결정론적 검색 지표"],
], widths=[3, 9], head=False, size=10)
pagebreak()

# ═══════════════════════════════════════════════════════ 목차
p("목차", style="Heading 1")
field(doc.add_paragraph(), r'TOC \o "1-2" \h \z \u')
p("※ 문서를 연 뒤 목차를 클릭하고 F9를 누르면 쪽 번호가 갱신됩니다.",
  size=9, color=MUTED, space_before=10)
pagebreak()

# ═══════════════════════════════════════════════════════ 0. 요약
p("0. 요약", style="Heading 1")
p("현행 파이프라인을 기준선(Baseline)으로 설정한 뒤, 내용 추출, 청킹, 검색 방식, 시스템 "
  "프롬프트를 각각 독립 변수로 변경하며 성능을 측정했다. 실험 결과 가장 큰 성능 변화를 "
  "유발한 요인은 검색 방식의 개선이었다. 또한 모델 성능 자체보다 더 큰 왜곡을 초래했던 "
  "요인은 측정 도구, 즉 평가 하네스 자체의 결함이었다.")
table([
    ["확인된 문제점", "개선 조치 및 결과"],
    ["평가 하네스가 3문항 기본 예외(fallback)로만 동작 중이었음", "10문항 전체 평가로 정상화"],
    ["ContextPrecision이 검색 순위를 판별하지 못함",
     "검색 청크를 단일 문자열이 아닌 개별 청크 리스트로 전달하도록 수정"],
    ["밀집 검색 단독 사용으로 인한 키워드 누락",
     "*하이브리드 검색(BM25 + Dense) 도입 — ContextRecall 0.900 → 1.000, "
     "ContextPrecision 0.671 → 0.819"],
    ["프롬프트의 배타적 거절 지시로 인한 오답 처리",
     "*지침을 항목별 규칙으로 세분화 — AnswerRelevancy 0.537 → 0.632"],
    ["유사도 점수 체계 왜곡",
     "!전체 산출 점수의 50.7%가 음수로 산출되던 L2 거리 변환 수식의 한계 규명"],
    ["청킹 오류로 인한 검색 실패 가설 검증",
     "!가설은 빗나감(정답 청크는 정상 보존). 단, 청크 크기는 검색 방식에 따라 독립적 영향 확인"],
], widths=[6.5, 6.5])

# ═══════════════════════════════════════════════════════ 1
p("1. 실험 환경과 방법", style="Heading 1")

p("1-1. 평가 환경의 사전 정상화", style="Heading 2")
p("성능 비교를 진행하기에 앞서, 신뢰성 있는 평가를 저해하던 평가 하네스의 다섯 가지 결함을 "
  "우선 정비했다. 측정 환경이 온전하지 않으면 이후의 비교 분석이 모두 왜곡되기 때문이다.")
table([
    ["문제 현상", "발생 원인", "조치 내용"],
    ["전체 10문항 중 3문항으로만 평가 진행",
     "eval_ragas.py 가 실행 경로를 기준으로 ./test_cases.json 을 탐색하여 파일 로드에 실패",
     "스크립트 위치를 기준으로 경로를 해석하도록 수정"],
    ["ContextPrecision 의 순위 판별 불가",
     "검색된 5개 청크를 하나의 문자열로 병합 전달하여 평가 K 가 1로 고정됨",
     "RAGState 에 retrieved_texts 필드를 추가하고 청크 리스트 형태로 전달"],
    ["서버 재시작 시 인덱스 소멸",
     "FastAPI 라이프사이클(lifespan) 내 shutil.rmtree 실행",
     "KEEP_CHROMA 환경 변수를 도입하여 기본 보존되도록 제어"],
    ["임베딩 모델 설정 불일치",
     ".env 에는 EMBEDDING_MODEL, 코드에는 EMBEDDING_MODEL_NAME 으로 작성되어 환경 변수가 무시됨",
     "환경 변수 키 이름 통일"],
    ["검색 점수 기록 불가", "상태 관리 객체 내 스코어 저장 필드 부재",
     "RAGState 에 scores 필드 추가"],
], widths=[3.4, 5.2, 3.6])
p("특히 네 번째 항목의 경우, Chroma 컬렉션의 실제 차원이 1,536차원으로 확인되었다. 환경 "
  "변수에는 text-embedding-3-large(3,072차원)가 지정되어 있었으나, 변수명 불일치로 인해 "
  "기본값인 text-embedding-3-small 이 적용되고 있었다. 이에 따라 기준선의 재현성을 확보하기 "
  "위해 실제로 구동되던 small 모델을 명시적 기준선으로 채택하고, large 모델은 별도의 비교 "
  "실험군으로 분리했다.")

p("1-2. LLM 비의존적 결정론적 검색 지표 구성", style="Heading 2")
p("Ragas 는 LLM 을 판정자로 활용하므로 동일한 입력값에 대해서도 평가 회차마다 점수 편차가 "
  "발생한다. 따라서 검색 단계의 성능만을 분리해 비교하기 위해 LLM 을 거치지 않는 "
  "결정론적(Deterministic) 지표를 병행 구축했다.")
p("10개 테스트 질문에 대해 원문 내 정답이 위치한 문장을 앵커 문자열로 라벨링했다. 모든 "
  "앵커는 문서 전체에서 고유하게 단 1회만 출현함을 사전 검증했다.")
table([
    ["평가 질문", "라벨링된 고유 앵커 문자열"],
    ["예비군 결석 처리", "예비군/민방위 등"],
    ["경조사 공가 일수", "본인 결혼 (5일)"],
    ["지각·조퇴 누적 규정", "지각/조퇴/외출 3회"],
    ["정규 교육시간", "09:00 ~ 18:00"],
    ["휴대전화·외부음식 규정", "외부 음식 반입 및 취식 금지"],
    ["명찰 재발급 비용", "16,500"],
    ["캠퍼스 보안 반입 절차", "봉인"],
    ["수료 기준", "6회 이상 Pass"],
    ["지원금 지급 시기", "Job-Fair 시작 후 3~4주차"],
    ["지각·조퇴 체크 기준 시각", "18:30"],
], widths=[5, 7])
p("위 라벨을 바탕으로 Recall@k 와 MRR(Mean Reciprocal Rank)을 산출했다. 이 지표들은 "
  "결정론적으로 계산되므로 특정 개선 조치가 검색 품질에 미친 영향을 독립적으로 판별할 수 있다.")

p("1-3. 대상 문서 제원", style="Heading 2")
table([
    ["문서명", "총 문자 수", "줄 수", "헤더 수", "표 행 수", "최장 행 길이"],
    ["SSAFY_GUIDE.md (기본 제공)", "9,153", "232", "25", "77", "615자"],
    ["YOUTH_RENT_GUIDE.md (직접 수집)", "6,107", "244", "29", "60", "97자"],
], widths=[5.4, 1.6, 1.1, 1.1, 1.2, 1.6], right_cols=[1, 2, 3, 4, 5])
p("두 번째 문서는 요구사항 F208 ①을 검증하기 위해 인천광역시 청년포털, 서울주거포털, "
  "토스피드의 공개 자료를 바탕으로 직접 수집·정리한 문서다. 국토교통부, 서울시, 인천시의 "
  "청년월세 지원 사업을 포괄하며, 지원 금액은 월 20만 원으로 동일하나 지원 기간(24개월 대 "
  "12개월)과 보증금 요건(5,000만 원 대 8,000만 원)이 상이하다. 유사한 조건 속에서 정밀한 "
  "수치 식별 성능을 평가하기에 적합한 데이터셋이다.")
p("검색 방식과 평가 지표의 정의는 다음 장에 정리했다.", size=10, color=MUTED)

# ═══════════════════════════════════════════════════════ 2
p("2. 핵심 개념 및 평가 지표 정의", style="Heading 1")

p("2-1. 검색 방식의 특성 및 상호 결합 (Hybrid Retrieval)", style="Heading 2")
p("밀집 검색 (Dense Retrieval)", style="Heading 3")
p("문장을 1,536차원의 고밀도 벡터로 변환하여 의미적 유사도를 측정한다. 질의와 문서 벡터 간 "
  "방향성이 일치할수록 유사도가 높게 산출된다. 어휘가 정확히 일치하지 않더라도 문맥이 "
  "유사하면 검색이 가능하다는 장점이 있으나(예: '연차' 검색 시 '휴가' 조항 반환), 단락 "
  "전체를 단일 벡터로 압축 표현하는 특성상 특정 숫자나 고유명사의 식별력이 희석되는 한계를 "
  "지닌다. 본문 5-1절의 명찰 사례가 여기에 해당한다.")
p("어휘 검색 (BM25)", style="Heading 3")
p("질의에 포함된 단어의 출현 빈도(TF), 역문서 빈도(IDF), 청크 길이를 종합적으로 고려해 "
  "점수를 산출한다. 흔한 불용어의 가중치는 낮추고 드물게 등장하는 핵심 키워드에 높은 점수를 "
  "부여한다. 문맥적 의미는 반영하지 못하나 '16,500'이나 '재발급'처럼 고유한 키워드가 포함된 "
  "청크를 정밀하게 식별한다.")
p("RRF(Reciprocal Rank Fusion)를 통한 결과 결합", style="Heading 3")
p("두 검색기가 산출하는 스코어는 스케일이 다르므로 단순 합산이 불가능하다. 따라서 점수 대신 "
  "순위(Rank)를 활용하는 RRF 알고리즘을 적용한다. 각 검색기 순위 r 에 대해 1 / (60 + r) 을 "
  "산출한 뒤 가중치를 곱해 합산한다. 상수 60은 상위권 순위 간 점수 격차를 완만하게 조정하는 "
  "역할을 한다.")
code([
    "[계산 예시] 명찰 질문의 정답 청크 — Dense 6위, BM25 1위",
    "",
    "  0.5 / (60 + 6)  +  0.5 / (60 + 1)",
    "= 0.00758        +  0.00820",
    "= 0.01578",
    "",
    "Dense 1위이나 BM25 순위가 낮은 문서(0.00820)보다 높은 점수를 얻어 상위권으로 재배열된다.",
])

p("2-2. 결정론적 검색 지표: Recall@k 및 MRR", style="Heading 2")
bullet("Recall@k: 질의 10개 중 상위 k개 결과 내에 정답 청크가 포함된 질의의 비율이다. "
       "순위와 무관하게 허용 범위 내 포함 여부만을 측정한다.")
bullet("MRR(Mean Reciprocal Rank): 각 질의별 정답 청크의 역순위(1/r)를 평균한 값이다. "
       "정답이 최상단에 위치할수록 1.0에 수렴하며, 검색 결과의 상위 집중도를 평가한다.")
code([
    "[계산 예시] 현행 Dense 검색의 10문항 정답 순위",
    "  [ 1, 2, 4, 1, 1, 6, 1, 2, 1, 1 ]",
    "",
    "  (1 + 0.5 + 0.25 + 1 + 1 + 0.167 + 1 + 0.5 + 1 + 1) / 10  =  0.742",
])
p("k=5 로 절단하는 본 시스템에서는 Recall@5 가 성패를 가르고, MRR 은 그 안에서의 상위 "
  "집중도를 보여준다. 두 지표를 함께 관측하는 이유가 여기에 있다.")

p("2-3. Ragas 4대 지표의 구조", style="Heading 2")
p("Ragas 는 LLM 을 심사자로 활용하여 RAG 시스템 전반을 다각도로 평가한다. 평가 변동성을 "
  "감안하여 모든 조건에서 3회 반복 측정을 수행했다.")
figure("fig2_ragas_metrics.png",
       "Ragas 4대 지표의 비교 대상 및 평가 기준. 앞의 두 지표는 생성 품질을, "
       "뒤의 두 지표는 검색 품질을 측정한다.")
table([
    ["지표명", "비교 대상 (평가 축)", "지표 저하 시 주요 원인", "기준선(A)"],
    ["Faithfulness", "생성 답변 ↔ 검색 컨텍스트", "컨텍스트에 없는 허위 정보 생성(환각)", "0.954"],
    ["AnswerRelevancy", "생성 답변 ↔ 사용자 질문", "질의 취지와 무관한 응답 또는 과도한 축약", "!0.537"],
    ["ContextRecall", "검색 컨텍스트 ↔ 실제 정답", "답변 생성에 필요한 근거 문서 누락", "0.900"],
    ["ContextPrecision", "검색 순위 ↔ 실제 정답", "정답보다 무관한 청크가 상위에 랭크됨", "0.671"],
], widths=[3.0, 5.2, 5.8, 2.0], right_cols=[3])
p("앞의 두 지표는 프롬프트를 조정하면 반응하고, 뒤의 두 지표는 검색을 조정하면 반응한다. "
  "본문 5-5절의 대응 관계가 바로 이 구조에서 도출된다.")

p("2-4. 코사인 유사도와 L2 거리 수식 및 음수 스코어 분석", style="Heading 2")
p("실측 결과 relevance score 의 50.7%가 음수로 산출되는 현상이 관측되었다. 발생 원인은 "
  "다음과 같다.")
num([
    "임베딩 모델의 출력 벡터는 크기가 1인 단위 벡터이다.",
    "단위 벡터 간 유클리드 거리 d 와 코사인 유사도 사이에는 "
    "d² = |u − v|² = |u|² + |v|² − 2(u·v) = 2 − 2cosθ 의 관계식이 성립한다.",
    "Chroma 는 기본 거리 척도로 L2 공간을 사용하며, 계산 효율을 위해 제곱근을 적용하지 않은 "
    "d² 를 반환한다.",
    "langchain-chroma 는 이 거리를 0~1 스케일의 유사도로 변환하기 위해 1 − d/√2 공식을 "
    "적용한다.",
    "그러나 이 변환식은 d 의 최댓값을 √2(cosθ = 0, 즉 직교 상태)로 가정하고 설계된 식이다. "
    "실제 단위 벡터 공간에서 d² 의 최댓값은 4(d = 2)에 도달할 수 있다.",
    "따라서 코사인 유사도가 0.293 미만으로 떨어지면 d 가 √2 를 초과하게 되어 최종 점수가 "
    "음수로 산출된다.",
    "무관한 문서 간 코사인 유사도는 통상 0.05~0.25 사이에 분포하므로, 전체 검색 결과의 "
    "절반이 음수로 표기된 것이다.",
])
code([
    "cos =  1  (같은 방향)   ->  d² = 0",
    "cos =  0  (직교)        ->  d² = 2",
    "cos = -1  (정반대)      ->  d² = 4",
    "",
    "관측 최고  0.397  ->  d = 0.853  ->  코사인 0.573",
    "관측 최저 -0.307  ->  d = 1.848  ->  코사인 0.076",
])
p("거리 척도를 cosine 으로 명시하면 점수는 0~1 범위로 정규화되지만, 단위 벡터 간 L2 거리와 "
  "코사인 유사도는 단조 대응 관계이므로 검색 순위는 단 한 건도 변하지 않는다. 즉 거리 척도 "
  "변경은 점수의 해석 가능성을 복원하는 조치일 뿐 검색 품질 자체를 바꾸는 개선책은 아니다.")

# ═══════════════════════════════════════════════════════ 3
p("3. F207 ① 수집 문서에 적합한 내용 추출 방식", style="Heading 1")

p("3-1. 문제 현상 분석", style="Heading 2")
p("SSAFY_GUIDE.md 문서는 마크다운 표 셀 내부에 <br> 태그를 사용하여 다수의 세부 항목을 "
  "줄바꿈 없이 밀집 배치한 구조를 취하고 있다. 문서 내 <br> 태그가 116개 존재하며 최장 행의 "
  "길이는 615자에 달한다. RecursiveCharacterTextSplitter 의 기본 구분자는 HTML <br> 태그를 "
  "개행으로 인식하지 못하므로, 615자 분량의 복합 항목이 분할 알고리즘 기준에서 단일 텍스트 "
  "블록으로 처리되는 병목이 발생했다.")

p("3-2. 세 가지 전처리 방식의 성능 비교", style="Heading 2")
table([
    ["전처리 방식", "전처리 상세 내용", "총 문자 수", "청크 수", "최장 행"],
    ["md_raw", "현행 유지 (HTML 마크업 보존)", "9,153", "30", "615자"],
    ["txt_plain", "평문 전개 (<br> 을 실제 개행 문자로 치환)", "7,592", "18", "95자"],
    ["md_norm", "엔티티 제거 및 각 데이터 행마다 표 헤더 맥락 주입", "8,258", "24", "95자"],
], widths=[2.0, 6.2, 1.6, 1.1, 1.4], right_cols=[2, 3, 4])
table([
    ["전처리 방식", "Dense MRR", "BM25 MRR", "Hybrid MRR"],
    ["md_raw (현행)", "0.742", "0.867", "0.850"],
    ["txt_plain", "0.708", "0.850", "*0.933"],
    ["md_norm (직접 구성)", "0.734", "!0.750", "0.800"],
], widths=[5.4, 2.2, 2.2, 2.2], right_cols=[1, 2, 3], hl=2)
caption("표. 내용 추출 방식별 MRR 비교 (10문항, text-embedding-3-small 고정)")

p("3-3. 결과 분석 및 시사점", style="Heading 2")
p("<br> 태그를 개행 문자로 치환한 평문 전개(txt_plain) 방식이 하이브리드 검색 기준 MRR "
  "0.933, Recall@1 0.90 으로 가장 우수한 성능을 보였다. 개행이 정상화됨에 따라 분할기가 "
  "논리적 항목 경계에 맞춰 청크를 분할할 수 있게 되었고, 청크 수가 30개에서 18개로 "
  "압축되면서 각 청크의 주제적 응집도가 향상되었다.")
p("반면 표 헤더를 매 행마다 인위적으로 주입한 정규화(md_norm) 방식은 BM25 점수가 0.867 에서 "
  "0.750 으로 하락하는 역효과를 낳았다. '구분', '주요 내용', '비고'와 같은 일반 명사가 모든 "
  "청크에 반복 삽입되면서 역문서 빈도(IDF) 가중치가 왜곡되었고, 질의 판별에 기여하지 못한 채 "
  "청크 내 유효 정보 밀도만 저하시켰기 때문이다. 결론적으로 마크다운 표는 인위적인 메타데이터 "
  "주입보다 개행을 정리한 평문화가 검색에 유리하다.")

# ═══════════════════════════════════════════════════════ 4
p("4. F207 ② 문서 특성에 따른 청킹(Chunking) 최적화", style="Heading 1")

p("4-1. 초기 가설 검증 및 반증", style="Heading 2")
p("'명찰 재발급 비용' 질문에서 ContextRecall 과 ContextPrecision 이 모두 0으로 측정되었다. "
  "초기에는 615자 분량의 표가 분할되는 과정에서 재발급 비용 정보가 누락되었을 것이라 가설을 "
  "세웠으나, 청킹 산출물을 직접 확인한 결과 이 가설은 빗나갔다.")
code([
    "총 청크 30개 / 길이 min 40, median 340, max 492 / 500자 초과 0개",
    "",
    "정답 청크 #16 (401자) — 누락 없이 정상 보존 확인",
    "  ## 4. 보안 규정",
    "  ### 4-1. 교육장 입·출문 보안규정",
    "  ...",
    "      * 교육 명찰 분실 시 즉시 신고 및 분실 사유서 작성 후 재발급",
    "          * ※ 재발급 비용 약 16,500원 본인 부담",
    "      * 재발급 기간 동안 임시 교육 명찰 패용 (당일 반납 원칙)",
])
p("정답 텍스트는 상위 헤더와 함께 401자 크기의 청크 내에 온전히 유지되고 있었다. 즉 문제는 "
  "청킹 단계의 정보 손실이 아니라, 밀집 검색기가 해당 청크를 상위 5위권 내로 끌어올리지 못한 "
  "검색 알고리즘의 한계였다.")

p("4-2. 청크 크기별 격자 실험 결과", style="Heading 2")
table([
    ["청킹 파라미터", "청크 수", "Dense MRR", "BM25 MRR", "Hybrid MRR", "Dense R@5", "명찰 순위"],
    ["recursive-300", "49", "*0.867", "0.750", "0.808", "0.90", "*1위"],
    ["recursive-500 (현행)", "30", "0.742", "0.867", "*0.850", "0.90", "!6위"],
    ["recursive-1000", "13", "!0.646", "0.883", "0.775", "0.90", "3위"],
    ["markdown-500 (헤더 주입)", "30", "!0.645", "0.883", "0.850", "*1.00", "3위"],
], widths=[3.6, 1.0, 1.7, 1.7, 1.8, 1.5, 1.5], right_cols=[1, 2, 3, 4, 5, 6], hl=2)
figure("fig4_chunk_size.png",
       "청크 크기에 대한 세 검색 방식의 반응. Dense 와 BM25 가 상반된 방향으로 움직인다.",
       width=15.0)

p("4-3. 분석 및 상충 관계 (Trade-off)", style="Heading 2")
bullet("Dense 검색의 청크 크기 민감도: 청크 크기가 작을수록 Dense 검색 성능이 단조 "
       "증가했다(MRR 0.646 → 0.742 → 0.867). 청크가 커질수록 여러 주제가 단일 벡터로 "
       "평균화되어 특정 키워드에 대한 식별력이 약화되기 때문이다. 300자로 축소하자 명찰 "
       "질문의 Dense 순위가 6위에서 1위로 상승했다.")
bullet("BM25 검색의 반대 경향: 반면 BM25 는 청크가 커질수록 성능이 향상되는 정반대 양상을 "
       "보였다(MRR 0.750 → 0.867 → 0.883). 텍스트 길이가 길수록 질의 관련 어휘를 포함할 "
       "확률이 높아지기 때문이다.")
bullet("상호 보완에 따른 최적점 도출: 두 검색 방식의 특성이 상호 보완적으로 작용함에 따라, "
       "최종 하이브리드 검색 기준에서는 500자 설정이 MRR 0.850 으로 가장 균형 잡힌 성능을 "
       "나타냈다. 청크 크기는 단독으로 결정할 수 없으며 채택한 검색 방식에 맞춰 "
       "최적화해야 한다.")

# ═══════════════════════════════════════════════════════ 5
p("5. F207 ③ 평가 시스템을 활용한 다각적 성능 개선", style="Heading 1")

p("5-1. 검색 방식별 성능 비교 (recursive-500 고정)", style="Heading 2")
table([
    ["검색 방식", "Recall@1", "Recall@3", "Recall@5", "MRR", "명찰 질문 순위"],
    ["Dense 단독 (현행)", "0.60", "0.80", "0.90", "0.742", "!6위"],
    ["BM25 단독", "*0.80", "1.00", "1.00", "*0.867", "*1위"],
    ["하이브리드 (RRF 0.5:0.5)", "0.70", "*1.00", "*1.00", "0.850", "*2위"],
], widths=[4.4, 1.5, 1.5, 1.5, 1.8, 1.8], right_cols=[1, 2, 3, 4, 5], hl=3)
p("명찰 질문에서 Dense 검색은 6위에 그쳤으나 BM25 는 1위를 기록했다. 정답 청크에만 존재하는 "
  "고유 키워드('명찰', '재발급', '16,500', '분실')를 정밀하게 매칭한 결과다. rank_bm25 "
  "라이브러리는 이미 프로젝트 의존성에 포함되어 있었으나 실제 파이프라인에서 활용되지 않고 "
  "있었다.")
p("한국어 조사를 분리하는 정규식 기반 토크나이저도 시험했다. 형태소 분석기(KoNLPy, Kiwi 등)는 "
  "JVM 의존성과 빌드 부담을 고려하여 검토 대상에서 제외했다. 그러나 단순 공백 분리만으로도 "
  "이미 1위를 확보할 수 있었고, 조사 분리 방식은 동일 토큰을 중복 생성하여 스코어만 0.47 "
  "에서 8.52 로 팽창시켰을 뿐 최종 순위 변동에는 기여하지 않았다. 불필요한 복잡도 증가를 "
  "피하기 위해 채택하지 않았다.")

p("5-2. 임베딩 모델 비교 평가", style="Heading 2")
table([
    ["모델명", "벡터 차원", "Dense MRR", "Recall@5", "Recall@10", "명찰 질문 순위"],
    ["text-embedding-3-small", "1,536", "0.742", "0.90", "*1.00", "6위"],
    ["text-embedding-3-large", "3,072", "*0.788", "0.90", "!0.90", "!23위"],
], widths=[4.6, 1.4, 2.0, 1.3, 1.3, 2.2], right_cols=[1, 2, 3, 4, 5])
p("large 모델 적용 시 전체 MRR 은 소폭 상승했으나(0.742 → 0.788), 명찰 질문의 순위는 오히려 "
  "6위에서 23위로 급락했고 Recall@10 지표도 1.00 에서 0.90 으로 저하되었다. 집계 지표의 "
  "개선이 개별 질의의 개선을 보장하지 않음을 보여주는 사례다. 순위 급락의 원인은 본 실험에서 "
  "규명하지 않았으며, 2배 이상의 호출 비용을 고려하여 small 모델을 유지하기로 결정했다.")

p("5-3. 시스템 프롬프트 개선을 통한 거절 오류 제어", style="Heading 2")
p("현행 프롬프트의 다음 지시문이 복합 질의 응답을 저해하고 있었다.")
code(["[참고문서]에 없는 내용은 '문의 사항은 참고 문서에 없습니다.' 라고만 답하세요."])
p("질문 중 일부 내용만 문서에 기재되어 있는 경우, 모델이 정상적인 답변을 생성해 놓고도 문맥 "
  "말미에 거절 문구를 병기하는 결함이 발생했다.")
quote([("현행 프롬프트의 실제 응답 예시:  ", True, MUTED),
       ("예비군 훈련은 국가 관련 소집으로 공가로 처리됩니다. … 장기간 부재는 교육 담당자와 "
        "사전 면담 필요. ", False, INK),
       ("문의 사항은 참고 문서에 없습니다.", True, DOWN)])
table([
    ["프롬프트 버전", "거절 문구 출현", "완전 거절", "정상 답변 뒤 오병기"],
    ["A (현행)", "3 / 10", "1", "!2"],
    ["B (규칙 분리)", "*0 / 10", "0", "*0"],
], widths=[5.0, 3.0, 2.0, 3.4], right_cols=[1, 2, 3], hl=2)
p("개선된 프롬프트 B 에서는 지시문을 세분화했다. 질문의 모든 항목이 문서에 부재할 때에만 "
  "단독 거절하도록 제한하고, 일부 항목만 확인되는 경우에는 확인된 사실을 우선 서술한 뒤 "
  "누락된 항목에 대해서만 부재 사실을 명시하도록 역할을 분리했다.")

p("5-4. Ragas 종합 정량 평가 결과", style="Heading 2")
p("LLM 판정의 편차를 보정하기 위해 조건별 3회 반복 측정을 수행하여 평균과 표준편차를 "
  "집계했다.")
table([
    ["실험 조건", "Faithfulness", "AnswerRelevancy", "ContextRecall", "ContextPrecision"],
    ["A. 현행 파이프라인", "0.954 ± .031", "0.537 ± .027", "0.900 ± .000", "0.671 ± .005"],
    ["B. 프롬프트만 개선", "0.941 ± .052", "*0.632 ± .014", "0.900 ± .000", "0.666 ± .028"],
    ["C. 하이브리드 검색 + 프롬프트", "0.967 ± .016", "0.565 ± .019", "*1.000 ± .000",
     "*0.819 ± .005"],
], widths=[4.6, 2.5, 2.7, 2.5, 2.7], right_cols=[1, 2, 3, 4], hl=3)
figure("fig5_ragas_ab.png",
       "조건별 Ragas 점수. 오차막대는 3회 반복의 표준편차이다. ContextRecall 의 오차막대가 "
       "보이지 않는 것은 표준편차가 0 이기 때문이다.", width=16.6)
table([
    ["기준선(A) 대비 변화량", "Faithfulness", "AnswerRelevancy", "ContextRecall",
     "ContextPrecision"],
    ["B (프롬프트 개선)", "−0.013 (오차 범위)", "*+0.094 (유의미)", "±0.000 (동일)",
     "−0.005 (오차 범위)"],
    ["C (하이브리드 결합)", "+0.012 (오차 범위)", "+0.028 (오차 범위)", "*+0.100 (유의미)",
     "*+0.149 (유의미)"],
], widths=[4.6, 2.5, 2.7, 2.5, 2.7], right_cols=[1, 2, 3, 4])
p("유의성 판정 기준은 변화량의 절댓값이 표준편차의 2배를 초과하고 동시에 0.05 이상인 경우로 "
  "설정했다.", size=9.5, color=MUTED, space_after=12)

p("5-5. 평가 결과 해석", style="Heading 2")
num([
    "프롬프트만 개선한 조건 B 는 검색을 수정하지 않았으므로 ContextRecall 이 "
    "0.900(표준편차 0.000)으로 오차 없이 동일하게 유지된 반면, 비정상적 거절 문구가 "
    "제거되면서 AnswerRelevancy 만 유의미하게 상승했다(+0.094).",
    "검색 파이프라인을 하이브리드로 교체한 조건 C 는 검색 단계 지표인 ContextRecall 과 "
    "ContextPrecision 을 동시에 크게 개선했다.",
    "Faithfulness 는 세 조건 모두 표준편차 내에서 변동하여 통계적으로 유의미한 차이가 "
    "관측되지 않았다.",
    "조건 C 의 AnswerRelevancy(0.565)가 조건 B(0.632)보다 낮은 이유는 검색 결과의 변화로 "
    "인해 답변 생성 내용이 달라졌기 때문이다. 이는 단일 파이프라인의 개선이 모든 지표의 "
    "동반 상승으로 직결되지는 않음을 보여준다.",
])

# ═══════════════════════════════════════════════════════ 6
p("6. 파이프라인 호출 구조 및 지연 시간 계측", style="Heading 1")
p("LangChain 콜백 핸들러를 파이프라인에 부착하여 /chat 엔드포인트 1회 호출 시의 단계별 소요 "
  "시간과 리소스 소비를 측정했다. LangSmith 와 동일한 인터페이스이며, 결과를 외부로 전송하지 "
  "않고 로컬에 기록했다.")
figure("fig1_call_flow.png",
       "/chat 요청 1회의 호출 분해. 브라우저는 OpenAI 를 직접 호출하지 않으며 API 키는 "
       "FastAPI 서버에만 존재한다. use_rag 가 false 이면 retrieve 를 건너뛰어 외부 호출이 "
       "1회로 감소한다.")

p("6-1. RAG 실행 트리 프로파일링", style="Heading 2")
code([
    "use_rag=True (RAG 경로)   총 소요 시간: 4,275 ms",
    "  [chain] LangGraph                      4274.9 ms",
    "  ├─ [chain] __start__                      0.2 ms",
    "  │  ├─ [chain] route_by_rag_flag            0.0 ms",
    "  ├─ [chain] retrieve                     376.3 ms   (임베딩 API + 로컬 벡터 검색)",
    "  ├─ [chain] generate                    3897.3 ms   (전체 지연의 91%)",
    "  │  ├─ [chain] RunnableSequence          3894.8 ms",
    "  │  │  ├─ [chain] ChatPromptTemplate        0.2 ms",
    "  │  │  ├─ [llm]   ChatOpenAI             3894.3 ms",
    "  │  │  │          입력 1,120 토큰 / 출력 274 토큰",
])
p("RAG 실행 지연 4,275 ms 의 91%인 3,897 ms 가 생성 단계에서 발생했다. retrieve 에 소요된 "
  "376 ms 는 대부분 질문 임베딩 API 의 왕복 네트워크 지연이며, Chroma 로컬 벡터 검색 시간은 "
  "이 구간에 포함되어 별도로 분리 측정하지 않았다. LangGraph 의 라우팅 오버헤드는 "
  "0.0~0.2 ms 로 실측되어 사실상 무시할 수 있는 수준이었다.")

p("6-2. RAG 경로와 일반 생성 경로의 비교", style="Heading 2")
table([
    ["호출 경로", "외부 API 호출", "프롬프트 길이", "입력 토큰", "출력 토큰", "전체 지연"],
    ["RAG 경로 (use_rag = True)", "2회", "1,909자", "1,120", "*274", "*4,275 ms"],
    ["일반 경로 (use_rag = False)", "1회", "106자", "70", "!792", "!9,711 ms"],
], widths=[4.4, 1.8, 1.8, 1.6, 1.6, 2.0], right_cols=[1, 2, 3, 4, 5])
figure("fig6_latency.png",
       "두 경로의 지연 구성. 짙은 구간이 생성 단계, 옅은 구간이 검색 단계이다.", width=16.0)
p("RAG 를 적용한 경로가 일반 경로 대비 약 2.3배 빠른 응답 속도를 기록했다. 외부 API 호출이 "
  "1회 추가되고 프롬프트 길이가 18배, 입력 토큰이 16배 증가했음에도 이러한 역전 현상이 "
  "발생한 원인은 출력 토큰 수의 대폭 감소(792 → 274)에 있다.")
p("LLM 추론 지연 시간은 일괄 처리되는 입력 토큰보다 자기회귀(Autoregressive) 방식으로 순차 "
  "생성되는 출력 토큰 수에 의해 지배된다. 명확한 컨텍스트 문서가 주어지면 모델이 핵심 사실만 "
  "간결하게 요약하여 출력하므로, 배경지식에 의존하여 장문의 원론적 설명을 나열할 때보다 지연 "
  "시간과 토큰 비용이 함께 절감된다.")

# ═══════════════════════════════════════════════════════ 7
p("7. F208 ① 업로드 문서에 따른 AI 응답 변화 분석", style="Heading 1")
p("동일한 질문, 모델, 프롬프트를 유지한 상태에서 참조 가능한 문서 인덱스 상태만을 변경하며 "
  "응답 양상을 분석했다.")
table([
    ["상태", "조건"],
    ["S1", "RAG 미사용 — 순수 LLM 사전 학습 지식 기반"],
    ["S2", "RAG 적용 — SSAFY 교육 규정집만 색인된 상태"],
    ["S3", "RAG 적용 — 청년월세 안내 가이드를 신규 업로드하여 색인한 상태"],
], widths=[1.6, 10.4])

p("7-1. 질의응답 비교", style="Heading 2")
p("질문: 국토교통부 청년월세 한시 특별지원은 최대 몇 개월 동안 총 얼마까지 받을 수 있나요? "
  "(공식 정답: 최대 24개월, 총 480만 원)", size=10, color=MUTED)
table([
    ["상태", "생성된 응답 내용", "판정"],
    ["S1", "「과거 사례: 한시성 청년 월세 지원은 흔히 3~6개월 범위로 지급된 경우가 많고, "
           "총액은 지자체·정책에 따라 수십만 원에서 100만원대까지 차이가 있었습니다.」",
     "!그럴듯하나 허위 정보"],
    ["S2", "「문의 사항은 참고 문서에 없습니다.」", "*정확한 지식 부재 인정"],
    ["S3", "「국토교통부 청년월세 한시 특별지원은 최대 24개월간, 총 480만원(월 최대 20만원)까지 "
           "받을 수 있습니다.」", "*정확한 사실 인용"],
], widths=[1.3, 8.5, 2.4], hl=3)

p("7-2. 응답 양상 분석", style="Heading 2")
bullet("S1: 정중하고 설득력 있는 문장 구조를 갖추었으나 실제 사실과 전혀 다른 수치('3~6개월, "
       "100만원대')를 생성했다. 정중한 어조와 무관하게 허위 정보가 그대로 생성된 사례이며, "
       "사전 지식에만 의존할 때 발생하는 전형적인 환각 현상이다.")
bullet("S2: 보유 문서에 해당 정보가 없음을 정확히 인식하고 답변 생성을 거절했다. 불확실한 "
       "지식을 임의로 생성하지 않고 거절하는 것은 RAG 도입의 핵심적인 실질적 효용이다.")
bullet("S3: 신규 문서를 업로드하는 것만으로 모델 재학습이나 코드 수정 없이 정책의 정확한 "
       "수치(24개월, 480만 원)를 즉각 도출했다. 서울시(8,000만 원 / 60만 원)와 "
       "국토교통부(5,000만 원 / 70만 원)의 상이한 요건 또한 오류 없이 구분했다.")

p("7-3. 컨텍스트 혼입에 의한 응답 오염 관측", style="Heading 2")
quote([("질문:  ", True, MUTED),
       ("인천에 사는 37세 청년인데 청년월세 지원을 어디에 신청해야 하나요?", False, INK)])
quote([("S3 응답:  ", True, MUTED),
       ("만 35세~39세 구간에 해당하므로 인천시 자체 사업으로 접수합니다. 인천청년포털 온라인 "
        "신청 또는 행정복지센터 방문하여 신청하세요.  ", False, INK),
       ("문의: 청년월세지원센터 1833-2030 / 다산콜센터 120", True, DOWN)])
p("앞선 두 문장은 사실에 부합한다. 그러나 마지막에 덧붙여진 연락처는 문서 내 서울시 지원 "
  "사업 절에만 기재된 고유 번호이다. 상위 5개 검색 결과 내에 서울시 관련 청크가 포함되면서 "
  "생성 모델이 이를 동일한 정책 맥락으로 오인하여 인천 정책 답변에 병합한 컨텍스트 간 간섭 "
  "현상이 확인되었다.")

# ═══════════════════════════════════════════════════════ 8
p("8. F208 ② 유사도 기준과 문서 분할 방식이 결과에 미친 영향", style="Heading 1")

p("8-1. 스코어링 체계의 한계와 거리 척도의 실질적 영향", style="Heading 2")
p("Chroma 의 hnsw:space 메타데이터가 미지정된 상태에서는 L2 공간이 기본 적용되며, 전체 "
  "점수의 50.7%가 음수 영역에 분포했다. 주목할 점은 거리 척도 수정이 검색 순위 자체에는 "
  "영향을 미치지 않는다는 사실이다. 거리 척도를 cosine 으로 명시하면 점수가 0~1 사이로 "
  "정상 표기되지만, 단위 벡터 간 L2 거리와 코사인 유사도는 단조 대응 관계를 형성하므로 "
  "10개 문항 전체에서 순위 변동은 단 한 건도 발생하지 않았다. 따라서 거리 척도 수정은 "
  "수치를 해석 가능하게 만드는 조치일 뿐 검색 순위의 질적 개선과는 무관하다.")
figure("fig3_l2_negative.png",
       "코사인 유사도와 relevance score 의 관계. 코사인 0.293 미만 구간은 모두 음수로 "
       "산출된다. 무관한 청크의 코사인은 통상 0.1 부근에 분포하므로 전체의 절반이 음수 "
       "구간에 포함된다.", width=15.0)

p("8-2. 유사도 임계값(Threshold) 필터링의 한계", style="Heading 2")
table([
    ["유사도 임계값", "통과 청크 수 (평균)", "정답 통과 질문 수", "정답 차단 질문 수"],
    ["0.00", "14.8", "10", "0"],
    ["0.05", "10.7", "10", "0"],
    ["0.10", "7.4", "10", "0"],
    ["0.15", "4.9", "10", "0"],
    ["0.20", "2.4", "8", "!2"],
    ["0.25", "1.5", "7", "!3"],
], widths=[3.0, 3.4, 3.0, 3.0], right_cols=[0, 1, 2, 3])
p("질의별 1위 청크와 정답 청크 간의 점수 격차는 대다수 0.00~0.02 이내에 머물렀으며 최대 "
  "격차도 0.108 에 불과했다. 이처럼 점수의 동적 범위가 극도로 좁기 때문에, 유효한 정답을 "
  "보존하면서 노이즈 문서만 배제하는 단일 임계값을 설정하는 것은 불가능하다.")

p("8-3. 임계값 필터링과 Top-k 절단의 비대체성", style="Heading 2")
p("임계값을 0.15 로 설정하면 평균 4.9개의 청크가 통과하고 10개 문항의 정답 청크가 모두 "
  "생존한다. 그러나 명찰 질문의 정답 청크는 여전히 6위에 머물러 있으므로 상위 5개를 취하는 "
  "k=5 절단 조건에서 누락된다.")
table([
    ["검색 Top-k", "정답 포함 비율", "컨텍스트 총 길이", "특이사항"],
    ["3", "8 / 10", "약 1,020자", "주요 질의 2건 누락"],
    ["5 (현행)", "9 / 10", "약 1,700자", "명찰 질문 누락"],
    ["8", "*10 / 10", "약 2,720자", "무관한 노이즈 청크 증가"],
    ["10", "*10 / 10", "약 3,400자", "무관한 노이즈 청크 증가"],
], widths=[2.0, 2.4, 3.0, 4.6], right_cols=[0, 1, 2], hl=3)
p("임계값은 낮은 점수의 문서를 제거할 뿐 청크의 상대적 순위를 상승시키지 못한다. 정답 청크를 "
  "상위 k 이내로 견인하는 역할은 검색 방식이 담당해야 하며, 실제로 하이브리드 검색을 "
  "도입함으로써 k=5 조건에서 10/10 정답 포섭을 달성할 수 있었다.")

p("8-4. 문서 분할 방식과 검색 방식의 결합 관계", style="Heading 2")
p("앞서 검증한 바와 같이 청크 크기는 Dense 검색과 BM25 검색에 정반대의 영향을 미친다. 현행 "
  "500자 설정은 Dense 검색 단독으로는 최적치가 아니었으나(300자가 MRR 0.867 로 우세), 두 "
  "검색을 결합한 하이브리드 환경에서는 500자가 최적의 균형점(MRR 0.850)을 형성했다. 따라서 "
  "문서 분할 파라미터는 검색 방식과 연계하여 결정해야 한다.")

# ═══════════════════════════════════════════════════════ 9
p("9. F208 ③ RAG 방식의 실증적 장점과 한계", style="Heading 1")

p("9-1. 실측 기반 주요 장점", style="Heading 2")
num([
    "지식 부재 시 환각 억제 및 거절 응답 생성: 사전 지식에 의존할 때 발생하는 설득력 있는 "
    "오답을 억제하고, 정보 부재 시 답변을 거절하도록 유도한다.",
    "출처 명시를 통한 사실 검증 지원: 생성된 답변에 기반 문서(YOUTH_RENT_GUIDE.md)를 "
    "명시함으로써 최종 사용자가 정보의 사실 여부를 직접 교차 검증할 수 있는 투명성을 "
    "확보한다.",
    "모델 재학습 없는 신속한 도메인 지식 전환: 모델의 파라미터 업데이트나 프롬프트 변경 없이 "
    "신규 문서 파일 추가만으로 전문 정책 질의에 대한 정확한 수치 응답을 실현한다.",
    "응답 지연 시간 및 토큰 비용 절감: 명확한 컨텍스트 제공을 통해 모델의 불필요한 장황 "
    "서술을 차단함으로써 출력 토큰 수를 65% 감축(792 → 274)시키고 응답 속도를 2.3배 "
    "향상시킨다.",
])

p("9-2. 실측 기반 구조적 한계", style="Heading 2")
num([
    "밀집 벡터 압축에 따른 고유 식별자 변별력 희석: 문장 전체를 단일 벡터로 투영하는 "
    "과정에서 수치와 고유명사 등의 세부 정보가 평활화되어 키워드 매칭 중심 질의에서 순위가 "
    "하락한다.",
    "유사도 스코어 기반 품질 판정의 불확실성: 거리 척도 변환의 한계로 인한 음수 스코어 "
    "발생과 청크 간 점수 편차 협소(0.02 이내)로 인해 정적 임계값에 기반한 품질 필터링이 "
    "불가능하다.",
    "인접 검색 컨텍스트에 의한 답변 오염: 질의와 무관한 청크가 상위 k 내에 혼입될 경우 "
    "LLM 이 이를 동일 맥락으로 취급하여 오답을 병합 생성한다(예: 인천 질의에 서울시 연락처 "
    "병기).",
    "엄격한 환각 방지 지침의 부작용: '문서에 없으면 없다고만 답하라'는 배타적 시스템 지침은 "
    "복합 질문 상황에서 정상 답변을 완료한 후에도 후미에 거절 문구를 중복 표기하게 만든다.",
    "대규모 임베딩 모델의 비일관적 성능: 상위 모델(large) 적용 시 평균 MRR 은 상승했으나 "
    "특정 질의의 순위가 6위에서 23위로 급락하는 현상이 관측되었다. 고사양 모델이 모든 개별 "
    "질의의 개선을 보장하지는 않는다.",
    "평가 하네스 자체의 잠재 결함: 평가 스크립트의 데이터 전달 규격 오류로 인해 주요 "
    "지표(ContextPrecision)가 무력화된 상태에서도 수치 자체는 정상 산출되는 맹점이 "
    "확인되었다. 평가 파이프라인의 결함은 지표 수치만으로는 감지되지 않는다.",
])

# ═══════════════════════════════════════════════════════ 10
p("10. F208 ④ 시스템 고도화를 위한 추가 개선 방안", style="Heading 1")
num([
    "검색 실패 시 일반 대화 모드로의 동적 Fallback 라우팅: 검색 결과가 부재할 경우 일반 AI "
    "모드임을 명시하도록 요구하는 사양(F206)을 충족하기 위해, 스코어 임계값 대신 BM25 "
    "스코어가 0이면서 상위 Dense 스코어 편차가 미미한 구간을 검색 실패로 감지하는 조건부 "
    "라우팅 노드를 LangGraph 에 추가한다.",
    "교차 인코더(Cross-Encoder) 기반 재순위화 도입: 하이브리드 검색을 통해 Recall@5 는 "
    "1.00 을 달성했으나 Recall@1 은 0.70 에 머물러 있다. 정답 청크의 1위 배치를 보장하기 "
    "위해 2단계 재순위화 모델 도입이 유효하며, CPU 지연 시간을 고려한 경량 모델 선별이 "
    "필요하다.",
    "토큰 단위 스트리밍 인터페이스 적용: 지연 시간 계측 결과 전체 지연의 91%가 LLM 생성 "
    "단계에 집중되어 있다. FastAPI 의 StreamingResponse 와 LangGraph 의 .stream() 메서드를 "
    "연동하여 첫 토큰 도착 시간을 단축하고 체감 응답성을 개선한다.",
    "클라이언트 예외 처리 강화: 프론트엔드(script.js)에서 response.ok 상태를 검증하지 않아 "
    "4xx/5xx 서버 오류 시 undefined 가 렌더링되는 결함을 보완하고, F201 규격에 맞춘 오류 "
    "안내 UI 를 구성한다.",
    "검색 근거 청크의 UI 투명성 제공: 현재 백엔드 콘솔에만 출력되는 참조 청크 본문과 검색 "
    "스코어를 화면에 접기·펼치기 형태로 노출하여, 사용자가 AI 응답의 사실 근거를 능동적으로 "
    "확인할 수 있도록 구현한다.",
    "관측 도구(LangSmith) 연동: 이미 의존성에 포함된 LangSmith 를 환경 변수만으로 활성화하여 "
    "토큰 소비량, 지연 병목, 질의 실패 패턴을 추적한다. 다만 문서 본문과 질의가 외부 "
    "서비스로 전송되므로 대외비 자료를 다룰 때에는 별도의 판단이 필요하다.",
])

# ═══════════════════════════════════════════════════════ 11
p("11. 실험 재현 절차", style="Heading 1")
code([
    "experiments/",
    "  corpus/YOUTH_RENT_GUIDE.md        직접 수집한 청년월세 가이드 문서",
    "  corpus/SSAFY_GUIDE_normalized.md  정규화 실험 산출물",
    "  run_retrieval.py                  청킹·임베딩·검색 방식 격자 실험",
    "  run_threshold.py                  거리 척도 및 임계값·k 파라미터 스윕",
    "  run_extraction.py                 내용 추출 방식 3종 비교",
    "  run_ragas_ab.py                   A/B/C 조건 Ragas 평가 (RUN_ID 반복)",
    "  run_document_ab.py                문서 교체 전·후 응답 비교",
    "  trace_calls.py                    호출 트리 및 지연 계측",
    "  aggregate.py                      3회 반복 측정 평균 및 표준편차 집계",
    "  make_figures.py                   보고서 그림 생성",
    "  make_docx.py                      본 보고서 생성",
    "  results/                          측정 데이터셋 (json/csv)",
])
code([
    "# PowerShell",
    "Set-Location C:\\SSAFY\\chatbot-project_lab",
    "$py = 'servers\\.venv\\Scripts\\python.exe'",
    "",
    "& $py experiments\\run_retrieval.py",
    "& $py experiments\\run_threshold.py",
    "& $py experiments\\run_extraction.py",
    "& $py experiments\\run_document_ab.py",
    "& $py experiments\\trace_calls.py",
    "1..3 | ForEach-Object { $env:RUN_ID = $_; & $py experiments\\run_ragas_ab.py }",
    "& $py experiments\\aggregate.py",
])
p("임베딩 연산 결과는 results/_emb_cache.json 에 캐싱되므로 재실행 시 중복 API 호출이 "
  "발생하지 않는다. LLM 기반 Ragas 평가는 조건당 약 160초에서 310초가 소요된다.")

# ═══════════════════════════════════════════════════════ 12
p("12. 참고 자료 및 데이터 출처", style="Heading 1")
table([
    ["제공 기관 및 정책명", "공식 웹사이트 주소"],
    ["인천광역시 청년포털 청년월세 지원사업",
     "https://youth.incheon.go.kr/dwelling/monthly.jsp"],
    ["서울주거포털 청년월세지원 사업개요",
     "https://housing.seoul.go.kr/site/main/content/sh01_060513"],
    ["토스피드 청년월세 특별지원 조건과 신청방법",
     "https://toss.im/tossfeed/article/rent-support-policy"],
    ["경기도 청년월세 한시 특별지원",
     "https://www.gg.go.kr/contents/contents.do?ciIdx=1366&menuId=3171"],
], widths=[5.4, 6.6], size=9)

# ── 바닥글 쪽번호 ──────────────────────────────────────────────
foot = doc.sections[0].footer.paragraphs[0]
foot.alignment = AL.CENTER
field(foot, "PAGE")
for r in foot.runs:
    r.font.name = KR
    r.font.size = Pt(9)
    r.font.color.rgb = MUTED

doc.save(OUTP)
print(f"저장: {OUTP}  (그림 {_fig[0]}장)")
