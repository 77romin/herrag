from pathlib import Path
p=Path('servers/story_game.py')
s=p.read_text(encoding='utf-8')
a=s.index('        if structured:\n', s.index('    def play('))
b=s.index('        ended = False',a)
s=s[:a]+'''        if structured:
            for attempt in range(2):
                proposed, route = propose_progress(game, turn, message)
                target_scene = game.scene + (1 if route and route.ending is None else 0)
                expected_complete = route is not None
                expected_ending = route.ending if route else None
                dialogue = "\\n".join(p.text for p in turn.segments if p.kind == "dialogue")
                valid_q = question_valid(turn.next_question, game, target_scene, proposed, dialogue)
                previous_units = set().union(*(dialogue_units(old) for old in game.spoken_dialogue))
                repeated = any(dialogue_units(p.text) & previous_units for p in turn.segments if p.kind == "dialogue")
                reasons = []
                if turn.grounding == "supported":
                    if turn.scene_complete != expected_complete or turn.ending != expected_ending:
                        reasons.append("progress_mismatch")
                    if turn.next_question is not None and not valid_q:
                        reasons.append("invalid_question")
                    if repeated:
                        reasons.append("repeated_dialogue")
                    if route and route.ending is None and getattr(turn, "introduced_scene", None) != target_scene:
                        reasons.append("missing_scene_introduction")
                elif turn.scene_complete or turn.ending is not None:
                    reasons.append("unsupported_progress")
                if not reasons:
                    # Server decides state. Ordinary replies do not have to ask a goal question.
                    turn.scene_complete = expected_complete
                    turn.ending = expected_ending
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
                    "reasons": reasons, "expected_scene_complete": expected_complete,
                    "expected_ending": expected_ending, "response_scene": target_scene,
                    "validated_completed": proposed, "previous_draft": turn.model_dump()})
                turn = generate(repair_game, message, contexts).model_copy(deep=True)
                turn.segments = normalize_segments(turn.segments, game.scenario.heroine_name)
                turn.answer = "\\n".join(p.text for p in turn.segments)
                if turn.grounding not in {"supported", "unspecified", "contradiction"}:
                    raise RuntimeError("Invalid grounding decision")
                if turn.grounding == "contradiction" and (not turn.evidence.strip() or turn.evidence not in game.document):
                    raise RuntimeError("Contradiction must cite an actual scenario passage")
''' +s[b:]
p.write_text(s,encoding='utf-8')
