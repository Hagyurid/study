# FlashLook Native V5

iPhone용 React Native / Expo 프로젝트. 기존 flashlook 웹앱과 별개입니다.

## 목표
- Safari/WebKit에서 Transformers.js 모델을 상주시켜 편집하던 구조 제거
- 사진 선택
- depth 추론은 사진당 1회
- depth/flash response map만 보존
- 슬라이더 편집은 추론 없이 수행
- EAS cloud build로 Mac 없이 iPhone 설치

## 현재 단계
V5 native foundation: Expo 앱, iOS bundle id, EAS internal distribution 설정, 사진 선택/preview UI까지 구성.

## 설치 빌드
Expo 계정 및 Apple Developer 계정 연결 후:
```
npx eas-cli@latest build --platform ios --profile preview
```
EAS가 iOS cloud build와 서명을 진행합니다.

> 현재 커밋은 기반 앱입니다. Depth/relighting 네이티브 구현은 아직 연결 전이므로 웹 V4 알고리즘을 WebView로 감싸지 않습니다.
