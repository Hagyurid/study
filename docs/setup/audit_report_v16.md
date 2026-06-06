# v16 수정 보고서

## 반영
- 홈 화면에 CASIO 계산기 PRGM 연결 복구
- SolvePad/CASIO Studio 홈 버튼 추가
- 외부 정리본을 통합 업로드의 자료 유형으로 정리
- 계산기 생성 결과에 analysis_markdown/manual_markdown 저장
- 저장된 계산기 프로젝트 목록/불러오기/삭제/manual 페이지 추가
- 정리본 replace_latest, 계산기 replace_calculator_project_id 교체 저장 지원

## 검수
- pytest 전체 통과
- node --check SolvePad/CASIO 통과
- 테스트 DB/캐시 제거
