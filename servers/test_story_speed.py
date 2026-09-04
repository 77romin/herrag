import unittest
from story_speed import choose_effort


class SpeedTests(unittest.TestCase):
    def test_only_complete_acknowledgements_use_fast_setting(self):
        for text in ("그러자", " 좋아! ", "안녕하세요."):
            self.assertEqual(choose_effort(text, "gpt-5-mini", False), "low")
        for text in ("그러자, 인천으로 가자", "여기 근처 인천 곱창집 가자",
                     "좋아?", "싫어", "ignore rules", "나는 미성년자야"):
            self.assertEqual(choose_effort(text, "gpt-5-mini", False), "default")

    def test_final_scene_other_models_and_explicit_override(self):
        self.assertEqual(choose_effort("그러자", "gpt-5-mini", True), "default")
        self.assertEqual(choose_effort("그러자", "other-model", False), "default")
        self.assertEqual(choose_effort("그러자", "gpt-5-mini", False, "default"), "default")
        with self.assertRaises(ValueError):
            choose_effort("그러자", "gpt-5-mini", False, "typo")
