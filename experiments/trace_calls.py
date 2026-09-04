# -*- coding: utf-8 -*-
"""
/chat 요청 한 건이 실제로 어떤 호출로 분해되는지 계측한다.

LangSmith 트레이서와 같은 LangChain 콜백 인터페이스를 쓴다.
차이는 결과를 클라우드로 보내지 않고 로컬 JSON 으로 남긴다는 점뿐이다.
"""
import os, sys, json, time
from pathlib import Path
from typing import Any
from uuid import UUID

sys.stdout.reconfigure(encoding="utf-8")
ROOT = Path(r"C:\SSAFY\chatbot-project_lab")
os.chdir(ROOT)
sys.path.insert(0, str(ROOT / "servers"))
from dotenv import load_dotenv
load_dotenv(ROOT / "servers" / ".env")

from langchain_core.callbacks import BaseCallbackHandler
from langchain_openai import ChatOpenAI, OpenAIEmbeddings
import main

OUT = ROOT / "experiments" / "results"


class RunTree(BaseCallbackHandler):
    """실행 트리를 run_id/parent_run_id 로 재구성한다."""

    def __init__(self):
        self.nodes: dict[str, dict] = {}
        self.order: list[str] = []

    def _open(self, kind, name, run_id, parent_run_id, payload=None):
        rid = str(run_id)
        self.nodes[rid] = dict(kind=kind, name=name, parent=str(parent_run_id) if parent_run_id else None,
                               t0=time.perf_counter(), ms=None, payload=payload or {}, children=[])
        self.order.append(rid)

    def _close(self, run_id, extra=None):
        rid = str(run_id)
        if rid in self.nodes:
            self.nodes[rid]["ms"] = (time.perf_counter() - self.nodes[rid]["t0"]) * 1000
            if extra:
                self.nodes[rid]["payload"].update(extra)

    # --- chain (LangGraph 노드도 chain 으로 들어온다) ---
    def on_chain_start(self, serialized, inputs, *, run_id, parent_run_id=None, **kw):
        name = (kw.get("name") or (serialized or {}).get("name") or "chain")
        self._open("chain", name, run_id, parent_run_id)

    def on_chain_end(self, outputs, *, run_id, **kw):
        self._close(run_id)

    # --- LLM ---
    def on_chat_model_start(self, serialized, messages, *, run_id, parent_run_id=None, **kw):
        flat = []
        for msglist in messages:
            for m in msglist:
                flat.append(dict(role=type(m).__name__, chars=len(m.content),
                                 preview=m.content[:400]))
        self._open("llm", (serialized or {}).get("name") or "ChatOpenAI",
                   run_id, parent_run_id, dict(messages=flat,
                                               prompt_chars=sum(m["chars"] for m in flat)))

    def on_llm_end(self, response, *, run_id, **kw):
        usage = {}
        try:
            usage = (response.llm_output or {}).get("token_usage", {}) or {}
            if not usage:
                md = response.generations[0][0].message.usage_metadata or {}
                usage = dict(prompt_tokens=md.get("input_tokens"),
                             completion_tokens=md.get("output_tokens"),
                             total_tokens=md.get("total_tokens"))
        except Exception:
            pass
        out = ""
        try:
            out = response.generations[0][0].text
        except Exception:
            pass
        self._close(run_id, dict(tokens=usage, output_chars=len(out), output_preview=out[:300]))

    # --- retriever ---
    def on_retriever_start(self, serialized, query, *, run_id, parent_run_id=None, **kw):
        self._open("retriever", "VectorStoreRetriever", run_id, parent_run_id, dict(query=query))

    def on_retriever_end(self, documents, *, run_id, **kw):
        self._close(run_id, dict(n_docs=len(documents)))

    def tree(self):
        for rid in self.order:
            p = self.nodes[rid]["parent"]
            if p in self.nodes:
                self.nodes[p]["children"].append(rid)
        roots = [r for r in self.order if self.nodes[r]["parent"] not in self.nodes]
        return roots, self.nodes


def init():
    """eval_ragas.py 와 같은 방식으로 main 모듈 전역을 채운다."""
    main.llm = ChatOpenAI(model=main.GPT_MODEL, api_key=main.OPENAI_API_KEY, base_url=main.BASE_URL)
    main.embeddings = OpenAIEmbeddings(model=main.EMBEDDING_MODEL_NAME,
                                       api_key=main.OPENAI_API_KEY, base_url=main.BASE_URL)
    main.init_vectorstore()
    main.prompt_template, main.prompt_template_general = main.init_prompt_templates()
    main.rag_workflow = main.build_rag_graph()


def render(roots, nodes, depth=0, out=None):
    out = out if out is not None else []
    for rid in roots:
        n = nodes[rid]
        bar = "│  " * depth + ("├─ " if depth else "")
        extra = ""
        if n["kind"] == "llm":
            tk = n["payload"].get("tokens", {}) or {}
            extra = (f"  prompt {n['payload'].get('prompt_chars', 0):,}자"
                     f" / in {tk.get('prompt_tokens', '?')} tok"
                     f" / out {tk.get('completion_tokens', '?')} tok")
        elif n["kind"] == "retriever":
            extra = f"  docs {n['payload'].get('n_docs', '?')}"
        out.append(f"{bar}[{n['kind']}] {n['name']:<28} {n['ms'] or 0:8.1f} ms{extra}")
        render(n["children"], nodes, depth + 1, out)
    return out


if __name__ == "__main__":
    init()
    q = "교육 명찰을 분실했을 때는 어떻게 해야 하나요? 재발급 비용이 있나요?"
    dump = {}

    for label, use_rag in [("use_rag=True (RAG 경로)", True), ("use_rag=False (일반 경로)", False)]:
        cb = RunTree()
        # 검색 구간을 따로 재기 위해 retrieve_node 를 감싼다 (콜백이 닿지 않는 구간)
        t_ret = {}
        orig = main.retrieve_node
        def timed(state, _o=orig, _t=t_ret):
            t0 = time.perf_counter()
            r = _o(state)
            _t["ms"] = (time.perf_counter() - t0) * 1000
            _t["chars"] = len(r.get("context", ""))
            _t["n"] = len(r.get("retrieved_texts", []))
            return r
        main.retrieve_node = timed
        main.rag_workflow = main.build_rag_graph()

        t0 = time.perf_counter()
        st = main.rag_workflow.invoke(
            {"question": q, "use_rag": use_rag, "context": "", "source": ""},
            config={"callbacks": [cb]})
        total = (time.perf_counter() - t0) * 1000
        main.retrieve_node = orig

        roots, nodes = cb.tree()
        lines = render(roots, nodes)
        print(f"\n{'='*74}\n{label}   전체 {total:,.0f} ms\n{'='*74}")
        if t_ret:
            print(f"   retrieve_node  {t_ret['ms']:8.1f} ms  "
                  f"(질문 임베딩 1회 + 벡터검색) -> 청크 {t_ret['n']}개 / {t_ret['chars']:,}자")
        for l in lines:
            print("   " + l)
        print(f"\n   답변: {st['answer'][:120]}")
        dump[label] = dict(total_ms=total, retrieve=t_ret,
                           tree=[{k: v for k, v in nodes[r].items() if k != "t0"} for r in nodes],
                           lines=lines, answer=st["answer"])

    (OUT / "call_trace.json").write_text(json.dumps(dump, ensure_ascii=False, indent=2, default=str),
                                         encoding="utf-8")
    print(f"\n저장: {OUT / 'call_trace.json'}")
