import unittest

from pydantic import ValidationError
from story_game import Scenario, GeneratedTurn, StoryGames


class SegmentTests(unittest.TestCase):
    def test_generated_turn_needs_no_duplicate_answer(self):
        turn = GeneratedTurn(grounding="supported", segments=[
            {"kind": "narration", "text": "서윤이 웃는다."},
            {"kind": "dialogue", "text": "반가워."}])
        self.assertEqual(turn.answer, "서윤이 웃는다.\n반가워.")
        self.assertNotIn("answer", GeneratedTurn.generation_schema()["properties"])
        with self.assertRaises(ValidationError):
            GeneratedTurn(grounding="supported", memory="가" * 601,
                          segments=[{"kind": "dialogue", "text": "안녕"}])
        with self.assertRaises(ValidationError):
            GeneratedTurn(grounding="supported", segments=[
                {"kind": "dialogue", "text": "가" * 2000}] * 3)

    def test_opening_and_turn_preserve_types_order_and_speaker(self):
        opening = [
            {"kind": "narration", "text": "항구의 늦은 오후."},
            {"kind": "dialogue", "text": "오랜만이야!"}]
        scenario = Scenario(title="새로운 팩", opening="discard duplicate",
            heroine_name="한서윤", opening_segments=opening,
            scenes=[{"title": "재회", "goal": "인사"}, {"title": "작별", "goal": "선택"}],
            endings=[{"title": "안녕", "condition": "작별"}])
        games = StoryGames()
        result = games.activate("a", "custom.md", "한서윤", scenario)
        self.assertEqual(result["heroine_name"], "한서윤")
        self.assertEqual(result["segments"], opening)
        self.assertEqual(result["answer"], "항구의 늦은 오후.\n오랜만이야!")
        parts = [{"kind": "dialogue", "text": "반가워."},
                 {"kind": "narration", "text": "서윤이 웃는다."}]
        turn = GeneratedTurn(answer="discard duplicate", segments=parts, grounding="supported")
        reply = games.play("a", result["revision"], "안녕", lambda *args: [], lambda *args: turn)
        self.assertEqual(reply["segments"], parts)
        self.assertEqual(reply["heroine_name"], "한서윤")
        self.assertEqual(games.games["a"].history[-1]["content"], "반가워.\n서윤이 웃는다.")

    def test_live_response_requires_valid_nonblank_segments(self):
        for parts in ([], [{"kind": "other", "text": "안녕"}], [{"kind": "dialogue", "text": "  "}]):
            with self.assertRaises(ValidationError):
                GeneratedTurn(answer="안녕", grounding="supported", segments=parts)
        with self.assertRaises(ValidationError):
            GeneratedTurn(answer="안녕", grounding="supported")


if __name__ == "__main__":
    unittest.main()
