import unittest

from story_brief import BriefFact, StoryBrief, public_brief
from story_game import Scenario, StoryGames


class PublicBriefTests(unittest.TestCase):
    def test_rejected_secret_is_not_public_even_with_real_evidence(self):
        doc = "현재 장소는 달빛 항구다. 숨겨진 사실: 그녀는 비밀 편지를 보관한다."
        brief = StoryBrief(
            location=BriefFact(text="달빛 항구", evidence="현재 장소는 달빛 항구다."),
            heroine=BriefFact(text="비밀 편지를 보관하는 인물", evidence="그녀는 비밀 편지를 보관한다."))
        self.assertEqual(public_brief(brief, doc, ["location"]), {"location": "달빛 항구"})

    def test_unverified_or_fabricated_facts_are_omitted(self):
        brief = StoryBrief(location=BriefFact(text="서울", evidence="서울에 있다."))
        self.assertEqual(public_brief(brief, "현재 부산이다.", ["location"]), {})
        self.assertEqual(public_brief(brief, "서울에 있다.", []), {})

    def test_session_exposes_only_reviewed_fields_and_replaces_them(self):
        scenario = Scenario(title="임의의 새 팩", opening="안녕하세요.",
            scenes=[{"title": "시작", "goal": "인사"}, {"title": "비밀", "goal": "편지"}],
            endings=[{"title": "결말", "condition": "조건"}],
            brief=StoryBrief(heroine=BriefFact(text="비밀 정체", evidence="비밀 정체")))
        games = StoryGames()
        result = games.activate("a", "custom.md", "원문", scenario,
                                public_brief={"location": "새로운 항구"})
        self.assertEqual(result["brief"], {"location": "새로운 항구"})
        self.assertNotIn("비밀 정체", str(result))
        fresh = games.activate("a", "another.md", "다른 원문", scenario)
        self.assertEqual(fresh["brief"], {})


if __name__ == "__main__":
    unittest.main()
