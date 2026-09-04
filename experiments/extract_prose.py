# -*- coding: utf-8 -*-
"""make_docx.py 안의 산문만 뽑아 윤문용 파일로 만든다. 표·코드·캡션은 건드리지 않는다."""
import ast, io, json, sys
sys.stdout.reconfigure(encoding="utf-8")
SRC = "experiments/make_docx.py"
tree = ast.parse(io.open(SRC, encoding="utf-8").read())

items = []
for node in ast.walk(tree):
    if not isinstance(node, ast.Call) or not isinstance(node.func, ast.Name):
        continue
    if node.func.id not in ("p", "bullet"):
        continue
    if not node.args or not isinstance(node.args[0], ast.Constant):
        continue
    txt = node.args[0].value
    if not isinstance(txt, str) or len(txt) < 25:
        continue
    if txt.startswith(("표.", "그림", "※")):
        continue
    items.append({"id": len(items) + 1, "line": node.lineno, "text": txt})

io.open("experiments/prose.json", "w", encoding="utf-8").write(
    json.dumps(items, ensure_ascii=False, indent=1))
with io.open("experiments/prose.md", "w", encoding="utf-8") as f:
    for it in items:
        f.write(f"[{it['id']}] {it['text']}\n\n")
print(f"산문 {len(items)}개 / {sum(len(i['text']) for i in items):,}자")
