v23.7 REMOVE GRAPH/IMAGE INSERTION PATCH

목적
- v23.7에서 추가했던 GRAPH_IMAGE / VALUE_TABLE / 그래프·이미지 자동 삽입 흐름을 제거한다.
- 정리본·해설지·문제팩은 텍스트, LaTeX 수식, Markdown 표 중심으로 작성한다.
- 그래프가 필요한 경우 실제 이미지 생성/첨부를 시도하지 말고 글로 개형과 축 해석을 설명한다.
- 그림/슬라이드 삽입은 자동으로 하지 않는다. 사용자가 명시적으로 요청한 경우에만 별도 처리한다.

사이트 코드
- app/main.py
- static/study/app.js
- static/study/index.html
- static/study/styles.css

위 4개 파일은 v23.6 상태로 되돌린다.
따라서 v23.7 GRAPH_IMAGE / VALUE_TABLE 렌더링, Studio 삽입 버튼, PDF/Word 그래프 변환 코드는 제거된다.
v23.6의 Study Studio 저장 안정화, <br> 정리, 슬라이드 기본 100% 관련 기본 패치는 유지된다.

GPT 지침
- 01_suite_instructions_v23_7_NO_GRAPH_IMAGE.txt
- CUSTOM_GPT_STUDY_NOTE_WRITING_GUIDE_V23_7_NO_GRAPH_IMAGE.txt
- CUSTOM_GPT_SOLUTION_WRITING_GUIDE_V23_7_NO_GRAPH_IMAGE.txt
- CUSTOM_GPT_PROBLEM_PACK_WRITING_GUIDE_V23_7_NO_GRAPH_IMAGE.txt

적용
1. 기존 v23.7 코드 패치를 적용했다면 이 ZIP을 덮어쓴다.
2. GitHub push 후 Render 재배포한다.
3. GPT Builder Instructions는 01_suite_instructions_v23_7_NO_GRAPH_IMAGE.txt로 교체한다.
4. 별도 첨부 지침은 NO_GRAPH_IMAGE 버전 3개를 사용한다.

주의
- 기존 문서 안에 이미 남아 있는 [[GRAPH_IMAGE...]], [[VALUE_TABLE...]] 마커는 자동 삭제하지 않는다.
- 기존 저장본까지 정리하려면 별도 마이그레이션 또는 수동 수정이 필요하다.
