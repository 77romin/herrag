import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace

from story_cache import PackCache
from story_game import GeneratedScenario, StoryGames


class Store:
    def __init__(self):
        self.ids = set()
        self.writes = 0
        self.documents = {}
        self.metadatas = {}

    def get(self, ids, include=None):
        present = [key for key in ids if key in self.ids]
        return {"ids": present, "documents": [self.documents[key] for key in present]}

    def add_documents(self, docs, ids):
        self.ids.update(ids)
        self.writes += 1
        self.documents.update({key: doc.page_content for key, doc in zip(ids, docs)})
        self.metadatas.update({key: dict(doc.metadata) for key, doc in zip(ids, docs)})


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.store = Store()
        self.builds = 0
        self.scenario = GeneratedScenario(title="팩", heroine_name="수아", opening="안녕",
            opening_segments=[{"kind": "dialogue", "text": "안녕?"}],
            opening_question={"scene": 0, "requirement_id": "greet", "text": "안녕?"},
            scenes=[{"title": "시작", "goal": "인사", "rules": {
                "requirements": [{"id": "greet", "description": "사용자가 인사", "evidence": "story", "question": "안녕?"}],
                "routes": [{"all_of": ["greet"]}]}},
                {"title": "끝", "goal": "선택", "rules": {
                "requirements": [{"id": "end", "description": "사용자가 선택", "evidence": "story", "question": "다시 볼까?"}],
                "routes": [{"all_of": ["end"], "ending": 0}]}}],
            endings=[{"title": "결말", "condition": "선택"}])

    def cache(self, version=1):
        def extract(path):
            return [SimpleNamespace(page_content=Path(path).read_text(encoding="utf-8"), metadata={})]

        def build(document):
            self.builds += 1
            return self.scenario, {"location": "항구"}

        return PackCache(self.directory.name, self.store, {"version": version}, extract, lambda docs: docs, build)

    def test_restart_and_renamed_file_reuse_without_ai_or_vectors(self):
        first = self.cache().prepare(b"story", "a.md")
        second = self.cache().prepare(b"story", "renamed.md")
        self.assertFalse(first["cache_hit"])
        self.assertTrue(second["cache_hit"])
        self.assertEqual(self.builds, 1)
        self.assertEqual(self.store.writes, 1)

    def test_content_or_settings_change_rebuilds(self):
        old = self.cache().prepare(b"story", "a.md")
        changed = self.cache().prepare(b"changed", "a.md")
        settings = self.cache(2).prepare(b"story", "a.md")
        self.assertEqual(len({old["key"], changed["key"], settings["key"]}), 3)
        self.assertEqual(self.builds, 3)
        self.assertEqual(self.store.writes, 2)  # Analysis-only changes reuse vectors.

    def test_missing_vectors_rebuilt_without_reanalyzing(self):
        self.cache().prepare(b"story", "a.md")
        self.store.ids.clear()
        result = self.cache().prepare(b"story", "a.md")
        self.assertFalse(result["cache_hit"])
        self.assertEqual(self.builds, 1)
        self.assertEqual(self.store.writes, 2)

    def test_new_vectors_include_pack_and_stable_chunk_identity(self):
        prepared = self.cache().prepare(b"story", "a.md")
        metadata = self.store.metadatas[prepared["ids"][0]]
        self.assertEqual(metadata["pack_id"], prepared["vector_key"])
        self.assertEqual(metadata["chunk_index"], 0)
        self.assertEqual(metadata["chunk_id"], prepared["ids"][0])

    def test_shared_pack_keeps_separate_sessions(self):
        prepared = self.cache().prepare(b"story", "a.md")
        games = StoryGames()
        for session in ["a", "b"]:
            games.activate(session, "a.md", prepared["document"], prepared["scenario"], pack_id=prepared["key"])
        games.games["a"].memory = "a only"
        self.assertEqual(games.games["b"].memory, "")
        self.assertNotEqual(games.games["a"].revision, games.games["b"].revision)
        games.games.pop("a")
        self.assertTrue(self.cache().prepare(b"story", "a.md")["cache_hit"])


if __name__ == "__main__":
    unittest.main()
