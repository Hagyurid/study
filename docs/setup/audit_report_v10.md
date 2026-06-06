# v10 수정 보고서

## 요청 반영
1. GPT 생성 정리본과 별도로 사용자 업로드 정리본 전용 공간 추가
2. 긴 작업을 순차 진행하고 checkpoint로 이어가기 가능하게 수정

## 새 사용자 화면
- `/notes/upload`: external_note 전용 업로드 페이지

## 새 API
- `GET /external-notes`
- `POST /workflow/runs`
- `GET /workflow/runs`
- `GET /workflow/runs/{run_id}/next`
- `POST /workflow/checkpoints`
- `GET /workflow/runs/{run_id}/checkpoints`

## GPT 규칙
- 여러 단원 작업은 createWorkflowRun 후 단원별 진행
- 각 단계 후 saveWorkflowCheckpoint
- 타임아웃 위험 시 직전 결과 저장 후 paused/timeout_safe_saved
- 계속/이어/다음/ㄱㄱ 입력 시 getNextWorkflowStep으로 이어가기
