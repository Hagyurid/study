# 안정 실행 파이프라인 v6

## 권장 실행 순서

1. `/upload`에서 자료 업로드
   - lecture_slides
   - textbook
   - transcript
   - exam_trend
   - past_exam
   - external_note

2. GPT에 입력:
   `업로드한 자료들 중 매핑 안 된 자료들 모두 매핑 진행해.`

3. GPT에 입력:
   `저장된 자료와 매핑 정보 기준으로 과목/단원/모드 선택지를 보여줘.`

4. 사용자가 선택:
   - 과목명 또는 자료 묶음
   - 단원 여러 개
   - 모드: 정리본 / 문제지 / 계산기 / 전사본 보정

5. GPT가 createWorkflowPlan으로 선택 내용을 저장.

6. 모드별 실행:
   - 정리본: saveNoteVersion으로 버전 저장
   - 문제지: saveProblemPack으로 SolvePad import_url 생성
   - 계산기: validateCalculatorBlueprint → generateCalculatorProgram
   - 전사본 보정: saveTranscriptRevision
   - 단원 매핑: saveUnitMap

## 실사용 개선점

- `/upload` 폼에 Action key 입력칸 추가. Render에서 ACTION_API_KEY를 설정해도 브라우저 업로드가 막히지 않음.
- workflow plan 저장 추가. 사용자가 어떤 과목/단원/모드를 골랐는지 서버에 기록 가능.
- GPT Instructions를 짧고 강한 우선순위 중심으로 재작성.
- 긴 세부 규칙은 Knowledge 파일로 분리.
