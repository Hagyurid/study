# v11 최종 점검 및 수정 보고서

## 요청 반영
1. “매핑 정보” 질문 시 무엇이 매핑되어 있는지 현황 조회 기능 추가
2. 업로드 파일 삭제 버튼 추가
3. 관련 GPT Instructions, Keyword Router, OpenAPI schema 최적화

## 새 API
- `GET /mapping/status`
- `DELETE /sources/{source_id}`
- `POST /sources/{source_id}/delete`

## 새 화면
- `/sources/manage`

## 삭제 처리
- sources record 삭제
- source_chunks 삭제
- 로컬 업로드 파일 삭제 시도
- unit_map 내부 과거 참조는 자동 삭제하지 않음
- 누락 참조는 mapping status에서 deletedOrMissingReferences로 확인 가능

## 최종 검수
- 전체 테스트 통과
- 테스트 DB/캐시/pycache 제외
