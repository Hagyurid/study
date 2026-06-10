v23.7 그래프·수치표 실제 코드 패치

이전 v23.7 ZIP은 기획본만 포함되어 있어 app/main.py, static/study/app.js, static/study/index.html, static/study/styles.css가 없었다.
이번 ZIP은 v23.6 기준 실제 코드 패치 파일을 포함한다.

포함 파일
- app/main.py
- static/study/app.js
- static/study/index.html
- static/study/styles.css
- docs/custom_gpt/01_suite_instructions_v23_7_GRAPH_TABLE_PATCH.txt
- PATCH_README_V23_7_GRAPH_TABLE_CODE.txt

기능
1. [[VALUE_TABLE ...]] 마커 렌더링
- Study Note 화면에서 실제 표로 표시
- PDF 출력에서 실제 표로 표시
- Word 출력에서는 docx 표로 변환

2. [[GRAPH_IMAGE ...]] 마커 렌더링
- Study Note 화면에서 SVG 그래프로 표시
- PDF 출력에서 그래프 이미지로 표시
- Word 출력에서는 그래프 제목/식/점 데이터 표로 fallback

3. Studio 수동 삽입 UI
- 오른쪽 툴바에 수치표 버튼 추가
- 오른쪽 툴바에 그래프 버튼 추가

4. Markdown 동기화
- 화면에서 표/그래프 삭제 후 저장 가능
- 그래프 캡션 수정 후 저장 가능
- VALUE_TABLE / GRAPH_IMAGE 마커로 다시 저장

적용 순서
1. v23.6 적용 레포 위에 이 ZIP 덮어쓰기
2. GitHub push
3. Render 재배포
4. Study Note Studio에서 수치표/그래프 삽입 테스트
5. 저장 후 새로고침하여 유지되는지 확인
6. PDF/Word 출력 확인

주의
- 그래프는 points="x,y|x,y" 형식 데이터가 있을 때 가장 안정적이다.
- formula만으로 자동 계산하지 않는다. GPT가 필요한 점 데이터를 같이 생성해야 한다.
- OpenAPI/Actions 수정은 필요 없다.
