# study 렌더 메모리 패치 적용 파일

이 zip은 **교체용 전체 파일**이 아니라, 현재 저장소 버전에 맞춰 `app/main.py`를 자동 수정하는 적용 패키지입니다.

## 포함 파일
- `apply_render_memory_fix.py` : `app/main.py` 자동 수정 스크립트
- `study_render_memory_patch.patch` : 참고용 패치 파일

## 적용 방법
1. 이 zip을 저장소 루트에 풉니다.
2. 저장소 루트에서 아래 실행:
   - `python apply_render_memory_fix.py`
3. 적용 후 `app/main.py.bak` 백업이 생성됩니다.
4. Render 재배포 또는 커밋 후 배포합니다.

## 수정 내용
- `data:image/png;base64,...` inline 이미지 제거
- `/slides/render.png` endpoint 추가
- 슬라이드 캐시 크기 `24 -> 6`
- zoom / 화질 로직은 유지

## 커스텀 GPT
현재 기준으로는 별도 수정이 필요 없습니다.
`[[SLIDE_IMAGE ...]]` 마커 포맷은 그대로이고, 서버 내부 렌더 방식만 바뀝니다.
