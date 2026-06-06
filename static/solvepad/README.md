# SolvePad MultiFile Local v5.4

아이패드 Safari/GitHub Pages용 문제풀이 웹앱입니다.

## 파일 구조

```text
index.html   # 화면 구조
styles.css   # 디자인/레이아웃/모눈종이 배경
app.js       # 앱 로직, IndexedDB, 캔버스 필기, 문제팩 관리
.nojekyll    # GitHub Pages 정적 파일 처리 안정화
```

## 데이터 저장 위치

문제팩, 필기, 오답, 북마크, 업로드 이미지는 GitHub가 아니라 브라우저의 IndexedDB에 저장됩니다.

## 업로드

GitHub 저장소 루트에 파일들을 업로드한 뒤 Pages를 main/root로 설정하세요.
