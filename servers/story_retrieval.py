"""Pack-scoped Dense/BM25 retrieval for story conversations."""
from __future__ import annotations

import re
from collections import defaultdict
from dataclasses import dataclass, replace
from threading import RLock

from rank_bm25 import BM25Okapi


SHORT_ANSWERS = {
    "ㅇㅇ", "ㅇ", "응", "네", "예", "그래", "그러자", "좋아", "좋아요",
    "알겠어", "알겠어요", "아니", "아니요", "싫어", "싫어요", "ㄴㄴ",
}


def canonical(text):
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).lower()


def tokenize(text):
    """Keep report-style words and add Hangul n-grams for 조사/어미 variation."""
    words = re.sub(r"[^\w\s]", " ", text.lower(), flags=re.UNICODE).split()
    tokens = list(words)
    for word in words:
        hangul = "".join(re.findall(r"[가-힣]", word))
        for size in (2, 3):
            tokens.extend(f"ko{size}:{hangul[i:i + size]}"
                          for i in range(len(hangul) - size + 1))
    return tokens


def build_story_query(game, message):
    """Add the pending question when a short answer has little retrieval meaning."""
    parts = [game.scenario.scenes[game.scene].title]
    if canonical(message) in SHORT_ANSWERS and game.pending_question is not None:
        parts.append(game.pending_question.text)
    parts.append(message)
    return " ".join(part.strip() for part in parts if part and part.strip())


def select_model_document(document, contexts, mode):
    """Select full or retrieval-only context for controlled A/B evaluation."""
    mode = mode.strip().lower()
    if mode == "full":
        return document
    if mode == "retrieved":
        return "\n\n".join(contexts)
    raise ValueError("STORY_CONTEXT_MODE must be full or retrieved")


@dataclass(frozen=True)
class SearchHit:
    chunk_id: str
    text: str
    metadata: dict
    dense_rank: int | None = None
    bm25_rank: int | None = None
    dense_score: float | None = None
    bm25_score: float | None = None
    rrf_score: float = 0.0


@dataclass
class _Corpus:
    hits: list[SearchHit]
    bm25: BM25Okapi
    token_sets: list[set[str]]
    by_id: dict[str, SearchHit]
    ids_by_text: dict[str, list[str]]


def reciprocal_rank_fusion(rankings, weights, constant=60):
    scores = defaultdict(float)
    for ranking, weight in zip(rankings, weights):
        for rank, chunk_id in enumerate(ranking, start=1):
            scores[chunk_id] += weight / (constant + rank)
    return scores


class StoryRetriever:
    """Retrieves only chunks belonging to the active immutable story pack."""

    def __init__(self, store, mode="hybrid", dense_k=8, bm25_k=8, final_k=4,
                 threshold=0.15, dense_weight=0.5, bm25_weight=0.5, rrf_constant=60):
        if mode not in {"dense", "bm25", "hybrid"}:
            raise ValueError("STORY_RETRIEVAL_MODE must be dense, bm25, or hybrid")
        if min(dense_k, bm25_k, final_k) < 1:
            raise ValueError("Retrieval k values must be positive")
        if dense_weight < 0 or bm25_weight < 0 or dense_weight + bm25_weight <= 0:
            raise ValueError("Retrieval weights must be non-negative with a positive sum")
        self.store = store
        self.mode = mode
        self.dense_k = dense_k
        self.bm25_k = bm25_k
        self.final_k = final_k
        self.threshold = threshold
        total = dense_weight + bm25_weight
        self.dense_weight = dense_weight / total
        self.bm25_weight = bm25_weight / total
        self.rrf_constant = rrf_constant
        self._corpora = {}
        self._lock = RLock()

    def _load_corpus(self, pack_id):
        with self._lock:
            if pack_id in self._corpora:
                return self._corpora[pack_id]
            found = self.store.get(where={"pack_id": pack_id},
                                   include=["documents", "metadatas"])
            rows = []
            for chunk_id, text, metadata in zip(found.get("ids", []),
                                                 found.get("documents", []),
                                                 found.get("metadatas", [])):
                metadata = dict(metadata or {})
                rows.append(SearchHit(str(chunk_id), text or "", metadata))
            rows.sort(key=lambda hit: (hit.metadata.get("chunk_index", 10**9), hit.chunk_id))
            by_id = {hit.chunk_id: hit for hit in rows}
            ids_by_text = defaultdict(list)
            for hit in rows:
                ids_by_text[hit.text].append(hit.chunk_id)
            tokenized = [tokenize(hit.text) for hit in rows]
            corpus = _Corpus(rows, BM25Okapi(tokenized), [set(row) for row in tokenized],
                             by_id, dict(ids_by_text)) if rows else None
            self._corpora[pack_id] = corpus
            return corpus

    @staticmethod
    def _dense_id(doc, corpus, used):
        metadata = getattr(doc, "metadata", {}) or {}
        explicit = metadata.get("chunk_id") or metadata.get("chunk_key")
        if explicit in corpus.by_id:
            return explicit
        for chunk_id in corpus.ids_by_text.get(getattr(doc, "page_content", ""), []):
            if chunk_id not in used:
                return chunk_id
        return None

    def search(self, query, pack_id):
        corpus = self._load_corpus(pack_id)
        if corpus is None:
            return []

        dense_ids, dense_scores = [], {}
        if self.mode in {"dense", "hybrid"}:
            kwargs = {"k": self.final_k if self.mode == "dense" else self.dense_k,
                      "filter": {"pack_id": pack_id}}
            if self.mode == "dense":
                kwargs["score_threshold"] = self.threshold
            dense = self.store.similarity_search_with_relevance_scores(query, **kwargs)
            used = set()
            for doc, score in dense:
                chunk_id = self._dense_id(doc, corpus, used)
                if chunk_id is None:
                    continue
                used.add(chunk_id)
                dense_ids.append(chunk_id)
                dense_scores[chunk_id] = float(score)

        bm25_ids, bm25_scores = [], {}
        if self.mode in {"bm25", "hybrid"}:
            query_tokens = tokenize(query)
            query_set = set(query_tokens)
            scores = corpus.bm25.get_scores(query_tokens)
            overlap = [len(query_set & tokens) for tokens in corpus.token_sets]
            ranked = sorted(range(len(scores)),
                            key=lambda i: (-float(scores[i]), -overlap[i], i))
            # RankBM25 can assign non-positive IDF to terms present in a tiny corpus.
            # Token overlap, not score sign, determines whether a lexical match exists.
            for index in ranked:
                score = float(scores[index])
                if len(bm25_ids) >= self.bm25_k:
                    break
                if overlap[index] == 0:
                    continue
                chunk_id = corpus.hits[index].chunk_id
                bm25_ids.append(chunk_id)
                bm25_scores[chunk_id] = score

        if self.mode == "dense":
            ordered = dense_ids
            fused = reciprocal_rank_fusion([dense_ids], [1.0], self.rrf_constant)
        elif self.mode == "bm25":
            ordered = bm25_ids
            fused = reciprocal_rank_fusion([bm25_ids], [1.0], self.rrf_constant)
        else:
            fused = reciprocal_rank_fusion([dense_ids, bm25_ids],
                                            [self.dense_weight, self.bm25_weight],
                                            self.rrf_constant)
            ordered = sorted(fused, key=lambda chunk_id: (-fused[chunk_id], chunk_id))

        dense_rank = {chunk_id: rank for rank, chunk_id in enumerate(dense_ids, 1)}
        bm25_rank = {chunk_id: rank for rank, chunk_id in enumerate(bm25_ids, 1)}
        return [replace(corpus.by_id[chunk_id], dense_rank=dense_rank.get(chunk_id),
                        bm25_rank=bm25_rank.get(chunk_id),
                        dense_score=dense_scores.get(chunk_id),
                        bm25_score=bm25_scores.get(chunk_id),
                        rrf_score=fused.get(chunk_id, 0.0))
                for chunk_id in ordered[:self.final_k]]

    def retrieve(self, game, message):
        return self.search(build_story_query(game, message), game.pack_id)
