"""Session-scoped story state; model decisions never directly overwrite game state."""
from __future__ import annotations
import json
import logging
from dataclasses import dataclass, field, replace
from threading import RLock
from uuid import uuid4
from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator
from story_brief import StoryBrief
from story_render import normalize_segments
from story_progress import (Rules, Question, Completion, dialogue_units, propose_progress,
                            fallback_question, question_valid, canonical, SHORT_ANSWERS)


class Scene(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    goal: str = Field(min_length=1, max_length=1000)
    rules: Rules | None = None


class StructuredScene(Scene):
    rules: Rules


class Ending(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    condition: str = Field(min_length=1, max_length=1000)


class StorySegment(BaseModel):
    kind: Literal["narration", "dialogue"]
    text: str = Field(min_length=1, max_length=2000)

    @field_validator("text")
    @classmethod
    def nonblank(cls, value):
        if not value.strip():
            raise ValueError("Story text cannot be blank")
        return value.strip()


class Scenario(BaseModel):
    title: str = Field(min_length=1, max_length=100)
    opening: str = Field(min_length=1, max_length=2000)
    scenes: list[Scene] = Field(min_length=2, max_length=8)
    endings: list[Ending] = Field(min_length=1, max_length=5)
    brief: StoryBrief = Field(default_factory=StoryBrief)
    heroine_name: str = Field(default="상대방", min_length=1, max_length=80)
    opening_segments: list[StorySegment] = Field(default_factory=list, max_length=16)
    opening_question: Question | None = None

    @model_validator(mode="after")
    def sync_opening(self):
        if self.opening_segments:
            self.opening = "\n".join(part.text for part in self.opening_segments)
        return self


class Turn(BaseModel):
    answer: str = Field(min_length=1, max_length=4000)
    grounding: str  # supported / unspecified / contradiction
    evidence: str = ""  # verbatim scenario quote for a contradiction
    scene_complete: bool = False
    ending: int | None = None
    memory: str = Field(default="", max_length=2000)
    segments: list[StorySegment] = Field(default_factory=list, max_length=16)
    satisfied_requirements: list[Completion] = Field(default_factory=list, max_length=12)
    next_question: Question | None = None

    @model_validator(mode="after")
    def sync_answer(self):
        if self.segments:
            self.answer = "\n".join(part.text for part in self.segments)
        return self


# Live AI responses must be structured; legacy state tests can still use plain text.
class GeneratedScenario(Scenario):
    heroine_name: str = Field(min_length=1, max_length=80)
    opening_segments: list[StorySegment] = Field(min_length=1, max_length=16)
    scenes: list[StructuredScene] = Field(min_length=2, max_length=8)
    opening_question: Question

    @model_validator(mode="after")
    def validate_progression(self):
        q = self.opening_question
        if q.scene != 0 or q.requirement_id not in {r.id for r in self.scenes[0].rules.requirements}:
            raise ValueError("Opening question must target first scene")
        if q.text not in "\n".join(p.text for p in self.opening_segments if p.kind == "dialogue"):
            raise ValueError("Opening question must actually be spoken")
        for index, scene in enumerate(self.scenes):
            for route in scene.rules.routes:
                if index == len(self.scenes) - 1:
                    if route.ending is None or not 0 <= route.ending < len(self.endings):
                        raise ValueError("Final routes must reference valid endings")
                elif route.ending is not None:
                    raise ValueError("Earlier routes cannot end the story")
        return self


class GeneratedTurn(Turn):
    # The model emits segments once; sync_answer assembles the API-compatible text.
    answer: str = ""
    memory: str = Field(default="", max_length=600)
    segments: list[StorySegment] = Field(min_length=1, max_length=16)
    introduced_scene: int | None = None
    scene_introduction: str = Field(default="", max_length=1000)

    @classmethod
    def generation_schema(cls):
        schema = cls.model_json_schema()
        schema["properties"].pop("answer")
        return schema

    @model_validator(mode="after")
    def check_answer_length(self):
        if len(self.answer) > 4000:
            raise ValueError("Combined story text exceeds 4000 characters")
        return self


def decode(model, response):
    content = response.content.strip()
    if content.startswith("```"):
        content = content.split("\n", 1)[1].rsplit("```", 1)[0]
    return model.model_validate(json.loads(content))


@dataclass
class Game:
    revision: str
    source: str
    document: str
    scenario: Scenario
    scene: int = 0
    memory: str = ""
    history: list = field(default_factory=list)
    public_brief: dict = field(default_factory=dict)
    pack_id: str = ""
    completed: dict = field(default_factory=dict)
    pending_question: Question | None = None
    asked_questions: list = field(default_factory=list)
    spoken_dialogue: list = field(default_factory=list)
    repair_feedback: dict | None = None


class StoryGames:
    def __init__(self):
        self.games = {}
        self.lock = RLock()

    def activate(self, session_id, source, document, scenario, revision=None, public_brief=None, pack_id=""):
        # Clean cached opening text at read time without re-embedding the story pack.
        scenario = scenario.model_copy(deep=True)
        scenario.opening_segments = normalize_segments(scenario.opening_segments, scenario.heroine_name)
        if scenario.opening_segments:
            scenario.opening = "\n".join(part.text for part in scenario.opening_segments)
        game = Game(revision or str(uuid4()), source, document, scenario)
        game.pack_id = pack_id
        game.public_brief = dict(public_brief or {})
        game.history = [{"role": "assistant", "content": scenario.opening}]
        game.pending_question = scenario.opening_question
        if game.pending_question:
            game.asked_questions.append(game.pending_question.model_dump())
        game.spoken_dialogue = [p.text for p in scenario.opening_segments if p.kind == "dialogue"]
        self.games[session_id] = game
        return self.describe(game)

    @staticmethod
    def describe(game):
        return {"revision": game.revision, "title": game.scenario.title,
                "scene": game.scenario.scenes[game.scene].title,
                "scene_number": game.scene + 1, "scene_count": len(game.scenario.scenes),
                "answer": game.scenario.opening, "source": game.source,
                "heroine_name": game.scenario.heroine_name,
                "segments": [part.model_dump() for part in game.scenario.opening_segments],
                "ended": False, "used_rag": True, "brief": dict(game.public_brief)}

    def play(self, session_id, revision, message, retrieve, generate):
        game = self.games.get(session_id)
        if game is None or game.revision != revision:
            raise ValueError("진행 중인 시나리오가 없습니다. 파일을 다시 업로드해 주세요.")
        contexts = retrieve(game, message)
        turn = generate(game, message, contexts)
        turn = turn.model_copy(deep=True)
        turn.segments = normalize_segments(turn.segments, game.scenario.heroine_name)
        if turn.segments:
            turn.answer = "\n".join(part.text for part in turn.segments)
        if turn.grounding not in {"supported", "unspecified", "contradiction"}:
            raise RuntimeError("Invalid grounding decision")
        if game.scenario.scenes[game.scene].rules is None and turn.grounding == "contradiction" and (
                not turn.evidence.strip() or turn.evidence not in game.document):
            raise RuntimeError("Contradiction must cite an actual scenario passage")
        # Unsupported proposals never advance a scene or change established memory.
        proposed = None
        clear_pending = False
        structured = game.scenario.scenes[game.scene].rules is not None
        if structured:
            for attempt in range(2):
                proposed, route = propose_progress(game, turn, message)
                target_scene = game.scene + (1 if route and route.ending is None else 0)
                expected_complete = route is not None
                expected_ending = route.ending if route else None
                dialogue = "\n".join(p.text for p in turn.segments if p.kind == "dialogue")
                if turn.next_question and turn.next_question.scene != target_scene:
                    # IDs are scene-local; correct only the index when the spoken question
                    # targets a valid unresolved requirement in the actual response scene.
                    candidate = turn.next_question.model_copy(update={"scene": target_scene})
                    if question_valid(candidate, game, target_scene, proposed, dialogue):
                        turn.next_question = candidate
                valid_q = question_valid(turn.next_question, game, target_scene, proposed, dialogue)
                clear_pending = turn.next_question is not None and not valid_q
                answered_questions = [Question.model_validate(q) for q in game.asked_questions]
                previous_units = set().union(*(dialogue_units(q.text) for q in answered_questions
                    if not question_valid(q, game, game.scene, proposed, q.text)))
                repeated = any(dialogue_units(p.text) & previous_units for p in turn.segments if p.kind == "dialogue")
                reasons = []
                if turn.grounding == "contradiction" and (not turn.evidence.strip() or turn.evidence not in game.document):
                    reasons.append("invalid_evidence")
                if turn.grounding == "supported":
                    if turn.satisfied_requirements and not any(
                            key not in game.completed for key in proposed):
                        reasons.append("unaccepted_completion")
                    if (canonical(message) in SHORT_ANSWERS and game.pending_question
                            and turn.next_question and turn.next_question.scene == game.pending_question.scene):
                        reqs = {r.id: r for r in game.scenario.scenes[game.scene].rules.requirements}
                        old = reqs.get(game.pending_question.requirement_id)
                        new = reqs.get(turn.next_question.requirement_id)
                        if old and new and (old.answer_to or old.id) == (new.answer_to or new.id):
                            reasons.append("short_answer_question_repeated")
                    if turn.scene_complete != expected_complete or turn.ending != expected_ending:
                        reasons.append("progress_mismatch")
                    if repeated:
                        reasons.append("repeated_dialogue")
                    intro = getattr(turn, "scene_introduction", "")
                    if route and route.ending is None and (
                            getattr(turn, "introduced_scene", None) != target_scene
                            or len(intro.strip()) < 20 or intro not in turn.answer):
                        reasons.append("missing_scene_introduction")
                elif turn.scene_complete or turn.ending is not None:
                    reasons.append("unsupported_progress")
                if not reasons:
                    # Server decides state. Ordinary replies do not have to ask a goal question.
                    turn.scene_complete = expected_complete
                    turn.ending = expected_ending
                    if not valid_q:
                        turn.next_question = None
                    if turn.grounding != "supported":
                        turn.next_question = None
                        turn.memory = game.memory
                    break
                logging.getLogger("uvicorn.error").warning(
                    "story_repair attempt=%s reasons=%s scene=%s", attempt, reasons, game.scene)
                if attempt:
                    # No canned story question, and no unverified ending/movement is shown.
                    raise RuntimeError("Story response still inconsistent after one repair")
                repair_game = replace(game, repair_feedback={
                    "reasons": reasons, "expected_scene_complete": None if any(r in reasons for r in
                        ("short_answer_question_repeated", "unaccepted_completion")) else expected_complete,
                    "expected_ending": expected_ending, "response_scene": target_scene,
                    "reconsider_user_choice": any(r in reasons for r in ("short_answer_question_repeated", "unaccepted_completion")),
                    "validated_completed": proposed, "previous_draft": turn.model_dump()})
                turn = generate(repair_game, message, contexts).model_copy(deep=True)
                turn.segments = normalize_segments(turn.segments, game.scenario.heroine_name)
                turn.answer = "\n".join(p.text for p in turn.segments)
                if turn.grounding not in {"supported", "unspecified", "contradiction"}:
                    raise RuntimeError("Invalid grounding decision")
        ended = False
        ending_title = None
        needs_final_choice = False
        if (turn.grounding == "supported" and turn.scene_complete
                and game.scene == len(game.scenario.scenes) - 1
                and (turn.ending is None or not 0 <= turn.ending < len(game.scenario.endings))):
            # Discard unvalidated ending prose; never invent a user's final choice.
            logging.getLogger("uvicorn.error").warning("story_recovery reason=invalid_final_ending")
            needs_final_choice = True
            turn.scene_complete = False
            turn.ending = None
            turn.memory = game.memory
            turn.answer = "이야기를 마무리할 선택을 아직 확인하지 못했어요. 마지막으로 어떤 선택을 할지 조금 더 분명하게 말해 주세요."
            turn.segments = [StorySegment(kind="narration", text=turn.answer)]
        if turn.grounding == "supported":
            if turn.scene_complete:
                if game.scene == len(game.scenario.scenes) - 1:
                    if turn.ending is None or not 0 <= turn.ending < len(game.scenario.endings):
                        raise RuntimeError("Final scene requires a valid ending")
                    ended = True
                    ending_title = game.scenario.endings[turn.ending].title
                elif turn.ending is not None:
                    raise RuntimeError("Cannot end before the final scene")
            elif turn.ending is not None:
                raise RuntimeError("Ending requires scene completion")
        elif turn.scene_complete or turn.ending is not None:
            raise RuntimeError("Unsupported input cannot progress the story")

        if turn.grounding == "supported":
            game.memory = turn.memory
            if structured:
                game.completed = proposed
                if clear_pending or turn.scene_complete:
                    game.pending_question = None
                if (game.pending_question and
                        f"{game.pending_question.scene}:{game.pending_question.requirement_id}" in proposed):
                    game.pending_question = None
                if turn.next_question:
                    game.pending_question = turn.next_question
                    game.asked_questions.append(turn.next_question.model_dump())
                    game.asked_questions = game.asked_questions[-64:]
            if turn.scene_complete and not ended:
                game.scene += 1
        game.spoken_dialogue.extend(p.text for p in turn.segments if p.kind == "dialogue")
        game.spoken_dialogue = game.spoken_dialogue[-80:]
        game.history.extend([{"role": "user", "content": message},
                             {"role": "assistant", "content": turn.answer}])
        game.history = game.history[-16:]
        result = {**self.describe(game), "answer": turn.answer, "ended": ended,
                  "segments": [part.model_dump() for part in turn.segments],
                  "ending_title": ending_title, "grounding": turn.grounding,
                  "evidence": turn.evidence if turn.grounding == "contradiction" else None,
                  "used_rag": turn.grounding == "supported",
                  "retrieved_contexts": contexts,
                  "notice": {"supported": "시나리오 문서 참고",
                             "unspecified": "문서 근거 없음 · 일반 AI 반응 (진행 유지)",
                             "contradiction": "문서 근거 없음 · 시나리오 설정과 충돌 (진행 유지)"}[turn.grounding]}
        if ended:
            del self.games[session_id]
        if needs_final_choice:
            result["notice"] = "마지막 선택 확인 필요 · 진행 유지"
        return result
