# v22.8 Audit Report

## 변경 사항

- `/sources/manage` 파일 관리 화면에 체크박스 기반 다중 선택 삭제 기능 추가.
- `전체 선택` 체크박스와 `선택 삭제` 버튼 추가.
- 개별 삭제 버튼은 유지하되 `/sources/delete-batch` 처리 흐름으로 통합.
- 삭제 결과 화면에서 삭제된 자료, source_id, chunk 삭제 수, 파일 삭제 여부를 표로 표시.
- 체크박스 스타일 보정: 일반 input width 규칙 때문에 checkbox가 넓게 표시되지 않도록 수정.
- 서버 버전 `2.2.8`로 갱신.

## 검수

- python compileall 통과
- node --check static/study/app.js 통과
- node --check static/solvepad/app.js 통과
- pytest 25 passed
