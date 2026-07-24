# OAK-D Lite VTuber Tracking Engine

OAK-D Lite 카메라로 Pose/Hand 랜드마크를 추출해서 VRM 아바타에 실시간으로 반영하는 프로젝트입니다.
현재 단계는 **파이프라인/렌더링 뼈대 구축** 단계이며, 실제 pose 추출 로직은 아직 더미(테스트용 사인파)로

## 현재 상태

- ✅ OAK-D Lite 카메라 파이프라인 (DepthAI) 구축
- ✅ PySide6 + Three.js/VRM 렌더러를 한 프로세스에 통합한 자체 렌더링 파이프라인 (`app.py` + `index.html`)
- ⬜ 실제 Pose/Hand 랜드마크 추출 (BlazePose/MediaPipe 등 NN 노드) — 미구현, 더미 데이터로 대체 중
- ⬜ 카메라 좌표계 → VRM 좌표계 변환
- ⬜ Roll 축을 포함한 본 회전 계산 (Kalidokit 방식 등 검토 필요)

> 외부 VMC 수신 프로그램(VSeeFace 등)은 사용하지 않고, `app.py`가 자체적으로 Three.js/VRM 렌더러를 띄워 아바타를 표시하는 구조

## 구성 파일

| 파일 | 설명 |
|---|---|
| `app.py` | OAK-D 트래킹 스레드 + PySide6 GUI + WebEngine 기반 Three.js 렌더러를 한 프로세스로 통합한 메인 실행 파일. |
| `index.html` | `app.py`가 띄우는 `QWebEngineView`에서 로드되는 3D 렌더러. Three.js + `@pixiv/three-vrm`으로 VRM 모델을 표시하고, Python에서 넘어온 본 회전값을 실시간 반영. |
| `avatar.vrm` | (직접 준비) `index.html`과 같은 폴더에 위치해야 하는 VRM 아바타 모델 파일. 저장소에는 포함되어 있지 않음. |

## 아키텍처 개요

```
[OAK-D Lite 카메라]
        │  (RGB / Depth 스트림)
        ▼
[DepthAI Pipeline] ── (예정: Pose NN 노드로 랜드마크 추출)
        │
        ▼
[본 회전 계산 (Quaternion)]
        │
        ▼
[TrackingThread] ──▶ Qt Signal ──▶ QWebEngineView.runJavaScript()
                                              │
                                              ▼
                                index.html (Three.js + VRM 렌더링)
```

카메라 트래킹부터 렌더링까지 전부 한 프로세스(`app.py`) 안에서 처리되며, 외부 프로그램으로 데이터를 내보내지 않음.

## 요구 사항

```
pip install depthai opencv-python PySide6 PySide6-WebEngine
```

- Node.js/npm 불필요 (Three.js, three-vrm은 CDN(unpkg)에서 importmap으로 로드)
- Python 3.9+ 권장

## 실행 방법

1. `avatar.vrm` 파일을 `app.py`, `index.html`과 같은 폴더에 준비
2. 실행

```bash
python app.py
```

## 알려진 이슈 / 주의사항

- **더미 트래킹 데이터**: 현재 두 스크립트 모두 실제 카메라 랜드마크 대신 하드코딩/사인파 값으로 회전을 계산합니다. 실 사용을 위해서는 Pose 추출 NN 노드 연동이 필요
- **좌표계 불일치**: OAK-D(OpenCV 계열, 오른손 좌표계)와 Unity/VMC(왼손 좌표계, Y-up) 간 좌표 변환이 아직 적용되어 있지 않습니다. 실제 랜드마크를 연결하면 상하/좌우가 반전될 수 있는 문제
- **Roll 축 누락**: 방향벡터 기반 회전 계산은 pitch/yaw만 반영하고 roll은 계산하지 않음
- **VRM 본 접근 방식**: `index.html`은 `getRawBoneNode` 대신 `getNormalizedBoneNode`를 사용. raw bone에 직접 값을 넣으면 `VRMHumanoid.autoUpdateHumanBones`(기본 true)가 매 프레임 normalized→raw 동기화를 하면서 값을 덮어써버리기 때문
- **QtWebEngine + `file://` 로컬 리소스**: Chromium 기반 QtWebEngine은 `file://` 스킴에서 fetch/XHR로 로컬 바이너리(`avatar.vrm` 등)를 읽을 때 CORS로 막힐 수 있어, `app.py`에서 `QTWEBENGINE_CHROMIUM_FLAGS=--allow-file-access-from-files`를 QApplication 생성 전에 설정해둔 상태. 그래도 안 뜨면 로컬 HTTP 서버로 서빙하는 방식으로 전환을 고려
- **트래킹 스레드 종료**: `app.py`는 `q_rgb.tryGet()`(non-blocking)을 사용해 창을 닫을 때 스레드가 멈추지 않도록 처리

## TODO

- [ ] BlazePose/MediaPipe ONNX 모델을 DepthAI NN 노드로 통합
- [ ] `SpatialLocationCalculator` 또는 depth 맵을 이용한 2D→3D 좌표 변환
- [ ] 카메라 좌표계 → VRM 좌표계 변환 함수 작성
- [ ] Kalidokit 등을 참고한 roll 축 포함 본 회전 계산
- [ ] 양팔/전신으로 본 확장
