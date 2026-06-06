# v17 최종 최적화 보고서

## 코드 점검/최적화
- searchSources가 전체 chunk를 메모리에 모두 올리지 않고 SQL LIKE pre-filter 후 scoring하도록 수정.
- workflow options가 subject 필터를 unit map/unit 목록에도 적용하도록 수정.
- 단원 source id 추출 로직을 `_unit_source_ids`와 `UNIT_SOURCE_FIELDS`로 통합.
- deleteSource가 source_chunks뿐 아니라 관련 note_versions, transcript_revisions orphan도 정리하도록 수정.
- 추가 인덱스: source_chunks(source_id, chunk_index), note_versions(source_id).
- 빈 title의 text source는 original_name 기반으로 자동 보정.
- FastAPI version을 1.6.0으로 갱신.

## Custom GPT 텍스트 최적화
- 누적 버전 패치형 Instructions를 단일 최종 운영 지침으로 재작성.
- 메뉴, 자료 우선순위, 단원 매핑, 정리본, 문제팩, 계산기, 교체 저장, 품질 검수를 한 문서에 통합.
- 출력 품질 안정화 계약 `17_output_quality_contract.txt` 추가.

## 검수
- pytest 전체 통과.
- Python compileall 통과.
- SolvePad JS syntax check 통과.
- 테스트 DB/cache/pycache 제거.
