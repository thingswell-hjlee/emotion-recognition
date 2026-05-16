"""
performance_profiles.py - 성능 프로파일 정의
각 프로파일은 카메라 해상도, 분석 주기, 분석 모듈 활성화 여부를 제어합니다.

프로파일:
- LOW_POWER: 최소 부하, 일반 노트북 권장
- STANDARD: 균형 잡힌 성능 (기본값)
- HIGH_ACCURACY: 최대 정확도, 고사양 PC 권장
- DEBUG: 개별 모듈 ON/OFF 수동 제어
"""

from dataclasses import dataclass
from typing import Dict, Tuple


@dataclass(frozen=True)
class PerformanceProfile:
    """성능 프로파일 설정값"""
    name: str
    description: str

    # 카메라
    resolution: Tuple[int, int]     # (width, height)
    camera_fps: int

    # 분석 주기
    analysis_interval: int          # 초 (cycle_seconds)
    analysis_skip_frames: int       # N프레임마다 1회 분석

    # 모듈 활성화
    face_analysis_enabled: bool
    audio_analysis_enabled: bool

    # 결과 안정화
    smoothing_window: int           # 이동평균 윈도우 크기 (최근 N회)
    confidence_threshold: float     # 이 미만이면 low confidence 표시

    # CPU 절약
    cpu_saver: bool                 # True면 추가 sleep 삽입


# === 프로파일 정의 ===

PROFILE_LOW_POWER = PerformanceProfile(
    name="low_power",
    description="🔋 Low Power - 일반 노트북 권장, 최소 CPU 부하",
    resolution=(320, 240),
    camera_fps=10,
    analysis_interval=12,
    analysis_skip_frames=10,
    face_analysis_enabled=True,
    audio_analysis_enabled=False,
    smoothing_window=5,
    confidence_threshold=0.5,
    cpu_saver=True,
)

PROFILE_STANDARD = PerformanceProfile(
    name="standard",
    description="⚡ Standard - 균형 잡힌 성능 (기본값)",
    resolution=(480, 360),
    camera_fps=15,
    analysis_interval=10,
    analysis_skip_frames=5,
    face_analysis_enabled=True,
    audio_analysis_enabled=False,
    smoothing_window=4,
    confidence_threshold=0.6,
    cpu_saver=False,
)

PROFILE_HIGH_ACCURACY = PerformanceProfile(
    name="high_accuracy",
    description="🎯 High Accuracy - 최대 정확도, 고사양 PC 권장",
    resolution=(640, 480),
    camera_fps=15,
    analysis_interval=8,
    analysis_skip_frames=3,
    face_analysis_enabled=True,
    audio_analysis_enabled=True,
    smoothing_window=3,
    confidence_threshold=0.6,
    cpu_saver=False,
)

PROFILE_DEBUG = PerformanceProfile(
    name="debug",
    description="🔧 Debug - 모든 옵션 수동 제어",
    resolution=(640, 480),
    camera_fps=15,
    analysis_interval=10,
    analysis_skip_frames=5,
    face_analysis_enabled=True,
    audio_analysis_enabled=True,
    smoothing_window=3,
    confidence_threshold=0.5,
    cpu_saver=False,
)

# === 프로파일 조회 ===

PROFILES: Dict[str, PerformanceProfile] = {
    "low_power": PROFILE_LOW_POWER,
    "standard": PROFILE_STANDARD,
    "high_accuracy": PROFILE_HIGH_ACCURACY,
    "debug": PROFILE_DEBUG,
}

PROFILE_NAMES = list(PROFILES.keys())


def get_profile(name: str) -> PerformanceProfile:
    """이름으로 프로파일 조회 (없으면 standard 반환)"""
    return PROFILES.get(name, PROFILE_STANDARD)


# === 모드별 기본 프로파일 매핑 ===

MODE_DEFAULT_PROFILES: Dict[str, str] = {
    "minimal": "low_power",
    "face": "standard",
    "voice": "standard",
    "full": "standard",
}


def get_default_profile_for_mode(run_mode: str) -> PerformanceProfile:
    """실행 모드에 맞는 기본 프로파일 반환"""
    profile_name = MODE_DEFAULT_PROFILES.get(run_mode, "standard")
    return PROFILES[profile_name]


# === Resolution 옵션 ===

RESOLUTION_OPTIONS = {
    "320x240 (Low)": (320, 240),
    "480x360 (Medium)": (480, 360),
    "640x480 (High)": (640, 480),
}
