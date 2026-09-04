# -*- coding: utf-8 -*-
"""윤문된 문단을 .docx 에 직접 반영한다. 표·그림·목차는 건드리지 않는다."""
import io, json, re, sys
from docx import Document
sys.stdout.reconfigure(encoding="utf-8")

DOCX = r"C:\SSAFY\chatbot-project_lab\ChatBot_고찰보고서.docx"
orig = json.load(io.open("experiments/prose.json", encoding="utf-8"))

raw = io.open("_workspace/2026-09-04-001/final.md", encoding="utf-8").read()
raw = re.split(r"<!--\s*HUMANIZE-SUMMARY\s*-->", raw)[0]
new = {}
for m in re.finditer(r"^\[(\d+)\]\s*(.+?)(?=\n\s*\n\[|\Z)", raw, re.S | re.M):
    new[int(m.group(1))] = " ".join(m.group(2).split())

norm = lambda s: " ".join(s.split())
lookup = {norm(o["text"]): new[o["id"]] for o in orig if o["id"] in new}
digits = lambda s: re.findall(r"\d[\d,.]*", s)

doc = Document(DOCX)
hit = miss = skip = 0
warn = []
for par in doc.paragraphs:
    key = norm(par.text)
    if key not in lookup:
        continue
    rep = lookup[key]
    if digits(key) != digits(rep):
        warn.append(key[:50]); skip += 1; continue
    runs = par.runs
    if not runs:
        continue
    runs[0].text = rep
    for r in runs[1:]:
        r.text = ""
    hit += 1
    lookup.pop(key)

miss = len(lookup)
doc.save(DOCX)
print(f"교체 {hit}문단 / 미적용 {miss}문단 / 수치불일치로 건너뜀 {skip}")
if warn:
    print("  수치 불일치:", warn)
if lookup:
    print("  문서에서 못 찾은 문단(앞 40자):")
    for k in list(lookup)[:6]:
        print("   -", k[:40])
