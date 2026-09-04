# -*- coding: utf-8 -*-
"""
F207 ③ 개선 조치별 Ragas A/B

조건을 한 번에 하나씩만 바꿔서, 어떤 조치가 어떤 지표를 움직였는지 분리한다.
  A  : 현행 (dense k=5, 원본 프롬프트)
  B  : A + 프롬프트만 수정
  C  : B + 검색을 하이브리드(BM25+dense RRF)로 교체
"""
import os, sys, json, re, time
from pathlib import Path
import numpy as np

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\SSAFY\chatbot-project_lab")
os.chdir(ROOT)
from dotenv import load_dotenv
load_dotenv(ROOT / "servers" / ".env")

# gpt-5-mini 는 temperature 를 받지 않는다. ragas 내부 호출까지 막아야 한다.
import openai
_oc = openai.resources.chat.completions.Completions.create
def _safe(self, *a, **k):
    k.pop("temperature", None)
    return _oc(self, *a, **k)
openai.resources.chat.completions.Completions.create = _safe
_oa = openai.resources.chat.completions.AsyncCompletions.create
async def _safea(self, *a, **k):
    k.pop("temperature", None)
    return await _oa(self, *a, **k)
openai.resources.chat.completions.AsyncCompletions.create = _safea

from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from rank_bm25 import BM25Okapi

sys.path.insert(0, str(ROOT / "experiments"))
from run_retrieval import embed, QUESTIONS, split_recursive, tok, rrf

OUT = ROOT / "experiments" / "results"
K = 5

text = (ROOT / "data" / "SSAFY_GUIDE.md").read_text(encoding="utf-8")
chunks = split_recursive(text, 500)
qs = [q["question"] for q in QUESTIONS]
gts = [q["ground_truth"] for q in QUESTIONS]

M = embed(chunks, "text-embedding-3-small"); M /= np.linalg.norm(M, axis=1, keepdims=True)
Q = embed(qs, "text-embedding-3-small");     Q /= np.linalg.norm(Q, axis=1, keepdims=True)
BM = BM25Okapi([tok(c) for c in chunks])

def retrieve_dense(i):
    return [chunks[j] for j in np.argsort(-(M @ Q[i]))[:K]]

def retrieve_hybrid(i):
    d = list(np.argsort(-(M @ Q[i])))
    b = list(np.argsort(-BM.get_scores(tok(qs[i]))))
    return [chunks[j] for j in rrf([b, d], [0.5, 0.5])[:K]]

PROMPT_ORIG = ChatPromptTemplate.from_messages([
    ("system",
     "당신은 SSAFY 교육 과정을 돕는 AI 어시스턴트입니다.\n"
     "아래의 [참고 문서] 내용을 바탕으로 사용자의 질문에 답변하세요.\n"
     "답변은 필요한 말만 두괄식으로 간략하게 하세요. 불필요한 서론은 생략하세요.\n"
     "[참고문서]에 없는 내용은 '문의 사항은 참고 문서에 없습니다.' 라고만 답하세요.\n\n"
     "[참고문서]\n\n{context}"),
    ("user", "{question}")])

PROMPT_FIXED = ChatPromptTemplate.from_messages([
    ("system",
     "당신은 SSAFY 교육 과정을 돕는 AI 어시스턴트입니다.\n"
     "아래 [참고문서]에 적힌 내용만 근거로 사용자의 질문에 답변하세요.\n\n"
     "[작성 규칙]\n"
     "1. 질문이 여러 항목을 묻는 경우, 문서에서 확인되는 항목을 각각 답하세요.\n"
     "2. 문서에서 확인되는 내용은 수치와 조건을 빠뜨리지 말고 답변에 포함하세요.\n"
     "3. 질문의 어떤 항목도 문서에서 찾을 수 없을 때에만 "
     "'문의 사항은 참고 문서에 없습니다.'라고 답하세요.\n"
     "4. 일부 항목만 확인되면 확인된 항목을 먼저 answer하고, "
     "확인되지 않은 항목에 대해서만 문서에 없다고 덧붙이세요.\n"
     "5. 문서에 없는 내용을 추측해서 채우지 마세요.\n\n"
     "[참고문서]\n\n{context}"),
    ("user", "{question}")])

CONDITIONS = {
    "A_baseline":      (retrieve_dense,  PROMPT_ORIG),
    "B_prompt_fix":    (retrieve_dense,  PROMPT_FIXED),
    "C_hybrid+prompt": (retrieve_hybrid, PROMPT_FIXED),
}

llm = ChatOpenAI(model=os.getenv("GPT_MODEL", "gpt-5-mini"),
                 api_key=os.getenv("API_KEY"), base_url=os.getenv("base_url"))

from ragas import EvaluationDataset, evaluate
from ragas.metrics import Faithfulness, AnswerRelevancy, LLMContextRecall, ContextPrecision
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_openai import OpenAIEmbeddings
rl = LangchainLLMWrapper(llm)
re_ = LangchainEmbeddingsWrapper(OpenAIEmbeddings(
    model="text-embedding-3-small", api_key=os.getenv("API_KEY"), base_url=os.getenv("base_url")))

def run(cond):
    retriever, prompt = CONDITIONS[cond]
    rows = []
    for i, q in enumerate(qs):
        ctxs = retriever(i)
        ans = (prompt | llm).invoke({"context": "\n\n".join(ctxs), "question": q}).content
        rows.append(dict(user_input=q, response=ans, retrieved_contexts=ctxs, reference=gts[i]))
        print(f"  [{cond}] {i+1}/10 완료", flush=True)
    ds = EvaluationDataset.from_list(rows)
    res = evaluate(dataset=ds,
                   metrics=[Faithfulness(llm=rl), AnswerRelevancy(llm=rl, embeddings=re_),
                            LLMContextRecall(llm=rl), ContextPrecision(llm=rl)],
                   llm=rl, embeddings=re_)
    df = res.to_pandas()
    return rows, df

if __name__ == "__main__":
    only = sys.argv[1:] or list(CONDITIONS)
    summary = {}
    for cond in only:
        t0 = time.time()
        print(f"\n=== {cond} ===", flush=True)
        rows, df = run(cond)
        cols = ["faithfulness", "answer_relevancy", "context_recall", "context_precision"]
        rid = os.getenv("RUN_ID", "1")
        summary[f"{cond}#{rid}"] = {c: float(df[c].mean()) for c in cols}
        df.to_csv(OUT / f"ragas_{cond}_r{rid}.csv", index=False, encoding="utf-8-sig")
        (OUT / f"answers_{cond}_r{rid}.json").write_text(
            json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"  -> {summary[f'{cond}#{rid}']}  ({time.time()-t0:.0f}s)", flush=True)
    p = OUT / "ragas_summary.json"
    prev = json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}
    prev.update(summary)
    p.write_text(json.dumps(prev, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n저장:", p)
