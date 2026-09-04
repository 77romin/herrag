# -*- coding: utf-8 -*-
"""윤문 결과(final.md)를 make_docx.py 의 문자열 리터럴에 되돌린다."""
import ast, io, json, re, sys
sys.stdout.reconfigure(encoding="utf-8")

SRC = "experiments/make_docx.py"
src = io.open(SRC, encoding="utf-8").read()
orig = json.load(io.open("experiments/prose.json", encoding="utf-8"))

# final.md 파싱 ([n] 본문)
raw = io.open("_workspace/2026-09-04-001/final.md", encoding="utf-8").read()
raw = raw.split("<!-- HUMANIZE-SUMMARY -->")[0]
new = {}
for m in re.finditer(r"^\[(\d+)\]\s*(.+?)(?=\n\s*\n\[|\Z)", raw, re.S | re.M):
    new[int(m.group(1))] = " ".join(m.group(2).split())
print(f"윤문본 문단 {len(new)}개 / 원본 {len(orig)}개")

# 숫자 보존 검사
digits = lambda s: re.findall(r"\d[\d,.]*", s)
bad = [o["id"] for o in orig
       if o["id"] in new and digits(o["text"]) != digits(new[o["id"]])]
if bad:
    print("!! 수치가 달라진 문단:", bad)
    for i in bad[:5]:
        t = next(o for o in orig if o["id"] == i)
        print(f"  [{i}] 원본 {digits(t['text'])}\n       윤문 {digits(new[i])}")
else:
    print("수치 보존 확인 — 전 문단 일치")

# 같은 순회로 노드를 찾아 치환 (뒤에서부터)
tree = ast.parse(src)
targets = []
idx = 0
for node in ast.walk(tree):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        continue
    if node.func.id not in ("p", "bullet") or not node.args:
        continue
    a = node.args[0]
    if not isinstance(a, ast.Constant) or not isinstance(a.value, str):
        continue
    if len(a.value) < 25 or a.value.startswith(("표.", "그림", "※")):
        continue
    idx += 1
    if idx in new and orig[idx - 1]["text"] == a.value:
        targets.append((a, new[idx]))

lines = src.splitlines(keepends=True)
offs = [0]
for L in lines:
    offs.append(offs[-1] + len(L))

def pos(lineno, col):
    return offs[lineno - 1] + len(lines[lineno - 1][:col].encode("utf-8").decode("utf-8"))

spans = []
for a, txt in targets:
    s0 = offs[a.lineno - 1] + a.col_offset
    s1 = offs[a.end_lineno - 1] + a.end_col_offset
    spans.append((s0, s1, json.dumps(txt, ensure_ascii=False)))

for s0, s1, rep in sorted(spans, key=lambda x: -x[0]):
    src = src[:s0] + rep + src[s1:]

io.open(SRC, "w", encoding="utf-8").write(src)
ast.parse(src)   # 문법 확인
print(f"치환 {len(spans)}곳 / 문법 검사 통과")
