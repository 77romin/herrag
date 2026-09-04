import unittest

from story_game import StorySegment
from story_render import normalize_segments


class SpeakerAttributionTests(unittest.TestCase):
    def split(self, text):
        return [(part.kind, part.text) for part in normalize_segments(
            [StorySegment(kind="dialogue", text=text)], "박소은")]

    def test_reported_example(self):
        self.assertEqual(self.split("박소은 말한다 안녕하세요, 오시느라 고생하셨어요."), [
            ("narration", "박소은 말한다."), ("dialogue", "안녕하세요, 오시느라 고생하셨어요.")])

    def test_particle_adverb_and_quotes(self):
        self.assertEqual(self.split('소은이 조심스럽게 묻는다: “같이 읽을까요?”'), [
            ("narration", "소은이 조심스럽게 묻는다."), ("dialogue", "같이 읽을까요?")])

    def test_label_and_narration_only(self):
        self.assertEqual(self.split("박소은: 안녕하세요."), [("dialogue", "안녕하세요.")])
        self.assertEqual(self.split("그녀가 말한다."), [("narration", "그녀가 말한다.")])

    def test_actual_speech_and_quoted_attribution_are_unchanged(self):
        for text in ["저는 박소은이에요.", "소은이 말한다고 했나요?", '“박소은이 말한다”라는 문장이 좋아요.', "그녀는 누구예요?"]:
            self.assertEqual(self.split(text), [("dialogue", text)])

    def test_order_and_input_are_preserved(self):
        parts = [StorySegment(kind="narration", text="비가 온다."),
                 StorySegment(kind="dialogue", text="박소은 말한다 안녕!"),
                 StorySegment(kind="narration", text="그녀가 웃는다.")]
        result = normalize_segments(parts, "박소은")
        self.assertEqual([p.kind for p in result], ["narration", "narration", "dialogue", "narration"])
        self.assertEqual(parts[1].text, "박소은 말한다 안녕!")


if __name__ == "__main__":
    unittest.main()
