import sys
sys.path.insert(0, r'C:/SSAFY/chatbot-project_lab/servers/.venv/Lib/site-packages')
sys.path.insert(0, r'C:/SSAFY/chatbot-project_lab/servers')
import asyncio, json, logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import main
from story_game import StoryGames
from story_progress import fallback_question
from langchain_openai import ChatOpenAI

async def run():
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    logging.getLogger('uvicorn.error').addHandler(logging.StreamHandler())
    async with main.lifespan(main.app):
        main.llm = ChatOpenAI(model=main.GPT_MODEL, api_key=main.OPENAI_API_KEY, base_url=main.BASE_URL, timeout=90, max_retries=0)
        main.app.state.get_story_cache()
        def check(name):
            prepared = main.app.state.prepare_story_pack((Path('clients/sample_data')/name).read_bytes(), name)
            assert prepared['cache_hit']
            games = StoryGames()
            initial = games.activate('test', name, prepared['document'], prepared['scenario'], pack_id=prepared['vector_key'])
            if name.startswith('교토'):
                game = games.games['test']
                game.scene = 1
                game.memory = '사용자가 바뀐 카메라를 확인하고 돌려주었다. 나경이 강변에서 사진을 찍자고 제안했다.'
                game.pending_question = fallback_question(game, 1, {})
                game.history = [{'role': 'assistant', 'content': game.pending_question.text}]
                game.asked_questions = [game.pending_question.model_dump()]
                game.spoken_dialogue = [game.pending_question.text]
                messages = ['좋아요']
            else:
                messages = ['왜 저한테 말을 거셨어요?', '좋아요. 같이 정리할게요.', '요즘 공부가 힘들어서 쉬러 왔어요. 해린 씨는요?']
            rows=[]
            drafts=[]
            def generate(game, message, contexts):
                turn=main.app.state.story_generate(game,message,contexts)
                drafts.append({'turn':turn.model_dump(),'feedback':game.repair_feedback})
                Path('tmp/kyoto-drafts.json').write_text(json.dumps(drafts,ensure_ascii=False,indent=2),encoding='utf-8')
                return turn
            for text in messages:
                try:
                    result = games.play('test', initial['revision'], text, main.app.state.story_retrieve, generate)
                    rows.append({'input': text, 'answer': result['answer'], 'scene': result['scene_number'], 'ended': result['ended']})
                except Exception as exc:
                    rows.append({'input': text, 'error': str(exc)})
                print(json.dumps({'pack': name, **rows[-1]}, ensure_ascii=False), flush=True)
            return {'pack': name, 'rows': rows}
        with ThreadPoolExecutor(max_workers=2) as pool:
            result=list(pool.map(check, ['교토에서 바뀐 필름 카메라.md']))
        Path('tmp/kyoto-final-results.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
        assert not any('error' in row for r in result for row in r['rows'])
        assert result[0]['rows'][0]['scene']==3

asyncio.run(run())
