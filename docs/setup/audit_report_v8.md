# v8 수정 보고서

## 요청 반영
사용자가 간단한 숫자 또는 단어만 입력해도 GPT가 의도를 자동 해석해 실행하도록 수정했습니다.

## 추가 규칙
- 기본 메뉴 번호 1~9
- 키워드 명령: 매핑, 선택, 정리, 문제, 계산기, 전사본, 수정, 최종, 상태
- 모드+단원 결합 입력: 정리 1-3, 문제 2, 계산기 3,4
- 단원 번호는 강의자료 기준 unitNumber로 해석
- 모호한 경우 짧은 확인 질문 1회

## 수정 파일
- docs/custom_gpt/11_keyword_command_router.txt 추가
- docs/custom_gpt/01_suite_instructions.txt 업데이트
- docs/custom_gpt/00_custom_gpt_setup_v6.txt 업데이트
- docs/custom_gpt/09_workflow_selector_contract.txt 업데이트
- docs/custom_gpt/02_first_prompts.txt 업데이트
