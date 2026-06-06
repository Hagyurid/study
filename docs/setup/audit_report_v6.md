# v6 점검 및 개선 보고서

## 파이프라인 점검
기존 v5는 기능은 많지만 실제 사용 흐름에서 다음 문제가 있었다.

1. `/upload` 폼이 ACTION_API_KEY 설정 시 인증 헤더를 보낼 수 없어 업로드가 막힐 수 있음.
2. 사용자가 과목/단원/모드를 고른 선택 상태를 저장하는 전용 구조가 없음.
3. Instructions가 계속 누적되어 길어져 GPT가 일부 규칙을 놓칠 가능성이 있음.
4. 세부 계약과 핵심 실행 규칙이 섞여 있음.

## v6 수정
1. `/upload` 폼에 Action key 입력칸 추가.
2. `workflow_plans` 테이블 추가.
3. `POST /workflow/plans`, `GET /workflow/plans` 추가.
4. GPT Instructions를 핵심 실행 규칙 중심으로 재작성.
5. 세부 규칙은 Knowledge 파일에 맡기도록 정리.
6. OpenAPI schema 갱신.
7. 캐시/테스트 DB/pycache 제거.

## 권장 경로
자료 업로드 → 미매핑 자료 매핑 → 선택지 조회 → workflow plan 저장 → 작업 실행 → 결과 저장.

## 테스트
전체 API 흐름 테스트 통과.
