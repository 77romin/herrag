from pathlib import Path
p=Path('tmp/check-dialogue-final.py')
s=p.read_text(encoding='utf-8')
s=s.replace("rows=[]", "rows=[]\n            drafts=[]\n            def generate(game, message, contexts):\n                turn=main.app.state.story_generate(game,message,contexts)\n                drafts.append({'turn':turn.model_dump(),'feedback':game.repair_feedback})\n                Path('tmp/kyoto-drafts.json').write_text(json.dumps(drafts,ensure_ascii=False,indent=2),encoding='utf-8')\n                return turn")
s=s.replace('main.app.state.story_retrieve, main.app.state.story_generate)', 'main.app.state.story_retrieve, generate)')
s=s.replace("['교토에서 바뀐 필름 카메라.md','제주 게스트하우스의 마지막 저녁.md']", "['교토에서 바뀐 필름 카메라.md']")
s=s.replace("Path('tmp/dialogue-final-results.json')", "Path('tmp/kyoto-final-results.json')")
Path('tmp/debug-kyoto-reply.py').write_text(s,encoding='utf-8')
