import logging
import os
import sys
from pathlib import Path
from time import perf_counter
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "servers"))

from fastapi.testclient import TestClient
import main
from story_api import games

os.environ['STORY_REASONING_EFFORT'] = 'auto'
logger = logging.getLogger('uvicorn.error')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
with TestClient(main.app) as client:
    session = str(uuid4())
    name = '이탈리아 베네치아에서 우연히 만난 초등학교 동창.md'
    start = client.post('/upload', data={'session_id': session}, files={
        'file': (name, (Path('clients/sample_data') / name).read_bytes(), 'text/markdown')})
    assert start.status_code == 200 and start.json()['cache_hit']
    game = games.games[session]
    game.scene = 1
    game.memory = '서윤과 사용자는 초등학교 동창임을 확인했다.'
    game.history.append({'role': 'assistant', 'content': '시간 있으면 함께 좀 걸을래? 운하 쪽으로 가면서 이야기하고 싶어.'})
    begin = perf_counter()
    reply = client.post('/story/chat', json={'session_id': session,
                        'revision': start.json()['revision'], 'message': '그러자'})
    print('seconds=', round(perf_counter() - begin, 2), 'status=', reply.status_code)
    assert reply.status_code == 200
    body = reply.json()
    assert body['grounding'] == 'supported' and not body['ended']
    assert body['scene_number'] in (2, 3)
    print('answer=', body['answer'], 'scene=', body['scene_number'])
    client.post('/story/reset', json={'session_id': session})
