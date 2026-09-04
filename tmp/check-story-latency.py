"""Small live smoke comparison, not a statistically representative benchmark."""
import sys
sys.path.insert(0, r'C:/SSAFY/chatbot-project_lab/servers/.venv/Lib/site-packages')
sys.path.insert(0, r'C:/SSAFY/chatbot-project_lab/servers')
import json
import logging
import os
from pathlib import Path
from time import perf_counter
from uuid import uuid4
from fastapi.testclient import TestClient
import main

logging.getLogger('uvicorn.error').setLevel(logging.INFO)
logging.getLogger('uvicorn.error').addHandler(logging.StreamHandler())
name = '이탈리아 베네치아에서 우연히 만난 초등학교 동창.md'
raw = (Path('clients/sample_data') / name).read_bytes()
results = []
with TestClient(main.app) as client:
    for effort in ('default', 'low'):
        os.environ['STORY_REASONING_EFFORT'] = effort
        for message, expected in [('어? 한서윤..?', 'supported'),
                                  ('여기 근처에 인천 곱창집 있는데 그쪽으로 갈래?', 'contradiction')]:
            session = str(uuid4())
            start = client.post('/upload', data={'session_id': session},
                                files={'file': (name, raw, 'text/markdown')})
            assert start.status_code == 200, start.status_code
            data = start.json()
            assert data['cache_hit']
            begin = perf_counter()
            reply = client.post('/story/chat', json={'session_id': session,
                                'revision': data['revision'], 'message': message})
            seconds = round(perf_counter() - begin, 2)
            body = reply.json()
            row = {'effort': effort, 'expected': expected, 'seconds': seconds,
                   'status': reply.status_code, 'grounding': body.get('grounding'),
                   'scene_number': body.get('scene_number')}
            results.append(row)
            Path('tmp/story-latency-results.json').write_text(
                json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
            print(json.dumps(row, ensure_ascii=False), flush=True)
            client.post('/story/reset', json={'session_id': session})
            if reply.status_code != 200:
                raise RuntimeError('Live reply failed; see server stage log')
            assert body['grounding'] == expected
            assert not body['ended'] and body['scene_number'] == 1
            assert body['answer'] == '\n'.join(part['text'] for part in body['segments'])
Path('tmp/story-latency-results.json').write_text(
    json.dumps(results, ensure_ascii=False, indent=2), encoding='utf-8')
