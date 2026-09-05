import unittest
from types import SimpleNamespace
from uuid import uuid4

from story_retrieval import (StoryRetriever, build_story_query,
                             reciprocal_rank_fusion, select_model_document, tokenize)


class Store:
    def __init__(self):
        self.rows = [
            ("a:0", "현재 장소는 교토의 빛의 서랍 사진관 앞이다.", {"pack_id": "a", "chunk_index": 0}),
            ("a:1", "나경의 카메라 스트랩은 남색이고 사용자의 것은 검은색이다.", {"pack_id": "a", "chunk_index": 1}),
            ("a:2", "현상에는 며칠이 걸려 오늘 필름을 볼 수 없다.", {"pack_id": "a", "chunk_index": 2}),
            ("b:0", "현재 장소는 제주이며 해린은 독립 서점을 준비한다.", {"pack_id": "b", "chunk_index": 0}),
        ]
        self.dense_order = ["a:0", "a:2", "a:1"]

    def get(self, where=None, include=None, ids=None):
        rows = self.rows
        if where:
            rows = [row for row in rows if all(row[2].get(k) == v for k, v in where.items())]
        if ids is not None:
            rows = [row for row in rows if row[0] in ids]
        return {"ids": [row[0] for row in rows], "documents": [row[1] for row in rows],
                "metadatas": [row[2] for row in rows]}

    def similarity_search_with_relevance_scores(self, query, k, filter, score_threshold=None):
        selected = [row for key in self.dense_order for row in self.rows
                    if row[0] == key and row[2]["pack_id"] == filter["pack_id"]]
        scores = [0.9, 0.8, 0.7]
        return [(SimpleNamespace(page_content=row[1], metadata=row[2]), score)
                for row, score in zip(selected[:k], scores[:k])
                if score_threshold is None or score >= score_threshold]


class StoryRetrievalTests(unittest.TestCase):
    def setUp(self):
        self.store = Store()

    def test_tokenizer_matches_report_rules(self):
        tokens = tokenize("검은색·남색 스트랩?")
        self.assertEqual(tokens[:3], ["검은색", "남색", "스트랩"])
        self.assertIn("ko2:남색", tokens)
        self.assertIn("ko3:스트랩", tokens)

    def test_rrf_rewards_chunks_found_by_both_retrievers(self):
        scores = reciprocal_rank_fusion([["a", "b"], ["b", "c"]], [0.5, 0.5])
        self.assertGreater(scores["b"], scores["a"])
        self.assertGreater(scores["b"], scores["c"])

    def test_hybrid_promotes_exact_keyword_dense_missed(self):
        retriever = StoryRetriever(self.store, mode="hybrid", dense_k=3, bm25_k=3,
                                   final_k=3, dense_weight=0.5, bm25_weight=0.5)
        hits = retriever.search("남색 스트랩", "a")
        self.assertEqual(hits[0].chunk_id, "a:1")
        self.assertEqual(hits[0].dense_rank, 3)
        self.assertEqual(hits[0].bm25_rank, 1)

    def test_pack_filter_never_returns_another_story(self):
        retriever = StoryRetriever(self.store, mode="hybrid", final_k=4)
        hits = retriever.search("제주 해린 독립 서점", "a")
        self.assertTrue(hits)
        self.assertTrue(all(hit.metadata["pack_id"] == "a" for hit in hits))

    def test_bm25_zero_scores_do_not_add_arbitrary_chunks(self):
        hits = StoryRetriever(self.store, mode="bm25").search("존재하지않는단어", "a")
        self.assertEqual(hits, [])

    def test_bm25_keeps_matches_in_a_single_chunk_pack(self):
        hits = StoryRetriever(self.store, mode="bm25").search("제주 해린", "b")
        self.assertEqual([hit.chunk_id for hit in hits], ["b:0"])

    def test_short_answer_query_contains_pending_question(self):
        game = SimpleNamespace(scene=0,
            scenario=SimpleNamespace(scenes=[SimpleNamespace(title="한 장의 산책")]),
            pending_question=SimpleNamespace(text="강변에서 사진 한 장씩 찍으실래요?"))
        query = build_story_query(game, "좋아요")
        self.assertIn("강변에서 사진 한 장씩 찍으실래요?", query)
        self.assertNotIn("강변에서", build_story_query(game, "오늘 날씨는 어때?"))

    def test_dense_mode_preserves_threshold_and_final_k(self):
        retriever = StoryRetriever(self.store, mode="dense", final_k=2, threshold=0.85)
        hits = retriever.search("카메라", "a")
        self.assertEqual([hit.chunk_id for hit in hits], ["a:0"])

    def test_context_mode_supports_full_and_retrieved_ab(self):
        self.assertEqual(select_model_document("전체", ["검색1", "검색2"], "full"), "전체")
        self.assertEqual(select_model_document("전체", ["검색1", "검색2"], "retrieved"),
                         "검색1\n\n검색2")
        with self.assertRaises(ValueError):
            select_model_document("전체", [], "invalid")

    def test_real_chroma_pack_filter_and_metadata_identity(self):
        from langchain_chroma import Chroma
        from langchain_core.documents import Document

        class Embeddings:
            @staticmethod
            def vector(text):
                return [float("교토" in text), float("제주" in text),
                        float("스트랩" in text), 0.1]

            def embed_documents(self, texts):
                return [self.vector(text) for text in texts]

            def embed_query(self, text):
                return self.vector(text)

        store = Chroma(collection_name="story_test_" + uuid4().hex,
                       embedding_function=Embeddings())
        try:
            docs = [
                Document(page_content="교토에서 남색 스트랩을 찾았다.",
                         metadata={"pack_id": "a", "chunk_index": 0, "chunk_id": "a:0"}),
                Document(page_content="제주에서 귤을 먹었다.",
                         metadata={"pack_id": "b", "chunk_index": 0, "chunk_id": "b:0"}),
            ]
            store.add_documents(docs, ids=["a:0", "b:0"])
            hits = StoryRetriever(store, mode="hybrid", final_k=2).search("남색 스트랩", "a")
            self.assertEqual([hit.chunk_id for hit in hits], ["a:0"])
            self.assertEqual(hits[0].metadata["pack_id"], "a")
        finally:
            store.delete_collection()


if __name__ == "__main__":
    unittest.main()
