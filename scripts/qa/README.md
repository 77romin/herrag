# QA 도구

개발 중 임시로 만든 검증 코드 가운데 반복 실행할 가치가 있는 스크립트를 보관합니다.
모든 명령은 프로젝트 루트에서 실행합니다.

## frontend

브라우저 없이 DOM을 모사하여 화면 상태, 스토리 소개, 대사 분리와 렌더링을 검증하는 Node.js 스크립트입니다.

```bash
node scripts/qa/frontend/qa-story-ui.cjs
node scripts/qa/frontend/qa-story-brief.cjs
node scripts/qa/frontend/qa-story-segments.cjs
node scripts/qa/frontend/qa-story-sentences.cjs
```

## live

실제 애플리케이션 구성과 모델 호출을 이용하는 통합·스모크 검증입니다. `servers/.env`와 Python 의존성이 필요하며 일부 스크립트는 모델 API 비용이 발생합니다.

- `verify-cached-upload.py`: 준비된 스토리팩 캐시와 초기 응답 검증
- `check-progress-live.py`: 짧은 응답 이후 장면 진행 검증
- `check-short-reply.py`: 짧은 동의 응답 처리 검증
- `check-story-latency.py`: 추론 설정별 지연시간 스모크 비교
- `check-pack-conversations.py`: 기본 스토리팩 전체 대화 검증
- `check-dialogue-final.py`: 대표 팩의 대화 및 결말 검증

실행 결과는 `docs/qa/archive/`에 저장합니다.
