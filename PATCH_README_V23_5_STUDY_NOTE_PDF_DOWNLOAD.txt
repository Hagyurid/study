# v23.5 Study Note PDF Direct Download Patch

## 문제
파일 관리의 '선택 문서 통합 PDF'는 실제 PDF 파일을 내려주는 기능이 아니라 HTML 인쇄 화면을 여는 방식이었다.
그래서 GPT 생성 정리본(generated_note)을 여러 개 선택해 한 번에 다운로드할 때 Markdown -> PDF 변환 경로가 없어 오류 또는 빈/잘못된 출력처럼 보일 수 있었다.

## 수정
- `/study/notes/{source_id}/download.pdf` 추가
  - 단일 Study Note Markdown을 서버에서 PDF로 변환해 바로 다운로드한다.
- `/sources/download-bundle.pdf` 추가
  - 파일 관리에서 선택한 문서형 source를 매핑/단원 순서로 정렬한 뒤 하나의 PDF로 묶어 바로 다운로드한다.
- 파일 관리 버튼 추가
  - `선택 정리본 PDF 바로 다운로드`
- 기존 `선택 문서 통합 PDF`는 유지
  - 브라우저 인쇄/수동 PDF 저장용.
- Markdown 변환 범위
  - 제목, 문단, 목록, 표, 코드블록, 이미지, `SLIDE_IMAGE` 마커.
- 문제팩은 기존처럼 `선택 문제지 PDF`, `선택 해설지 PDF` 사용.

## 적용 파일
- `app/main.py`

## 검수
- `python -m compileall -q app` 통과
- `node --check static/solvepad/app.js` 통과
- `_study_notes_pdf_bytes()`가 `%PDF` 바이트를 생성하는 것 확인

## 참고
전체 pytest는 기존 계산기 direct-content 테스트 1건이 실패했다. 실패 지점은 calculator generate 파일명 처리이며, 이번 Study Note PDF 패치와 직접 관련 없는 기존 상태다.
