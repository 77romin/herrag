"""Deterministic story retrieval benchmark for Dense, BM25, and hybrid modes.

Embedding calls use the configured provider. No answer-generation or judge LLM is used.
The isolated Chroma collection is deleted after the run.
"""
import argparse
import json
from datetime import datetime
from pathlib import Path
from uuid import uuid4


def summarize(rows, ks=(1, 3, 4, 5)):
    total_evidence = sum(len(row["evidence_ranks"]) for row in rows)
    result = {}
    for k in ks:
        matched = sum(sum(rank is not None and rank <= k for rank in row["evidence_ranks"])
                      for row in rows)
        complete = sum(all(rank is not None and rank <= k for rank in row["evidence_ranks"])
                       for row in rows)
        result[f"evidence_recall@{k}"] = matched / total_evidence if total_evidence else 0.0
        result[f"complete_case_recall@{k}"] = complete / len(rows) if rows else 0.0
    first = [min((rank for rank in row["evidence_ranks"] if rank is not None), default=None)
             for row in rows]
    result["mrr"] = sum(1 / rank for rank in first if rank) / len(rows) if rows else 0.0
    result["avg_context_chars"] = (sum(row["context_chars"] for row in rows) / len(rows)
                                   if rows else 0.0)
    return result


def run():
    parser = argparse.ArgumentParser()
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--overlap", type=int, default=50)
    parser.add_argument("--dense-k", type=int, default=8)
    parser.add_argument("--bm25-k", type=int, default=8)
    parser.add_argument("--final-k", type=int, default=5)
    parser.add_argument("--threshold", type=float, default=0.15)
    parser.add_argument("--dense-weight", type=float, default=0.5)
    parser.add_argument("--bm25-weight", type=float, default=0.5)
    parser.add_argument("--modes", default="dense,bm25,hybrid",
                        help="Comma-separated subset of dense,bm25,hybrid")
    args = parser.parse_args()
    if not 0 <= args.overlap < args.chunk_size:
        parser.error("Require 0 <= overlap < chunk-size")

    import main
    from langchain_chroma import Chroma
    from story_retrieval import StoryRetriever

    root = Path(__file__).resolve().parent
    cases = json.loads((root / "story_test_cases.json").read_text(encoding="utf-8"))
    modes = [mode.strip() for mode in args.modes.split(",") if mode.strip()]
    if not modes or any(mode not in {"dense", "bm25", "hybrid"} for mode in modes):
        parser.error("--modes must contain dense, bm25, or hybrid")
    if any(mode in {"dense", "hybrid"} for mode in modes):
        if not main.OPENAI_API_KEY or main.OPENAI_API_KEY == "키를 입력하세요.":
            parser.error("Dense/hybrid evaluation requires API_KEY in servers/.env")
        from langchain_openai import OpenAIEmbeddings
        embeddings = OpenAIEmbeddings(model=main.EMBEDDING_MODEL_NAME,
                                      api_key=main.OPENAI_API_KEY, base_url=main.BASE_URL)
    else:
        class LocalPlaceholderEmbeddings:
            def embed_documents(self, texts):
                return [[1.0, 0.0] for _ in texts]

            def embed_query(self, text):
                return [1.0, 0.0]

        embeddings = LocalPlaceholderEmbeddings()
    store = Chroma(collection_name="story_retrieval_eval_" + uuid4().hex,
                   embedding_function=embeddings)
    try:
        for filename in sorted({case["file"] for case in cases}):
            docs = main.extract_documents(root.parent / "clients" / "sample_data" / filename)
            chunks = main.chunk_documents(docs, args.chunk_size, args.overlap)
            ids = [f"{filename}:{index}" for index in range(len(chunks))]
            for index, chunk in enumerate(chunks):
                chunk.metadata.update(pack_id=filename, chunk_index=index, chunk_id=ids[index])
            store.add_documents(chunks, ids=ids)

        report = {"settings": vars(args), "cases": len(cases), "modes": {}}
        for mode in modes:
            retriever = StoryRetriever(store, mode=mode, dense_k=args.dense_k,
                bm25_k=args.bm25_k, final_k=args.final_k, threshold=args.threshold,
                dense_weight=args.dense_weight, bm25_weight=args.bm25_weight)
            rows = []
            for case in cases:
                hits = retriever.search(case["question"], case["file"])
                ranks = []
                for evidence in case["evidence"]:
                    ranks.append(next((rank for rank, hit in enumerate(hits, 1)
                                       if evidence in hit.text), None))
                rows.append({"file": case["file"], "question": case["question"],
                             "category": case["category"], "evidence_ranks": ranks,
                             "context_chars": sum(len(hit.text) for hit in hits),
                             "hits": [{"id": hit.chunk_id, "dense_rank": hit.dense_rank,
                                       "bm25_rank": hit.bm25_rank,
                                       "rrf_score": round(hit.rrf_score, 8)} for hit in hits]})
            report["modes"][mode] = {"summary": summarize(rows), "rows": rows}
            print(mode, json.dumps(report["modes"][mode]["summary"], ensure_ascii=False))

        output = root / "evaluations" / (datetime.now().strftime("%Y%m%d-%H%M%S-%f")
                                          + "-retrieval")
        output.mkdir(parents=True)
        (output / "retrieval.json").write_text(
            json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"Saved: {output}")
    finally:
        store.delete_collection()


if __name__ == "__main__":
    run()
