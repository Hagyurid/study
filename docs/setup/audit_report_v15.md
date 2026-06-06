# v15 수정 보고서

## 요청 반영
1. Custom GPT에서 “메뉴” 입력 시 사용 가능한 기능 메뉴 출력
2. 메뉴 번호 선택 → 하위 메뉴 출력 → 실행 흐름으로 이어지는 규칙 추가
3. 업로드할 때 ACTION_API_KEY를 매번 입력하지 않도록 브라우저 localStorage 자동 저장 기능 추가
4. 업로드, 외부 정리본 업로드, 파일 관리 화면에 저장된 키 자동 입력 및 삭제 버튼 추가

## 보안 설계
- API 키 인증은 유지
- 키는 서버 DB에 저장하지 않음
- 키는 사용자의 브라우저 localStorage에만 저장
- 저장된 키 지우기 버튼 제공

## 수정 파일
- app/main.py
- docs/custom_gpt/01_suite_instructions.txt
- docs/custom_gpt/11_keyword_command_router.txt
- docs/custom_gpt/16_menu_navigation_contract.txt
- docs/custom_gpt/00_custom_gpt_setup_v6.txt
- README.md
