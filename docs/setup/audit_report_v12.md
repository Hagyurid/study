# v12 UI + multi upload update

## 변경 내용

- `/` 홈 화면을 카드형 대시보드로 개선
- `/upload` 자료 업로드 화면 UI 개선
- `/notes/upload` 외부 정리본 업로드 화면 UI 개선
- 제목 입력을 선택사항으로 변경
- 제목이 비어 있으면 파일명을 자동 제목으로 사용
- 여러 파일을 한 번에 업로드하는 `/sources/upload-batch` 추가
- 업로드 결과를 표로 표시
- `/sources/manage` 파일 관리 화면 UI 개선

## 검수

- FastAPI import/compile 확인
- 기존 API 테스트 통과
- 총 12개 테스트 통과

## 참고

GitHub 커넥터의 쓰기 요청이 안전 검사에서 차단되어, 원격 저장소 직접 업데이트는 완료하지 못했습니다. 이 패키지의 내부 파일을 GitHub에 업로드하면 Render가 자동 배포합니다.
