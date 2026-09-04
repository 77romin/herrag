import unittest
from pydantic import ValidationError
from story_progress import Rules
from story_game import GeneratedScenario, GeneratedTurn, StoryGames


def req(id, question, answer_to=None):
    return dict(id=id, description="사용자가 " + id, evidence="원문", question=question, answer_to=answer_to)


class ProgressTests(unittest.TestCase):
    def setUp(self):
        self.scenario = GeneratedScenario(title="임의의 팩", heroine_name="수아", opening="동창이지?",
            opening_segments=[dict(kind="dialogue", text="동창이지?")],
            opening_question=dict(scene=0, requirement_id="recognize", text="동창이지?"),
            scenes=[dict(title="재회", goal="인정과 동행 또는 거절", rules=dict(
                requirements=[req("recognize", "동창이지?"), req("walk", "같이 걸을래?"),
                              req("refuse", "같이 걸을래?", "walk")],
                routes=[dict(all_of=["recognize", "walk"]), dict(all_of=["refuse"])])),
                dict(title="선택", goal="관계 선택", rules=dict(
                    requirements=[req("friend", "친구로 연락할까?"), req("bye", "친구로 연락할까?", "friend")],
                    routes=[dict(all_of=["friend"], ending=0), dict(all_of=["bye"], ending=1)]))],
            endings=[dict(title="친구", condition="동의"), dict(title="작별", condition="거절")])
        self.games = StoryGames()
        self.start = self.games.activate("a", "a.md", "원문", self.scenario)

    def play(self, message, ids=(), question=None, complete=False, ending=None, grounding="supported", text=None):
        introduction = '함께 이야기를 마친 뒤 다음 약속을 정할 시간이 되었다.' if question and question[0] > self.games.games['a'].scene else ''
        turn = GeneratedTurn(grounding=grounding, scene_complete=complete, ending=ending,
            introduced_scene=question[0] if question and question[0] > self.games.games['a'].scene else None,
            scene_introduction=introduction,
            segments=([dict(kind='narration', text=introduction)] if introduction else []) + [dict(kind="dialogue", text=text or (question[2] if question else "알겠어."))],
            satisfied_requirements=[dict(requirement_id=id, evidence=message, value=message) for id in ids],
            next_question=dict(scene=question[0], requirement_id=question[1], text=question[2]) if question else None)
        return self.games.play("a", self.start["revision"], message, lambda *a: [], lambda *a: turn)

    def test_short_yes_does_not_accept_unasked_walk(self):
        result = self.play("ㅇㅇ", ["recognize", "walk"], (0, "walk", "같이 걸을래?"), complete=False)
        game = self.games.games["a"]
        self.assertEqual(result["scene_number"], 1)
        self.assertEqual(set(game.completed), {"0:recognize"})
        self.assertEqual(game.pending_question.requirement_id, "walk")
        result = self.play("그러자", ["walk"], (1, "friend", "친구로 연락할까?"), complete=True)
        self.assertEqual(result["scene_number"], 2)
        self.assertFalse(result["ended"])

    def test_unrepairable_repeated_question_keeps_original_state(self):
        with self.assertRaises(RuntimeError):
            self.play("응", ["recognize"], (0, "recognize", "동창이지?"))
        self.assertEqual(self.games.games['a'].completed, {})

    def test_refusal_route_and_valid_final_choice(self):
        self.play("응", ["recognize"], (0, "walk", "같이 걸을래?"))
        result = self.play("아니", ["refuse"], (1, "friend", "친구로 연락할까?"), complete=True)
        self.assertEqual(result["scene_number"], 2)
        result = self.play("아니", ["bye"], complete=True, ending=1, text="잘 가.")
        self.assertTrue(result["ended"])
        self.assertNotIn("a", self.games.games)

    def test_unsupported_and_ambiguous_do_not_advance(self):
        self.play("잘 모르겠어", question=(0, "recognize", "같은 반이었는지 기억나?"))
        game = self.games.games["a"]
        self.assertEqual(game.completed, {})
        self.play("없는 사실", ["recognize"], grounding="unspecified")
        self.assertEqual(game.completed, {})
        self.assertEqual(game.pending_question.text, "같은 반이었는지 기억나?")

    def test_fabricated_evidence_and_unknown_condition_ignored(self):
        turn = GeneratedTurn(grounding="supported", segments=[dict(kind="dialogue", text="다시 말해 줄래?")],
            satisfied_requirements=[dict(requirement_id="recognize", evidence="없는 인용", value="인정"),
                                    dict(requirement_id="bogus", evidence="응", value="인정")])
        with self.assertRaises(RuntimeError):
            self.games.play("a", self.start["revision"], "응", lambda *a: [], lambda *a: turn)
        self.assertEqual(self.games.games["a"].completed, {})

    def test_pack_reset_removes_progress(self):
        self.play("응", ["recognize"], (0, "walk", "같이 걸을래?"))
        self.games.activate("a", "b.md", "원문", self.scenario)
        self.assertEqual(self.games.games["a"].completed, {})
        self.assertEqual(len(self.games.games["a"].asked_questions), 1)

    def test_premature_final_choice_not_accepted(self):
        self.play("응", ["recognize"], (0, "walk", "같이 걸을래?"))
        self.play("그러자", ["walk"], (1, "friend", "친구로 연락할까?"), complete=True)
        with self.assertRaises(RuntimeError):
            self.play("편지를 못 받았어", complete=True, ending=0, text="우리 친구가 되었어.")
        self.assertIn('a', self.games.games)

    def test_conflicting_yes_and_no_are_not_both_committed(self):
        self.play("응", ["recognize"], (0, "walk", "같이 걸을래?"))
        with self.assertRaises(RuntimeError):
            self.play("그러자", ["walk", "refuse"], complete=False)
        self.assertEqual(self.games.games['a'].scene, 0)
        self.assertEqual(set(self.games.games["a"].completed), {"0:recognize"})

    def test_final_missing_ending_recovers_without_losing_session(self):
        self.play("응", ["recognize"], (0, "walk", "같이 걸을래?"))
        self.play("그러자", ["walk"], (1, "friend", "친구로 연락할까?"), complete=True)
        with self.assertRaises(RuntimeError):
            self.play("응", ["friend"], complete=True)
        self.assertNotIn("1:friend", self.games.games["a"].completed)
        self.assertEqual(self.games.games["a"].pending_question.scene, 1)

    def test_question_anchor_is_not_a_second_required_answer(self):
        with self.assertRaises(ValidationError):
            Rules(requirements=[req("walk", "같이 걸을래?"), req("no", "같이 걸을래?", "walk")],
                  routes=[dict(all_of=["walk", "no"])])

    def test_full_sentence_repeat_inside_longer_bubble_is_detected(self):
        self.games.games["a"].spoken_dialogue.append("혹시 우리 같은 반 아니었어?")
        self.games.games["a"].asked_questions.append(dict(scene=0, requirement_id='recognize', text='혹시 우리 같은 반 아니었어?'))
        with self.assertRaises(RuntimeError):
            self.play("응", ["recognize"], (0, "walk", "같이 걸을래?"),
                      text="혹시 우리 같은 반 아니었어? 같이 걸을래?")

    def test_explanation_without_goal_question_is_preserved(self):
        result = self.play('어떻게 알았어?', text='네 이름표를 보고 알아봤어.')
        self.assertEqual(result['answer'], '네 이름표를 보고 알아봤어.')
        self.assertEqual(self.games.games['a'].pending_question.text, '동창이지?')

    def test_unanswered_question_can_follow_an_explanation(self):
        result = self.play('어떻게 알아봤어?', question=(0, 'recognize', '동창이지?'),
                           text='이름표를 보고 알았어. 동창이지?')
        self.assertIn('이름표', result['answer'])
        self.assertEqual(result['scene_number'], 1)

    def test_social_question_does_not_erase_explanation_or_bind_old_goal(self):
        result = self.play('어떻게 알아봤어?', question=(0, 'social', '영화 좋아해?'),
                           text='이름표를 보고 알았어. 영화 좋아해?')
        self.assertIn('이름표를 보고', result['answer'])
        self.assertEqual(result['scene_number'], 1)
        self.assertIsNone(self.games.games['a'].pending_question)

    def test_bad_contradiction_quote_is_repaired_once(self):
        calls = []
        def generate(game, message, contexts):
            calls.append(game.repair_feedback)
            return GeneratedTurn(grounding='contradiction', evidence='원문' if game.repair_feedback else '잘못된 인용',
                segments=[dict(kind='dialogue', text='그 장소는 여기에서 갈 수 없어.')])
        result = self.games.play('a', self.start['revision'], '다른 나라로 걸어가자', lambda *a: [], generate)
        self.assertEqual(len(calls), 2)
        self.assertEqual(result['grounding'], 'contradiction')
        self.assertEqual(self.games.games['a'].completed, {})

    def test_one_repair_preserves_answer_and_adds_scene_introduction(self):
        self.play('응', ['recognize'], (0, 'walk', '같이 걸을래?'))
        calls = []
        def generate(game, message, contexts):
            calls.append(game.repair_feedback)
            if game.repair_feedback:
                self.assertIn('missing_scene_introduction', game.repair_feedback['reasons'])
            return GeneratedTurn(grounding='supported', scene_complete=True,
                satisfied_requirements=[dict(requirement_id='walk', evidence='그러자', value='동행')],
                introduced_scene=1 if game.repair_feedback else None,
                scene_introduction='같이 가 줘서 고마워. 이제 헤어질 시간이네.' if game.repair_feedback else '',
                segments=[dict(kind='dialogue', text='같이 가 줘서 고마워. 이제 헤어질 시간이네. 친구로 연락할까?' if game.repair_feedback else '친구로 연락할까?')],
                next_question=dict(scene=1, requirement_id='friend', text='친구로 연락할까?'))
        result = self.games.play('a', self.start['revision'], '그러자', lambda *a: [], generate)
        self.assertEqual(len(calls), 2)
        self.assertIn('헤어질 시간', result['answer'])
        self.assertEqual(result['scene_number'], 2)
