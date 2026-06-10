# v23.4 Local Pack / Cascade Delete / Calculator UI Patch

## 목적
- SolvePad 문제팩 관리에서 기기 저장 문제팩과 메인 저장소 문제팩을 탭으로 분리
- 기기 문제팩 삭제 시 오답, 필기, 첨부 이미지까지 함께 삭제
- 서버 메인 저장소에서 사라진 문제팩의 로컬 오답/필기 캐시 자동 정리
- source 삭제 시 정리본 버전 기록, 문제팩, 문제팩 버전, 관련 source까지 cascade 삭제
- CASIO PRGM Studio 프로젝트 목록 검색/최근 프로젝트/카드형 불러오기 UI 개선

## 적용 파일
- app/db.py
- app/main.py
- static/solvepad/index.html
- static/solvepad/app.js
- static/solvepad/styles.css
- static/casio/index.html

## 주의
서버가 브라우저 IndexedDB를 직접 지울 수는 없습니다. 대신 SolvePad가 메인 저장소 목록을 새로고침할 때, 서버에서 삭제된 문제팩의 server:* 오답/필기/첨부 캐시를 자동 정리합니다.
