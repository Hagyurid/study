# v13 SolvePad 수정 보고서

## 반영 내용
- SolvePad 문제/보기/해설 수식 렌더링 보강
- MathJax v3 SVG 렌더링 추가
- JSON 붙여넣기 시 LaTeX 단일 백슬래시를 가능한 범위에서 자동 보정
- `\frac`, `\sqrt`, `\begin`, `\to`, `\theta` 등 주요 LaTeX 명령 보정
- 풀이 작성란 두 손가락 확대/축소 구현
- 확대 상태에서 두 손가락 좌우/상하 시점 이동 구현
- 펜촉만 인식 옵션 유지: Apple Pencil은 필기, 손가락은 제스처용
- 화면 저장 이미지가 현재 확대/이동된 시점 기준으로 나오도록 조정
- v12 UI/다중 파일 업로드 개선 유지
- 패키지 내부 테스트 업로드 파일 제거

## 검수
- `node --check static/solvepad/app.js` 통과
- pytest 전체 통과
