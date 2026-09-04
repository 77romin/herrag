"""Conservative routing for short conversational acknowledgements."""

SHORT_REPLIES = frozenset({
    "응", "네", "그래", "그러자", "좋아", "좋아요", "알겠어", "알겠어요",
    "안녕", "안녕하세요", "반가워", "반가워요", "고마워", "고마워요",
})


def choose_effort(message, model, final_scene, setting="auto"):
    setting = setting.strip().lower()
    if setting not in {"auto", "default", "minimal", "low", "medium", "high"}:
        raise ValueError("Invalid STORY_REASONING_EFFORT")
    if setting != "auto":
        return setting
    # Match complete utterances, never substrings of a factual proposal.
    short_reply = message.strip().rstrip(".!~… ")
    if model == "gpt-5-mini" and not final_scene and short_reply in SHORT_REPLIES:
        return "low"
    return "default"
