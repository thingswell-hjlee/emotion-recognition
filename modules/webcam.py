"""
modules/webcam.py - 웹캠 캡처 및 얼굴 감지 모듈
노트북 내장 카메라에서 프레임을 캡처하고 얼굴 영역을 감지합니다.
"""

import cv2
import numpy as np
from typing import List, Optional, Tuple

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import Config, DEFAULT_CONFIG
from utils.data_types import FaceRegion


class WebcamCapture:
    """웹캠 프레임 캡처 및 얼굴 감지"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config
        self.cap: Optional[cv2.VideoCapture] = None
        self._face_cascade: Optional[cv2.CascadeClassifier] = None
        self._is_opened = False

    def open(self) -> bool:
        """카메라를 열고 초기화"""
        try:
            self.cap = cv2.VideoCapture(self.config.camera_device_id)
            if not self.cap.isOpened():
                return False

            self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, self.config.frame_width)
            self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, self.config.frame_height)

            # Haar Cascade 로드
            cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
            self._face_cascade = cv2.CascadeClassifier(cascade_path)
            if self._face_cascade.empty():
                return False

            self._is_opened = True
            return True

        except Exception:
            self._is_opened = False
            return False

    def read_frame(self) -> Tuple[bool, Optional[np.ndarray]]:
        """한 프레임 캡처"""
        if not self._is_opened or self.cap is None:
            return False, None

        ret, frame = self.cap.read()
        if not ret:
            return False, None

        return True, frame

    def detect_faces(self, frame: np.ndarray) -> List[FaceRegion]:
        """프레임에서 얼굴 영역 감지"""
        if self._face_cascade is None:
            return []

        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        gray = cv2.equalizeHist(gray)

        faces = self._face_cascade.detectMultiScale(
            gray,
            scaleFactor=1.3,
            minNeighbors=5,
            minSize=(30, 30),
        )

        regions = []
        for (x, y, w, h) in faces:
            regions.append(FaceRegion(x=int(x), y=int(y), w=int(w), h=int(h)))

        return regions

    def get_largest_face(self, faces: List[FaceRegion]) -> Optional[FaceRegion]:
        """여러 얼굴 중 가장 큰(가까운) 얼굴 반환"""
        if not faces:
            return None
        return max(faces, key=lambda f: f.area)

    def crop_face(self, frame: np.ndarray, region: FaceRegion,
                  padding: float = 0.2) -> Optional[np.ndarray]:
        """얼굴 영역을 크롭 (패딩 포함)"""
        h, w = frame.shape[:2]

        pad_x = int(region.w * padding)
        pad_y = int(region.h * padding)

        x1 = max(0, region.x - pad_x)
        y1 = max(0, region.y - pad_y)
        x2 = min(w, region.x + region.w + pad_x)
        y2 = min(h, region.y + region.h + pad_y)

        face_img = frame[y1:y2, x1:x2]

        if face_img.shape[0] < 10 or face_img.shape[1] < 10:
            return None

        return face_img

    def release(self):
        """카메라 리소스 해제"""
        if self.cap is not None:
            self.cap.release()
        self._is_opened = False

    @property
    def is_opened(self) -> bool:
        return self._is_opened

    def __enter__(self):
        self.open()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.release()
        return False
