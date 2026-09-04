# -*- coding: utf-8 -*-
"""
F208 ① "업로드한 문서에 따라 AI 응답이 어떻게 달라졌는지" 실험

같은 질문 / 같은 모델 / 같은 프롬프트를 고정하고, 참조 가능한 문서만 바꾼다.
  S1  RAG 끄기            -> 모델의 사전지식만
  S2  RAG 켜기 + 규정집만  -> 관련 문서가 없는 상태
  S3  RAG 켜기 + 청년월세  -> 문서를 올린 뒤
"""
import os, sys, json
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\SSAFY\chatbot-project_lab")
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv(ROOT / "servers" / ".env")

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
sys.path.insert(0, str(ROOT / "experiments"))
from run_retrieval import embed, split_recursive

OUT = ROOT / "experiments" / "results"
K = 5

GUIDE = (ROOT / "data" / "SSAFY_GUIDE.md").read_text(encoding="utf-8")
RENT = (ROOT / "experiments" / "corpus" / "YOUTH_RENT_GUIDE.md").read_text(encoding="utf-8")

QUESTIONS = [
    "국토교통부 청년월세 한시 특별지원은 최대 몇 개월 동안 총 얼마까지 받을 수 있나요?",
    "서울시 청년월세지원과 국토교통부 한시 특별지원의 보증금·월세 요건은 각각 어떻게 다른가요?",
    "인천에 사는 37세 청년인데 청년월세 지원을 어디에 신청해야 하나요?",
]

RAG_PROMPT = ChatPromptTemplate.from_messages([
    ("system",
     "당신은 SSAFY 교육 과정을 돕는 AI 어시스턴트입니다.\n"
     "아래 [참고문서]에 적힌 내용만 근거로 사용자의 질문에 답변하세요.\n"
     "질문의 어떤 항목도 문서에서 찾을 수 없을 때에만 "
     "'문의 사항은 참고 문서에 없습니다.'라고 답하세요.\n"
     "문서에 없는 내용을 추측해서 채우지 마세요.\n\n[참고문서]\n\n{context}"),
    ("user", "{question}")])
GEN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", "당신은 SSAFY 교육 과정을 돕는 친절한 AI 어시스턴트입니다. "
               "사용자 질문에 대해 최선을 다해 친절하게 답변해주세요."),
    ("user", "{question}")])

llm = ChatOpenAI(model=os.getenv("GPT_MODEL", "gpt-5-mini"),
                 api_key=os.getenv("API_KEY"), base_url=os.getenv("base_url"))

def build(texts):
    chunks = []
    for name, t in texts:
        for c in split_recursive(t, 500):
            chunks.append((name, c))
    M = embed([c for _, c in chunks], "text-embedding-3-small")
    return chunks, M / np.linalg.norm(M, axis=1, keepdims=True)

QV = embed(QUESTIONS, "text-embedding-3-small")
QV = QV / np.linalg.norm(QV, axis=1, keepdims=True)

STATES = {
    "S1_rag_off":        None,
    "S2_guide_only":     [("SSAFY_GUIDE.md", GUIDE)],
    "S3_rent_uploaded":  [("SSAFY_GUIDE.md", GUIDE), ("YOUTH_RENT_GUIDE.md", RENT)],
}

out = {}
for sname, corpus in STATES.items():
    print(f"\n===== {sname} =====")
    out[sname] = []
    if corpus is None:
        for i, q in enumerate(QUESTIONS):
            ans = (GEN_PROMPT | llm).invoke({"question": q}).content
            out[sname].append(dict(question=q, sources=[], answer=ans))
            print(f"\nQ. {q}\nA. {ans[:300]}")
    else:
        chunks, M = build(corpus)
        for i, q in enumerate(QUESTIONS):
            idx = np.argsort(-(M @ QV[i]))[:K]
            ctx = "\n\n".join(chunks[j][1] for j in idx)
            srcs = sorted({chunks[j][0] for j in idx})
            ans = (RAG_PROMPT | llm).invoke({"context": ctx, "question": q}).content
            out[sname].append(dict(question=q, sources=srcs, answer=ans))
            print(f"\nQ. {q}\n   출처: {srcs}\nA. {ans[:300]}")

(OUT / "document_ab.json").write_text(json.dumps(out, ensure_ascii=False, indent=2),
                                      encoding="utf-8")
print(f"\n저장: {OUT / 'document_ab.json'}")
