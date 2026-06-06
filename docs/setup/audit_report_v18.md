# v18 Study Note Studio + Exam Cram 보고서

## 추가 기능
- Study Note Studio 추가: `/static/study/index.html`
- 저장된 GPT 생성 정리본/외부정리본/시험직전정리/계산기해설 조회
- Markdown 편집, 이미지 삽입, 형광펜 표시, 저장
- Markdown/Word 다운로드
- MathJax 기반 PDF 인쇄 화면
- 시험 직전 정리 자료 source_type `exam_cram` 추가
- 계산기 프로젝트 ZIP 다운로드 endpoint 추가

## 새 API
- `GET /study/notes`
- `POST /study/notes`
- `GET /study/notes/{source_id}`
- `PUT /study/notes/{source_id}`
- `GET /study/notes/{source_id}/download.md`
- `GET /study/notes/{source_id}/download.docx`
- `GET /study/notes/{source_id}/print`
- `POST /exam-cram`
- `GET /calculator/projects/{project_id}/download.zip`
