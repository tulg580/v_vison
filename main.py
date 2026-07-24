import sys
import os
import math

# QtWebEngine이 file:// 스킴에서 로컬 리소스(.vrm 등)를 fetch/XHR로 읽을 수 있도록
# QApplication 생성 "전"에 Chromium 플래그를 설정해야 함.
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--allow-file-access-from-files")

import depthai as dh
from PySide6.QtCore import QUrl, QThread, Signal, Slot
from PySide6.QtWidgets import QApplication, QMainWindow
from PySide6.QtWebEngineWidgets import QWebEngineView

# app.py 자신의 위치를 기준으로 index.html / avatar.vrm 경로를 잡기 위한 베이스 경로
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# ==========================================
# 1. OAK-D 카메라 트래킹 스레드
# ==========================================
class TrackingThread(QThread):
    # (bone_name, qx, qy, qz, qw)
    bone_updated = Signal(str, float, float, float, float)

    def run(self):
        pipeline = dh.Pipeline()

        # OAK-D RGB 카메라 설정
        cam_rgb = pipeline.create(dh.node.ColorCamera)
        cam_rgb.setBoardSocket(dh.CameraBoardSocket.CAM_A)
        cam_rgb.setResolution(dh.ColorCameraProperties.SensorResolution.THE_1080_P)
        cam_rgb.setVideoSize(640, 480)
        cam_rgb.setFps(30)

        xout = pipeline.create(dh.node.XLinkOut)
        xout.setStreamName("rgb")
        cam_rgb.video.link(xout.input)

        with dh.Device(pipeline) as device:
            q_rgb = device.getOutputQueue(name="rgb", maxSize=4, blocking=False)

            t = 0.0
            while not self.isInterruptionRequested():
                # get() 대신 tryGet()을 사용해 non-blocking으로 프레임을 확인.
                # get()은 blocking이라 프레임이 안 들어오면 isInterruptionRequested()를
                # 영영 체크하지 못해 종료 시 스레드가 멈춰버릴 수 있음.
                in_rgb = q_rgb.tryGet()
                if in_rgb is None:
                    self.msleep(1)
                    continue

                # -----------------------------------------------------------
                # 여기서 OAK-D 랜드마크 추출 및 쿼터니언 계산 수행
                # (테스트용으로 팔이 건들거리는 가상 사인파 계산)
                # TODO: 실제 pose 추출(BlazePose/MediaPipe NN 노드) +
                #       카메라 좌표계 -> VRM 좌표계 변환 + roll 축 포함 회전 계산으로 교체
                # -----------------------------------------------------------
                t += 0.05
                angle = math.sin(t) * 0.5

                # 쿼터니언 계산 (Z축 회전 예시)
                qz = math.sin(angle / 2)
                qw = math.cos(angle / 2)

                # WebEngine 렌더러로 뼈대 회전 신호 발송
                # VRM 표준 뼈대 이름: leftUpperArm, rightUpperArm, head 등
                self.bone_updated.emit("leftUpperArm", 0.0, 0.0, qz, qw)

                self.msleep(16)  # ~60FPS 유지


# ==========================================
# 2. 메인 렌더링 GUI 창
# ==========================================
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("OAK-D Standalone VTuber Engine")
        self.resize(1024, 768)

        # WebEngine (Three.js 렌더러) 세팅
        self.web_view = QWebEngineView()

        # index.html은 이 파일(app.py)과 같은 폴더에 있다고 가정
        html_path = os.path.join(BASE_DIR, "index.html")
        self.web_view.setUrl(QUrl.fromLocalFile(html_path))
        self.setCentralWidget(self.web_view)

        # 트래킹 스레드 시작
        self.tracking_thread = TrackingThread()
        self.tracking_thread.bone_updated.connect(self.update_avatar_bone)
        self.tracking_thread.start()

    @Slot(str, float, float, float, float)
    def update_avatar_bone(self, bone_name, qx, qy, qz, qw):
        # Python -> JavaScript 함수 직접 호출
        js_code = f"window.updateBoneRotation('{bone_name}', {qx}, {qy}, {qz}, {qw});"
        self.web_view.page().runJavaScript(js_code)

    def closeEvent(self, event):
        self.tracking_thread.requestInterruption()
        self.tracking_thread.wait()
        event.accept()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
