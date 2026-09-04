"""Conservative cleanup for explicit speaker attributions mislabeled as dialogue."""
import re


def normalize_segments(segments, heroine_name):
    names = {"그녀"}
    if heroine_name and heroine_name != "상대방":
        names.add(heroine_name)
        if re.fullmatch(r"[가-힣]{3}", heroine_name):
            names.add(heroine_name[1:])
    speaker = "(?:" + "|".join(re.escape(name) for name in sorted(names, key=len, reverse=True)) + ")"
    attribution = re.compile(
        rf"^(?P<description>{speaker}(?:은|는|이|가)?\s+"
        r"(?:(?:조심스럽게|조용히|부드럽게|작게|웃으며|미소를 지으며|고개를 끄덕이며)\s+){0,3}"
        r"(?:말한다|말했다|묻는다|물었다|답한다|답했다|대답한다|대답했다|속삭인다|덧붙인다))"
        r"(?=$|\s|[.:：。\"“「])(?:[.:：。]\s*|\s*)"
    )
    label = re.compile(rf"^{speaker}\s*[:：]\s*")
    result = []
    for segment in segments:
        if segment.kind != "dialogue":
            result.append(segment)
            continue
        text = segment.text.strip()
        match = attribution.match(text)
        if match:
            description = match.group("description") + "."
            result.append(segment.model_copy(update={"kind": "narration", "text": description}))
            text = text[match.end():].strip()
        else:
            text = label.sub("", text, count=1)
        # Only strip a matching outer quotation pair after removing an attribution.
        if match and len(text) >= 2 and (text[0], text[-1]) in {('"', '"'), ('“', '”'), ('「', '」')}:
            text = text[1:-1].strip()
        if text:
            result.append(segment.model_copy(update={"text": text}))
    return result
