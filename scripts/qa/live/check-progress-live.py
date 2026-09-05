import json
import logging
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "servers"))

from fastapi.testclient import TestClient
import main
from story_api import games

logger = logging.getLogger('uvicorn.error')
logger.setLevel(logging.INFO)
logger.addHandler(logging.StreamHandler())
results = []
with TestClient(main.app) as client:
    name = '이탈리아 베네치아에서 우연히 만난 초등학교 동창.md'
    session = str(uuid4())
    reply = client.post('/upload', data={'session_id': session}, files={
        'file': (name, (Path('clients/sample_data') / name).read_bytes(), 'text/markdown')})
    assert reply.status_code == 200, reply.text
    initial = reply.json()
    assert initial['cache_hit'] and initial['chunks_added'] == 0
    for message, expected_scene in [('ㅇㅇ', 1), ('그러자', 2)]:
        reply = client.post('/story/chat', json={'session_id': session,
            'revision': initial['revision'], 'message': message})
        assert reply.status_code == 200, reply.text
        data = reply.json()
        game = games.games[session]
        row = {'message': message, 'answer': data['answer'], 'scene': data['scene_number'],
               'completed': game.completed, 'pending': game.pending_question.model_dump() if game.pending_question else None}
        results.append(row)
        print(json.dumps(row, ensure_ascii=False), flush=True)
        Path('docs/qa/archive/progress-live-results.json').write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
        assert data['scene_number'] == expected_scene and not data['ended']
        assert initial['segments'][-1]['text'] not in data['answer']
    client.post('/story/reset', json={'session_id': session})
print('PASS: initial acknowledgement stays in scene 1; walking consent advances to scene 2.')
