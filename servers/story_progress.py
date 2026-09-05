"""Evidence-backed progression and question tracking, independent of HTTP/LLM calls."""
from __future__ import annotations
import re
from pydantic import BaseModel, Field, model_validator


class Requirement(BaseModel):
    id: str = Field(min_length=1, max_length=60)
    description: str = Field(min_length=1, max_length=500, pattern="^사용자가")
    evidence: str = Field(min_length=1, max_length=1000)
    question: str = Field(min_length=1, max_length=300, pattern=r"\?$" )
    answer_to: str | None = None


class Route(BaseModel):
    all_of: list[str] = Field(min_length=1, max_length=12)
    ending: int | None = None


class Rules(BaseModel):
    requirements: list[Requirement] = Field(min_length=1, max_length=12)
    routes: list[Route] = Field(min_length=1, max_length=12)

    @model_validator(mode="after")
    def references(self):
        ids = {r.id for r in self.requirements}
        if len(ids) != len(self.requirements):
            raise ValueError("Duplicate requirement IDs")
        if any(r.answer_to is not None and r.answer_to not in ids for r in self.requirements):
            raise ValueError("Unknown question anchor")
        targets = {r.id: r.answer_to for r in self.requirements}
        if any(r.answer_to and targets[r.answer_to] is not None for r in self.requirements):
            raise ValueError("Question anchors must point directly to a primary requirement")
        if any(not set(route.all_of) <= ids for route in self.routes):
            raise ValueError("Unknown requirement in route")
        for route in self.routes:
            route_anchors = [targets[id] or id for id in route.all_of]
            if len(set(route_anchors)) != len(route_anchors):
                raise ValueError("A route cannot require multiple answers to one question")
        used = set().union(*(set(r.all_of) for r in self.routes))
        anchors = {r.answer_to for r in self.requirements if r.answer_to}
        if used | anchors != ids:
            raise ValueError("Every requirement must be a route condition or question anchor")
        return self


class Question(BaseModel):
    scene: int = Field(ge=0)
    requirement_id: str = Field(min_length=1, max_length=60)
    text: str = Field(min_length=1, max_length=300)


class Completion(BaseModel):
    requirement_id: str = Field(min_length=1, max_length=60)
    evidence: str = Field(min_length=1, max_length=2000)
    value: str = Field(min_length=1, max_length=300)


def canonical(text):
    return re.sub(r"[\W_]+", "", text, flags=re.UNICODE).lower()


def dialogue_units(text):
    return {canonical(part) for part in re.split(r"(?<=[?!。！？])\s*|(?<=\.)\s+|\n+", text)
            if len(canonical(part)) >= 6}


SHORT_ANSWERS = {"ㅇㅇ", "ㅇ", "응", "네", "예", "그래", "그러자", "좋아", "좋아요",
                 "알겠어", "알겠어요", "아니", "아니요", "싫어", "싫어요", "ㄴㄴ"}


def propose_progress(game, turn, message):
    """Stage changes locally; caller commits only after all response checks pass."""
    rules = game.scenario.scenes[game.scene].rules
    completed = dict(game.completed)
    if turn.grounding != "supported":
        return completed, None
    ids = {r.id for r in rules.requirements}
    anchors = {r.id: r.answer_to or r.id for r in rules.requirements}
    route_ids = set().union(*(set(r.all_of) for r in rules.routes))
    short = canonical(message) in SHORT_ANSWERS
    pending = game.pending_question
    proposals = {}
    for item in turn.satisfied_requirements:
        if item.requirement_id in route_ids:
            proposals.setdefault(anchors[item.requirement_id], set()).add(item.requirement_id)
    chosen = {anchors[r.id] for r in rules.requirements if f"{game.scene}:{r.id}" in completed}
    for item in turn.satisfied_requirements:
        if item.requirement_id not in route_ids or not item.evidence.strip() or item.evidence not in message:
            continue
        if len(proposals[anchors[item.requirement_id]]) != 1 or anchors[item.requirement_id] in chosen:
            continue
        # A bare yes/no can answer exactly the previous question, never a new one.
        if short and (pending is None or pending.scene != game.scene
                      or anchors[pending.requirement_id] != anchors[item.requirement_id]):
            continue
        key = f"{game.scene}:{item.requirement_id}"
        if key not in completed:
            completed[key] = {**item.model_dump(), "scene": game.scene, "user_message": message}
    done = {r.id for r in rules.requirements if f"{game.scene}:{r.id}" in completed}
    matches = [route for route in rules.routes if set(route.all_of) <= done]
    # Ambiguous mutually exclusive ending choices must not select an arbitrary route.
    route = matches[0] if matches and len({r.ending for r in matches}) == 1 else None
    return completed, route


def fallback_question(game, scene, completed):
    done_anchors = {r.answer_to or r.id for r in game.scenario.scenes[scene].rules.requirements
                    if f"{scene}:{r.id}" in completed}
    for req in game.scenario.scenes[scene].rules.requirements:
        if (req.answer_to or req.id) not in done_anchors:
            return Question(scene=scene, requirement_id=req.id, text=req.question)
    return None


def question_valid(question, game, scene, completed, dialogue):
    if question is None or question.scene != scene:
        return False
    reqs = game.scenario.scenes[scene].rules.requirements
    anchors = {r.id: r.answer_to or r.id for r in reqs}
    done = {anchors[r.id] for r in reqs if f"{scene}:{r.id}" in completed}
    return (question.requirement_id in anchors
            and anchors[question.requirement_id] not in done
            and f"{scene}:{question.requirement_id}" not in completed
            and question.text in dialogue)
