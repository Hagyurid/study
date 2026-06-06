# v4 코드 점검 및 수정 보고서

## 제거한 불필요 파일
- `.pytest_cache/`
- `data/test.sqlite3`
- `data/test_v2.sqlite3`
- `data/test_v3.sqlite3`
- Python `__pycache__`

## 코드 정리
- `app/db.py`를 재작성해 시간 처리 경고를 `datetime.now(UTC)`로 수정
- 중복적인 generated_note/external_note 저장 로직을 `save_text_source`로 통합
- 검색/저장/프로젝트/문제팩/계산기/단원매핑 기능을 명확히 분리
- `app/main.py`에서 사용하지 않는 import 제거
- 루트 `/`에 업로드/도구/문서 링크 추가
- `/upload` 간단 업로드 페이지 추가

## 새 기능
- 외부 정리본 저장: `/notes/text`, `/sources/text`, `/sources/upload` + source_type `external_note`
- 제작 정리본 저장: `/projects/{project_id}/export-note-source` + source_type `generated_note`
- 단원 자동 매핑 저장:
  - `POST /unit-maps`
  - `GET /unit-maps`
  - `GET /unit-maps/{unit_map_id}`

## 효율적인 경로
1. 자료 업로드
2. 단원 매핑 생성
3. 정리본 생성
4. generated_note 저장
5. 시험 문제팩 생성
6. 계산기 PRGM 생성

## 주의
단원 매핑 판단 자체는 서버가 하지 않는다. GPT가 searchSources 결과를 바탕으로 판단하고, 서버는 그 판단 결과를 구조화해 저장한다.
