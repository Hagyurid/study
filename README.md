# LectureNote Suite

하나의 저장소에서 다음 세 가지를 묶어 관리하는 통합 서버입니다.

1. 강의 정리본 제작
2. 시험 문제팩 생성 + SolvePad 풀이
3. 강의 정리본 기반 CASIO 계산기 PRGM 설계

## 자료 저장소

서버는 다음 자료를 로컬 저장공간에 저장합니다.

- 강의자료
- 기출 문제
- 시험 경향 텍스트
- 원본 교재
- 전체 전사본

업로드된 자료는 텍스트로 추출되어 chunk 단위로 저장됩니다. GPT는 전체 파일을 매번 읽지 않고 필요한 chunk만 검색합니다.

## 실행

```bash
pip install -r requirements.txt
uvicorn app.main:app --reload
```

확인:

```text
http://localhost:8000/health
```

SolvePad:

```text
http://localhost:8000/static/solvepad/index.html
```

CASIO PRGM Tool:

```text
http://localhost:8000/static/casio/index.html
```

## Render 배포

`render.yaml` 포함.

환경변수:

```env
DATABASE_PATH=/var/data/lecturenote_suite.sqlite3
UPLOAD_DIR=/var/data/uploads
PUBLIC_BASE_URL=https://YOUR-RENDER-SERVICE.onrender.com
ACTION_API_KEY=긴_비밀키
```

## Custom GPT

Instructions:

```text
docs/custom_gpt/01_suite_instructions.txt
```

Actions Schema:

```text
docs/actions/openapi.yaml
```

First prompts:

```text
docs/custom_gpt/02_first_prompts.txt
```


## v2 연결 강화

이 버전은 GPT가 생성한 강의 정리본도 다시 자료 저장소에 저장할 수 있습니다.

사용 흐름:

```text
원본 자료 업로드
→ 강의 정리본 생성
→ exportProjectNoteAsSource
→ generated_note 저장
→ 시험 문제팩 생성에 generated_note 활용
→ CASIO PRGM 설계에 generated_note 활용
```

새로 추가된 Action:

```text
POST /sources/text
POST /projects/{project_id}/export-note-source
```

`generated_note`는 이후 `searchSources`에서 검색되어 문제팩 제작과 계산기 PRGM 제작에 사용됩니다.


## v3 프롬프트 강화

추가된 Custom GPT 문서:

```text
docs/custom_gpt/04_solvepad_problempack_contract.txt
docs/custom_gpt/05_casio_prgm_contract.txt
docs/custom_gpt/06_exam_generation_modes.txt
docs/custom_gpt/07_setup_checklist.txt
```

v3는 다음을 강화합니다.

```text
강의 정리본 생성 계약
SolvePad 문제팩 JSON 계약
CASIO PRGM blueprint 계약
시험범위/비범위 구분
동일 시험지 형식 재현
출제 스타일 분석 기반 신규 문제셋
generated_note 기반 후속 제작 연결
```


## v4 정리

v4는 코드 정리와 단원 매핑 기능을 추가합니다.

추가 기능:

```text
외부 정리본 업로드/저장
단원 자동 매핑 결과 저장
업로드 페이지
Unit Map 조회 API
불필요 캐시/테스트 DB 제거
```

새 endpoint:

```text
POST /notes/text
POST /unit-maps
GET  /unit-maps
GET  /unit-maps/{unit_map_id}
```

단원 매핑은 GPT가 판단합니다. 서버는 판단 결과를 저장하고 이후 정리본, 문제팩, 계산기 PRGM 제작에 재사용합니다.


## v5 정리

v5는 선택형 작업 흐름, 정리본 버전 관리, 전사본 용어 보정 기능을 추가합니다.

새 endpoint:

```text
GET  /sources/unmapped
GET  /workflow/options
POST /notes/versions
GET  /notes/versions
GET  /notes/versions/{series_id}/latest
POST /transcripts/revisions
```

작업 흐름:

```text
자료 업로드
→ 미매핑 자료 자동 매핑
→ workflow/options로 과목/단원/모드 선택
→ 정리본/계산기/문제지/전사본 보정 실행
→ 결과 저장
```


## v6 개선

v6는 실제 사용성을 기준으로 파이프라인을 정리했습니다.

추가/수정:
- `/upload` 폼에서 Action key 입력 가능
- workflow plan 저장 기능 추가
- GPT Instructions 최적화
- 세부 규칙 Knowledge 분리
- OpenAPI schema 갱신

새 endpoint:

```text
POST /workflow/plans
GET  /workflow/plans
```

권장 사용:

```text
자료 업로드
→ 미매핑 자료 모두 매핑
→ 선택지 조회
→ 단원/모드 선택
→ workflow plan 저장
→ 정리본/문제지/계산기/전사본 보정 실행
```


## v8 개선

v8은 Custom GPT에서 숫자/짧은 단어만 입력해도 작업을 자동 실행하도록 명령 라우터 규칙을 추가합니다.

예:

```text
1
2
정리 전체
정리 1-3
문제 2
계산기 3,4
전사본 보정
수정
```

추가 문서:

```text
docs/custom_gpt/11_keyword_command_router.txt
```


## v9 과목별 업로드

v9부터 자료 업로드 시 `subject`를 저장합니다.

예:

```text
subject = CRE
source_type = lecture_slides
```

동일 과목의 교재, 강의자료, 전사본, 시험지, 정리본은 같은 subject로 업로드하는 것을 권장합니다.

지원:
- `/upload` 폼에서 과목명 입력
- `/sources?subject=CRE`
- `/sources/unmapped?subject=CRE`
- `/workflow/options?subject=CRE`
- `searchSources`에서 subject 필터 사용
```


## v10 외부 정리본 공간 + 체크포인트

추가 기능:

```text
/notes/upload
/external-notes
/workflow/runs
/workflow/checkpoints
```

긴 작업은 workflow run을 만들고 단계별 checkpoint를 저장합니다.
중간에 멈추면 `계속` 또는 `run-xxxx 계속`으로 이어갈 수 있습니다.


## v11 매핑 현황 + 파일 삭제

추가 기능:

```text
GET    /mapping/status
DELETE /sources/{source_id}
GET    /sources/manage
POST   /sources/{source_id}/delete
```

`/sources/manage`에서 업로드한 자료를 버튼으로 삭제할 수 있습니다.

GPT에서 다음처럼 입력할 수 있습니다.

```text
CRE 매핑 정보
매핑 현황
미매핑 자료 뭐 있어?
src-xxxx 삭제
```


## v12 UI 및 다중 업로드

v12는 브라우저 UI를 개선하고, 여러 파일을 한 번에 업로드할 수 있게 수정합니다.

추가/변경:

```text
/upload: 여러 파일 선택 가능
/notes/upload: 여러 외부 정리본 선택 가능
/sources/manage: 정돈된 파일 관리 UI
POST /sources/upload-batch: 다중 파일 업로드
```

제목은 선택사항입니다. 비워두면 파일명이 자동 제목으로 저장됩니다.

권장 사용:

```text
Action key: ACTION_API_KEY 값
Subject: CRE 같은 과목명, 선택사항이지만 입력 권장
Source type: 자료 유형 선택
Title: 비워두면 파일명 자동 사용
Files: 여러 개 선택 가능
```


## v12 UI + multi upload

v12 improves the built-in web UI.

- Modern dashboard home page
- Cleaner upload page
- Multiple file upload support at `/sources/upload-batch`
- Optional title field; file names are used automatically when title is empty
- Improved external note upload page
- Improved source management page

Recommended user links:

```text
/upload
/notes/upload
/sources/manage
```


## v13 SolvePad fix

SolvePad에서 문제/보기/해설의 LaTeX 수식 렌더링을 MathJax 기반으로 보강했습니다. 풀이 작성란은 Apple Pencil 필기를 유지하면서 두 손가락 확대/축소 및 좌우/상하 이동을 지원합니다. JSON 붙여넣기 시 일부 LaTeX 단일 백슬래시 문제를 자동 보정합니다.


## v14 SolvePad iPad 필기 안정화

SolvePad에서 iPad Safari가 캔버스 필기 중 텍스트 선택/복사 툴바를 띄우는 문제를 막았습니다.

수정:

```text
static/solvepad/index.html
static/solvepad/styles.css
static/solvepad/app.js
tests/test_solvepad_static_v13.py
```

배포 후 Safari에서 페이지를 새로고침하고 문제가 남으면 웹사이트 데이터 캐시를 삭제하세요.


## v15 메뉴형 GPT + 업로드 키 자동 입력

추가 기능:

```text
Custom GPT에서 “메뉴” 입력 시 단계형 메뉴 표시
업로드/외부정리본/파일관리 화면에서 ACTION_API_KEY를 브라우저 localStorage에 저장
다음 업로드부터 키 자동 입력
저장된 키 지우기 버튼 추가
```

업로드 키는 서버에 저장되지 않고 사용자의 브라우저에만 저장됩니다.


## v16 계산기 연결 / 통합 업로드 / 교체 저장

- 홈 화면에 CASIO 계산기 PRGM Studio 링크를 복구했습니다.
- SolvePad와 CASIO Studio에 홈으로 돌아가기 버튼을 추가했습니다.
- 외부 정리본은 별도 화면이 아니라 `/upload`의 자료 유형 `외부 정리본`으로 업로드합니다.
- 계산기 프로그램 저장 시 `analysis_markdown`과 `manual_markdown`을 함께 저장할 수 있습니다.
- 저장된 계산기 프로젝트는 `/static/casio/index.html`에서 불러오고 사용법 문서를 열 수 있습니다.
- 정리본 수정은 `replace_latest=true`, 계산기 수정은 `replace_calculator_project_id`로 기존 생성물을 교체할 수 있습니다.


## v17 최적화

변경 사항:

```text
- searchSources SQL pre-filter 적용으로 큰 자료셋 검색 효율 개선
- subject 필터가 workflow options의 unit map에도 적용되도록 수정
- deleteSource 시 note_versions/transcript_revisions orphan 정리
- Custom GPT Instructions 누적식 문서를 단일 최종 운영 지침으로 정리
- 출력 품질 안정화 Knowledge 추가
```

추가 Knowledge:

```text
docs/custom_gpt/17_output_quality_contract.txt
```


## v18 Study Note Studio + Exam Cram

추가 기능:

```text
/static/study/index.html
/study/notes
/exam-cram
```

Study Note Studio에서 GPT 생성 정리본, 외부 정리본, 시험 직전 정리, 계산기 사용법 문서를 열어 공부하고 수정할 수 있습니다.

지원:
- Markdown 원문 수정
- MathJax 수식 렌더링
- 이미지 삽입
- 형광펜 표시
- 저장
- Markdown/Word 다운로드
- PDF 저장용 인쇄 화면

시험 직전 정리 자료는 `exam_cram` source_type으로 저장됩니다.


## v20 Study Note Studio 개선

Study Note Studio가 Markdown 코드 편집 중심에서 실제 문서형 편집 방식으로 변경되었습니다.

- 본문을 워드처럼 직접 수정
- 텍스트 선택 후 형광펜 적용
- 이미지 파일을 실제 이미지 카드로 삽입
- 긴 이미지 주소/data URL은 기본 화면에서 숨김
- Markdown 원문은 `원문 보기`에서만 확인
- 한글 제목 Word 다운로드 오류 방지


## v21 Study Note WYSIWYG + Past Exam Metadata

- Study Note Studio는 실제 문서형 편집 화면을 기본으로 사용합니다.
- Markdown 원문은 고급 dialog로만 표시됩니다.
- 시험지/기출 업로드 시 현재 시험범위 해당 여부와 사용 방식을 저장합니다.
- 문제팩 제작 시 `exam_scope_status`, `exam_usage_mode`, `exam_range_note`를 기준으로 원문 전사/신규 생성/제외를 구분합니다.

## v22 정리 및 최적화

v22는 v21 기능을 유지하면서 Custom GPT 사용성과 코드/문서 정합성을 정리한 버전입니다.

### 핵심 변경

- `/dashboard` 추가: 메뉴/상태/자료 목록 확인을 한 번에 조회
- Custom GPT Actions 스키마 25개로 정리
- `getDashboard` 우선 정책 반영
- Study Note, SolvePad, CASIO, 시험지 메타 기능 유지
- legacy Action 사용 금지 규칙을 Instructions에 통합
- 오래된 설정 문서와 일부 중복 안내를 정리

### 주요 링크

```text
/
/upload
/static/study/index.html
/static/solvepad/index.html
/static/casio/index.html
/sources/manage
/dashboard
```

### Custom GPT 설정

- Instructions: `docs/custom_gpt/01_suite_instructions.txt`
- Actions Schema: `docs/actions/openapi.yaml`
- Knowledge: `docs/custom_gpt/00_custom_gpt_setup_v6.txt` 참고


## v22.6 Study Note formatting stabilization
- 일반 설명 코드블록이 어둡게 표시되는 문제를 줄이기 위해 Study Note 렌더러를 보정했습니다.
- Markdown 표, 세부 제목, 흐름 박스, 이미지 카드 표시를 안정화했습니다.
- 정리본 생성 지침에서 긴 이미지 삽입 위치 목록을 제거하고, 최종 단계에서 본문 위치에 직접 이미지 카드가 들어가도록 정리했습니다.

## v22.7 notes

Study Note export now converts Markdown tables into real DOCX/print tables. Study Note Studio also includes a `슬라이드 삽입` button: enter a PDF lecture source_id and page number to embed the original slide page as an image card. This requires the PyMuPDF dependency in requirements.txt.
