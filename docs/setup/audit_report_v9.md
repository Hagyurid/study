
# v9 수정 보고서

## 요청 반영
자료 업로드를 과목별로 할 수 있도록 `subject` 필드를 추가했습니다.

## 수정 내용
- sources 테이블에 subject 컬럼 추가
- 기존 DB도 자동 마이그레이션되도록 ALTER TABLE 처리
- /upload 폼에 Subject / 과목명 입력칸 추가
- /sources, /sources/unmapped, /workflow/options에서 subject 필터 지원
- searchSources에서 subject 필터 지원
- notes/text, sources/text, note versions, transcript revisions에 subject 저장 지원
- GPT Instructions에 과목별 작업 규칙 추가
- keyword router에 "CRE 정리 1-3" 같은 과목명 포함 명령 규칙 추가

## 사용 예
- CRE 정리 1-3
- 수학2 문제 전체
- 반응공학 매핑
- 미적분 전사본 보정
