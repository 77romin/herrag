import sys
sys.path.insert(0, r'C:/SSAFY/chatbot-project_lab/servers/.venv/Lib/site-packages')
sys.path.insert(0, r'C:/SSAFY/chatbot-project_lab/servers')
import asyncio
import json
import logging
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from time import perf_counter
import main
from story_game import StoryGames
from story_progress import fallback_question

CASES = [
 ('교토에서 바뀐 필름 카메라.md', ['맞아요. 어떻게 아셨죠?', '앗 죄송해요. 제 것이 아니군요', '카메라를 확인했어요. 여기 돌려드릴게요.', '좋아요'], '사진 친구로 연락하고 싶어요.'),
 ('이탈리아 베네치아에서 우연히 만난 초등학교 동창.md', ['ㅇㅇ', '여기 근처 한강대교로 걸어갈까?', '그러자'], '친구로 연락하며 지내고 싶어.'),
 ('제주 게스트하우스의 마지막 저녁.md', ['왜 저한테 말을 거셨어요?', '좋아요. 같이 정리할게요.', '요즘 공부가 힘들어서 쉬러 왔어요. 해린 씨는요?'], '친구로 연락하며 지내고 싶어요.'),
 ('심야 라디오의 마지막 게스트.md', ['왜 마지막 방송인가요?', '별명은 가을이라고 불러주세요.', '아직 생각이 정리되지 않아서 잠깐 조용히 있고 싶어요.'], '방송 밖에서 데이트로 만나고 싶어요.'),
 ('비 오는 북카페의 마지막 페이지.md', ['다른 분들은 왜 안 오셨어요?', '책을 많이 안 읽었는데 괜찮을까요?', '오늘은 모임 대신 가볍게 대화하고 싶어요.'], '다음에는 데이트로 만나고 싶어요.')]


async def run():
    logging.getLogger('uvicorn.error').setLevel(logging.INFO)
    logging.getLogger('uvicorn.error').addHandler(logging.StreamHandler())
    async with main.lifespan(main.app):
        # Bound provider stalls in this paid QA run.
        from langchain_openai import ChatOpenAI
        main.llm = ChatOpenAI(model=main.GPT_MODEL, api_key=main.OPENAI_API_KEY,
                             base_url=main.BASE_URL, timeout=90, max_retries=0)
        main.app.state.get_story_cache()
        def check(case):
            name, messages, ending_message = case
            prepared = main.app.state.prepare_story_pack((Path('clients/sample_data') / name).read_bytes(), name)
            assert prepared['cache_hit'], 'Unexpected scenario reanalysis'
            games = StoryGames()
            initial = games.activate('test', name, prepared['document'], prepared['scenario'], pack_id=prepared['vector_key'])
            rows = []
            for text in messages:
                begin = perf_counter()
                try:
                    result = games.play('test', initial['revision'], text, main.app.state.story_retrieve, main.app.state.story_generate)
                    rows.append({'input': text, 'answer': result['answer'], 'scene': result['scene_number'], 'grounding': result['grounding'], 'ended': result['ended'], 'seconds': round(perf_counter()-begin, 2)})
                except Exception as exc:
                    rows.append({'input': text, 'error': str(exc)})
                print(json.dumps({'pack': name, **rows[-1]}, ensure_ascii=False), flush=True)
            # Isolated final-scene test, not a claim of a complete playthrough.
            game = games.games['test']
            game.scene = len(game.scenario.scenes)-1
            game.completed = {}
            game.pending_question = fallback_question(game, game.scene, {})
            game.history = [{'role': 'assistant', 'content': game.pending_question.text}]
            game.spoken_dialogue = [game.pending_question.text]
            game.memory = '현재 마지막 장면에서 앞으로의 관계를 선택할 차례다.'
            try:
                end = games.play('test', initial['revision'], ending_message, main.app.state.story_retrieve, main.app.state.story_generate)
                rows.append({'isolated_final': True, 'input': ending_message, 'answer': end['answer'], 'ended': end['ended'], 'ending_title': end['ending_title'], 'session_deleted': 'test' not in games.games})
            except Exception as exc:
                rows.append({'isolated_final': True, 'error': str(exc)})
            Path('tmp/pack-qa').mkdir(exist_ok=True)
            (Path('tmp/pack-qa') / (Path(name).stem+'.json')).write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps({'pack': name, **rows[-1]}, ensure_ascii=False), flush=True)
            return {'pack': name, 'rows': rows}
        selected = CASES
        if '--recheck' in sys.argv:
            selected = [CASES[0], (CASES[1][0], ['여기 근처 한강대교로 걸어갈까?'], CASES[1][2]),
                        (CASES[3][0], ['왜 마지막 방송인가요?'], CASES[3][2]), CASES[2]]
        with ThreadPoolExecutor(max_workers=3) as pool:
            results = list(pool.map(check, selected))
        filename = 'pack-conversation-recheck.json' if '--recheck' in sys.argv else 'pack-conversation-results.json'
        (Path('tmp') / filename).write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')

asyncio.run(run())
