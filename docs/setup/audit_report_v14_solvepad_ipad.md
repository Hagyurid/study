# v14 SolvePad iPad Pencil Guard

## 수정 내용
- iPad Safari에서 풀이 작성 중 텍스트 선택 툴바가 뜨는 문제 방지
- `.paper-viewport`, `.paper`, `canvas.ink`에 native touch/callout/selection 차단
- `selectionchange` 발생 시 최근 필기/제스처 중이면 selection 제거
- 전체 SolvePad UI에 `-webkit-user-select:none`, `-webkit-touch-callout:none` 적용
- 입력창/textarea/select는 텍스트 선택 가능 유지
- 기존 MathJax 수식 렌더링, LaTeX 보정, 두 손가락 확대/이동 기능 유지

## 검수
- pytest 전체 통과
- `node --check static/solvepad/app.js` 통과
