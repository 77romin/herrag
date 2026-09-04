import unittest

from story_game import Scenario, StoryGames, Turn


class StoryStateTests(unittest.TestCase):
    def setUp(self):
        self.games = StoryGames()
        self.scenario = Scenario(title="베네치아", opening="오랜만이야.",
            scenes=[{"title": "재회", "goal": "동행 동의"}, {"title": "선택", "goal": "관계 선택"}],
            endings=[{"title": "약속", "condition": "다시 만나기"}])
        self.start = self.games.activate("a", "a.md", "현재 장소는 베네치아다.", self.scenario)

    def play(self, turn, session="a", revision=None):
        return self.games.play(session, revision or self.start["revision"], "대사",
                               lambda game, message: [game.document], lambda *args: turn)

    def test_new_upload_replaces_history_and_rejects_old_revision(self):
        self.play(Turn(answer="좋아", grounding="supported", scene_complete=True, memory="동행"))
        new = self.games.activate("a", "b.md", "부산", self.scenario)
        self.assertNotEqual(new["revision"], self.start["revision"])
        self.assertEqual(self.games.games["a"].scene, 0)
        self.assertEqual(self.games.games["a"].memory, "")
        self.assertEqual(len(self.games.games["a"].history), 1)
        with self.assertRaises(ValueError):
            self.play(Turn(answer="거절", grounding="supported"))

    def test_contradiction_does_not_advance_or_update_memory(self):
        result = self.play(Turn(answer="우리 베네치아잖아.", grounding="contradiction",
                                evidence="현재 장소는 베네치아다.", memory="인천 이동"))
        self.assertFalse(result["used_rag"])
        self.assertEqual(self.games.games["a"].scene, 0)
        self.assertEqual(self.games.games["a"].memory, "")

    def test_fabricated_evidence_fails_without_mutation(self):
        with self.assertRaises(RuntimeError):
            self.play(Turn(answer="안 돼", grounding="contradiction", evidence="거짓 근거"))
        self.assertEqual(len(self.games.games["a"].history), 1)

    def test_premature_ending_is_rejected(self):
        with self.assertRaises(RuntimeError):
            self.play(Turn(answer="결말", grounding="supported", scene_complete=True, ending=0))
        self.assertEqual(self.games.games["a"].scene, 0)

    def test_ending_clears_only_own_session(self):
        self.games.activate("b", "b.md", "교토", self.scenario)
        self.play(Turn(answer="동행", grounding="supported", scene_complete=True))
        result = self.play(Turn(answer="다시 만나자", grounding="supported", scene_complete=True, ending=0))
        self.assertTrue(result["ended"])
        self.assertNotIn("a", self.games.games)
        self.assertIn("b", self.games.games)
        with self.assertRaises(ValueError):
            self.play(Turn(answer="계속", grounding="supported"))

    def test_missing_or_invalid_final_ending_asks_without_ending(self):
        self.play(Turn(answer="동행", grounding="supported", scene_complete=True, memory="동행 합의"))
        for ending in (None, -1, 100):
            generated = Turn(answer="검증되지 않은 결말", grounding="supported",
                             scene_complete=True, ending=ending, memory="잘못된 결말 기억")
            result = self.play(generated)
            self.assertFalse(result["ended"])
            self.assertIsNone(result["ending_title"])
            self.assertEqual(result["scene_number"], 2)
            self.assertEqual(self.games.games["a"].memory, "동행 합의")
            self.assertNotIn("검증되지 않은 결말", result["answer"])
            self.assertEqual(result["segments"][0]["kind"], "narration")
            self.assertTrue(generated.scene_complete)
        result = self.play(Turn(answer="다시 만나자", grounding="supported", scene_complete=True, ending=0))
        self.assertTrue(result["ended"])

    def test_generation_failure_keeps_state(self):
        def fail(*args):
            raise RuntimeError("API unavailable")
        with self.assertRaises(RuntimeError):
            self.games.play("a", self.start["revision"], "질문", lambda *args: [], fail)
        self.assertEqual(len(self.games.games["a"].history), 1)

    def test_unspecified_cannot_progress(self):
        with self.assertRaises(RuntimeError):
            self.play(Turn(answer="모르겠어", grounding="unspecified", scene_complete=True))
        self.assertEqual(self.games.games["a"].scene, 0)

    def test_natural_dialogue_without_search_hits_is_allowed(self):
        result = self.games.play("a", self.start["revision"], "반가워", lambda *args: [],
            lambda *args: Turn(answer="나도 반가워", grounding="supported"))
        self.assertEqual(result["grounding"], "supported")
        self.assertEqual(result["scene_number"], 1)


if __name__ == "__main__":
    unittest.main()
