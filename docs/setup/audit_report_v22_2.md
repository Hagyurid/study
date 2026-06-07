# v22.2 Invalid Action Key UI Hotfix

## 수정 목적
- 홈 화면의 `상태판`, `매핑` 버튼이 보호된 JSON API(`/dashboard`, `/mapping/status`)를 직접 열어 `Invalid action key`가 표시되는 문제 수정.
- Study Note Studio에서 액션 키가 비어 있을 때 원시 JSON 오류가 뜨는 문제 수정.
- iPad Safari 캐시가 이전 JS를 잡는 문제를 줄이기 위해 Study Note 정적 파일 query version 갱신.

## 변경 파일
- `app/main.py`
- `static/study/index.html`
- `static/study/app.js`
- `docs/setup/audit_report_v22_2.md`

## 변경 내용
- 홈 화면의 상태판/매핑 링크를 `/status` UI로 변경.
- `/status` HTML 페이지 추가. 저장된 localStorage 액션 키로 `/dashboard`, `/mapping/status`를 호출.
- Study Note Studio API 호출 전 액션 키 존재 여부 검사.
- `Invalid action key` 원시 JSON 대신 한국어 안내 메시지 표시.
- `/health` version을 `2.2.2`로 갱신.

## 검수
- `python -m compileall app` 통과
- `node --check static/study/app.js` 통과
- `node --check static/solvepad/app.js` 통과
- `pytest -q` 25 passed
