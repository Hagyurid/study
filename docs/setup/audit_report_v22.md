# v22 코드/문서 정리 및 최적화 보고서

## 반영 내용

1. `/dashboard` endpoint 추가
   - 메뉴/상태/자료 목록 조회를 한 번에 처리
   - Custom GPT의 Action 호출 횟수 감소 목적

2. OpenAPI 스키마 정리
   - OpenAPI 3.1.0 유지
   - `components.schemas: {}` 명시
   - operationId 25개로 정리
   - legacy Action은 제외

3. Custom GPT Instructions 정리
   - 누적된 v19/v20/v21 패치 문구를 단일 최종 운영 지침으로 통합
   - `getDashboard` 우선 정책 추가
   - legacy Action 금지 규칙 명확화

4. Knowledge 계약서 정리
   - CASIO PRGM 계약서 v22 정리
   - Sequential checkpoint 계약서 v22 정리
   - Menu navigation 계약서 v22 정리

5. 사용자 편의 개선
   - 홈에 상태판 링크 추가
   - 업로드/다운로드는 사이트 UI 사용 원칙 유지
   - Study Note, SolvePad, CASIO, 시험지 메타 기능 유지

## 유지한 기능

- 자료 업로드 및 과목별 관리
- 시험지/기출 메타데이터
- Study Note WYSIWYG 편집
- Word/PDF/Markdown 내보내기
- SolvePad 문제팩
- CASIO 계산기 PRGM
- 전사본 보정
- 단원 매핑
- 긴 작업 checkpoint 이어가기

## 의도적으로 남긴 것

서버에는 일부 legacy endpoint가 남아 있다. 기존 데이터와 이전 링크의 호환성 때문이다.
다만 Custom GPT Actions에서는 제외했고, Instructions에서도 사용하지 않도록 제한했다.
