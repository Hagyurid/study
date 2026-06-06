# v7 수정 보고서

## 요청 반영
단원 매핑 시 강의자료를 기준축으로 사용하도록 수정했습니다.

## 핵심 변경
- 단원 번호: lecture_slides 기준
- 단원명: lecture_slides 기준
- slide/page range: lectureAnchor로 저장
- 교재/전사본/시험지/정리본: 강의자료 기준 단원에 확장 연결
- 강의자료 기준 단원에 붙지 않는 내용: unmapped 또는 extensionOnly로 분리

## 수정 파일
- docs/custom_gpt/01_suite_instructions.txt
- docs/custom_gpt/08_unit_mapping_contract.txt
- docs/custom_gpt/09_workflow_selector_contract.txt
- docs/custom_gpt/02_first_prompts.txt
- app/db.py: workflow/options에서 unitNumber, lectureAnchor 노출
