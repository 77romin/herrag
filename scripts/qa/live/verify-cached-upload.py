import json
import sys
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "servers"))

from fastapi.testclient import TestClient
import main
root=Path('servers')
names=sorted({c['file'] for c in json.loads((root/'story_test_cases.json').read_text(encoding='utf-8'))})
with TestClient(main.app) as client:
    session=str(uuid4())
    for name in names:
        raw=(Path('clients/sample_data')/name).read_bytes()
        response=client.post('/upload',data={'session_id':session},files={'file':(name,raw,'text/markdown')})
        assert response.status_code==200, response.status_code
        data=response.json()
        assert data['cache_hit'] is True
        assert data['scene_number']==1
        assert data['segments'] and data['heroine_name']
        assert data['brief'], 'Expected a reviewed introduction'
        assert 'document' not in data and 'scenario' not in data
        print('API REUSED:',data['title'],'brief fields:',len(data['brief']))
    assert client.post('/story/reset',json={'session_id':session}).status_code==200
    again=client.post('/upload',data={'session_id':session},files={'file':(name,raw,'text/markdown')}).json()
    assert again['cache_hit'] and again['revision']!=data['revision']
    print('PASS: reset preserves prepared pack; new session revision starts fresh.')
