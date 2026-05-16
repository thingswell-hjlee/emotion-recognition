"""
ui/app.py - Streamlit UI
감정 인식 설정, 제어, 결과 표시를 하나의 화면에서 제공합니다.

핵심 설계:
- st.session_state로 모든 상태를 명확히 관리
- 모드 변경 시 기존 분석기를 안전하게 stop → cleanup → 재초기화
- 슬라이더 값만 변경 시 전체 재초기화 없이 hot-update
- 성능 프로파일로 부하 제어

실행: streamlit run ui/app.py
⚠️ 프로젝트 루트(emotion-recognition/)에서 실행하세요.
"""

import sys
import os
import time

# 프로젝트 루트를 Python path에 추가 (import 오류 방지)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

import streamlit as st
from config import (
    Config, EMOTIONS, EMOTION_EMOJI,
    VALID_RUN_MODES, RUN_MODE_MINIMAL, RUN_MODE_FACE, RUN_MODE_VOICE, RUN_MODE_FULL,
)
from performance_profiles import (
    PROFILES, PROFILE_NAMES, get_profile, get_default_profile_for_mode,
    RESOLUTION_OPTIONS,
)
from utils.data_types import AppState


# ============================================================
# SESSION STATE 초기화
# ============================================================

def init_session_state():
    """Streamlit 세션 상태 초기화 (앱 첫 로드 시 1회)"""
    defaults = {
        "controller": None,
        "app_state": AppState(),
        "initialized": False,
        # 핵심 상태 (UI와 controller 동기화 기준)
        "current_mode": RUN_MODE_MINIMAL,
        "is_running": False,
        "performance_profile": "standard",
        "camera_enabled": True,
        "audio_enabled": False,
        "face_analysis_enabled": False,
        "audio_analysis_enabled": False,
        # 슬라이더 상태 (hot-update 대상)
        "cycle_seconds": 10,
        "tts_volume": 70,
        "tts_enabled": False,
        "camera_device_id": 0,
        "resolution_key": "480x360 (Medium)",
    }
    for key, value in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = value


# ============================================================
# CONTROLLER 관리
# ============================================================

def get_controller():
    """Controller 인스턴스 가져오기 (없으면 생성)"""
    if st.session_state.controller is None:
        try:
            from controller import EmotionController
            config = _build_config_from_state()
            controller = EmotionController(config=config)
            st.session_state.controller = controller
        except Exception as e:
            st.error(f"⚠️ 컨트롤러 생성 실패: {e}")
            return None
    return st.session_state.controller


def _build_config_from_state() -> Config:
    """현재 session_state에서 Config 객체 생성"""
    config = Config()
    config.run_mode = st.session_state.current_mode
    config.performance_profile = st.session_state.performance_profile
    config.camera_enabled = st.session_state.camera_enabled
    config.audio_enabled = st.session_state.audio_enabled
    config.face_analysis_enabled = st.session_state.face_analysis_enabled
    config.audio_analysis_enabled = st.session_state.audio_analysis_enabled
    config.cycle_seconds = st.session_state.cycle_seconds
    config.tts_volume = st.session_state.tts_volume
    config.tts_enabled = st.session_state.tts_enabled
    config.camera_device_id = st.session_state.camera_device_id

    # 해상도 적용
    res = RESOLUTION_OPTIONS.get(st.session_state.resolution_key, (480, 360))
    config.frame_width, config.frame_height = res

    # 프로파일 값 적용
    config.apply_profile(st.session_state.performance_profile)

    # 모드 기본값 적용 (debug가 아닌 경우)
    if st.session_state.performance_profile != "debug":
        config.apply_mode_defaults(st.session_state.current_mode)

    return config


def safe_mode_switch(new_mode: str):
    """
    안전한 모드 전환:
    1. 기존 분석 stop
    2. camera release, microphone close
    3. sleep(0.5) - 리소스 해제 대기
    4. controller를 None으로 리셋
    5. 새 모드로 session_state 업데이트
    """
    controller = st.session_state.controller

    # 1. 기존 분석 중단 및 리소스 해제
    if controller is not None:
        try:
            controller.cleanup()
        except Exception:
            pass
        time.sleep(0.5)  # 리소스 해제 대기
        st.session_state.controller = None

    # 2. 상태 업데이트
    st.session_state.current_mode = new_mode
    st.session_state.is_running = False
    st.session_state.initialized = False
    st.session_state.app_state = AppState()

    # 3. 모드별 기본 토글 설정 (debug가 아닌 경우)
    if st.session_state.performance_profile != "debug":
        if new_mode == RUN_MODE_MINIMAL:
            st.session_state.camera_enabled = True
            st.session_state.audio_enabled = False
            st.session_state.face_analysis_enabled = False
            st.session_state.audio_analysis_enabled = False
        elif new_mode == RUN_MODE_FACE:
            st.session_state.camera_enabled = True
            st.session_state.audio_enabled = False
            st.session_state.face_analysis_enabled = True
            st.session_state.audio_analysis_enabled = False
        elif new_mode == RUN_MODE_VOICE:
            st.session_state.camera_enabled = False
            st.session_state.audio_enabled = True
            st.session_state.face_analysis_enabled = False
            st.session_state.audio_analysis_enabled = True
        elif new_mode == RUN_MODE_FULL:
            st.session_state.camera_enabled = True
            st.session_state.audio_enabled = True
            st.session_state.face_analysis_enabled = True
            st.session_state.audio_analysis_enabled = True


def safe_profile_switch(new_profile: str):
    """성능 프로파일 전환 (실행 중이면 stop 후 재시작)"""
    st.session_state.performance_profile = new_profile
    profile = get_profile(new_profile)

    # 프로파일 값을 session_state에 반영
    res_key = next(
        (k for k, v in RESOLUTION_OPTIONS.items() if v == profile.resolution),
        "480x360 (Medium)"
    )
    st.session_state.resolution_key = res_key
    st.session_state.cycle_seconds = profile.analysis_interval

    if new_profile != "debug":
        st.session_state.face_analysis_enabled = profile.face_analysis_enabled
        st.session_state.audio_analysis_enabled = profile.audio_analysis_enabled

    # controller 재생성 필요
    controller = st.session_state.controller
    if controller is not None:
        was_running = st.session_state.is_running
        try:
            controller.stop()
            controller.cleanup()
        except Exception:
            pass
        st.session_state.controller = None
        st.session_state.initialized = False
        if was_running:
            st.session_state.is_running = False  # UI에서 다시 시작 클릭 필요


def hot_update_slider(controller, key: str, value):
    """슬라이더 값 변경 시 전체 재초기화 없이 controller에 반영"""
    if controller is None:
        return

    try:
        if key == "cycle_seconds":
            controller.update_cycle(value)
        elif key == "tts_volume":
            controller.update_volume(value)
        elif key == "tts_enabled":
            controller.update_voice_feedback(value)
        elif key == "camera_device_id":
            controller.update_camera_index(value)
    except Exception:
        pass


# ============================================================
# MAIN UI
# ============================================================

def sync_state_from_controller():
    """
    핵심 수정: controller.state → st.session_state.app_state 동기화.
    Streamlit rerun 시마다 호출하여 최신 분석 결과를 UI에 반영합니다.
    """
    controller = st.session_state.get("controller")
    if controller is not None and hasattr(controller, 'state'):
        st.session_state.app_state = controller.state
        st.session_state.is_running = controller.state.is_running


def main():
    st.set_page_config(
        page_title="Emotion Monitor",
        page_icon="🧠",
        layout="wide",
    )

    init_session_state()

    # ★ 핵심: 매 rerun마다 controller 상태를 UI로 동기화
    sync_state_from_controller()

    state: AppState = st.session_state.app_state

    # === 헤더 ===
    st.title("🧠 Multimodal Emotion State Monitor")

    # === 상단 상태 바 ===
    render_status_bar(state)

    # === 사이드바 ===
    render_sidebar()

    st.divider()

    # === 제어 패널 ===
    render_controls(state)

    st.divider()

    # === 결과 표시 ===
    render_results(state)

    # === 입력 상태 (마이크) ===
    if st.session_state.current_mode in (RUN_MODE_VOICE, RUN_MODE_FULL, "minimal"):
        render_mic_status(state)

    # === 음성 분석 상세 ===
    if st.session_state.current_mode in (RUN_MODE_VOICE, RUN_MODE_FULL):
        render_voice_pipeline(state)

    # === 감정 차트 ===
    render_chart(state)

    # === 로그 ===
    render_logs(state)

    # === 안내문 ===
    st.divider()
    st.warning(
        "⚠️ 감정 분석 결과는 **참고용**이며, 의학적·심리학적 진단이 아닙니다. "
        "모든 영상/음성은 로컬에서만 처리되며 저장·전송되지 않습니다."
    )

    # === 자동 새로고침 ===
    if st.session_state.is_running:
        time.sleep(2)
        st.rerun()


# ============================================================
# 상단 상태 바
# ============================================================

def render_status_bar(state: AppState):
    """현재 실행 상태, 부하 수준, 활성화된 분석 모듈 표시"""
    cols = st.columns(5)

    with cols[0]:
        mode = st.session_state.current_mode
        mode_emoji = {"minimal": "🟢", "face": "📷", "voice": "🎤", "full": "🔄"}.get(mode, "")
        st.caption(f"모드: {mode_emoji} {mode}")

    with cols[1]:
        profile = st.session_state.performance_profile
        profile_emoji = {"low_power": "🔋", "standard": "⚡", "high_accuracy": "🎯", "debug": "🔧"}.get(profile, "")
        st.caption(f"프로파일: {profile_emoji} {profile}")

    with cols[2]:
        running = "🟢 실행 중" if st.session_state.is_running else "⚪ 대기"
        st.caption(f"상태: {running}")

    with cols[3]:
        modules = []
        if st.session_state.camera_enabled:
            modules.append("📷")
        if st.session_state.face_analysis_enabled:
            modules.append("🧠")
        if st.session_state.audio_enabled:
            modules.append("🎤")
        if st.session_state.audio_analysis_enabled:
            modules.append("🔊")
        st.caption(f"활성 모듈: {' '.join(modules) or '없음'}")

    with cols[4]:
        res = st.session_state.resolution_key.split(" ")[0]
        interval = st.session_state.cycle_seconds
        st.caption(f"해상도: {res} | 주기: {interval}s")


# ============================================================
# 사이드바
# ============================================================

def render_sidebar():
    """사이드바: Mode, Profile, Camera, Audio, Interval, Resolution"""
    with st.sidebar:
        st.header("⚙️ 설정")

        # --- 실행 모드 ---
        mode_labels = {
            RUN_MODE_MINIMAL: "🟢 Minimal (안정)",
            RUN_MODE_FACE: "📷 Face (표정 분석)",
            RUN_MODE_VOICE: "🎤 Voice (음성 분석)",
            RUN_MODE_FULL: "🔄 Full (전체)",
        }
        current_mode = st.session_state.current_mode
        new_mode = st.selectbox(
            "실행 모드",
            options=VALID_RUN_MODES,
            format_func=lambda x: mode_labels.get(x, x),
            index=VALID_RUN_MODES.index(current_mode),
            key="sb_mode",
        )
        if new_mode != current_mode:
            safe_mode_switch(new_mode)
            st.rerun()

        st.divider()

        # --- 성능 프로파일 ---
        current_profile = st.session_state.performance_profile
        new_profile = st.selectbox(
            "성능 프로파일",
            options=PROFILE_NAMES,
            format_func=lambda x: get_profile(x).description,
            index=PROFILE_NAMES.index(current_profile),
            key="sb_profile",
        )
        if new_profile != current_profile:
            safe_profile_switch(new_profile)
            st.rerun()

        st.divider()

        # --- 해상도 ---
        res_options = list(RESOLUTION_OPTIONS.keys())
        current_res = st.session_state.resolution_key
        new_res = st.selectbox(
            "카메라 해상도",
            options=res_options,
            index=res_options.index(current_res) if current_res in res_options else 1,
            key="sb_resolution",
        )
        if new_res != current_res:
            st.session_state.resolution_key = new_res
            # 해상도 변경은 재초기화 필요
            if st.session_state.controller is not None:
                safe_profile_switch(st.session_state.performance_profile)
                st.rerun()

        # --- 분석 주기 ---
        new_cycle = st.slider(
            "분석 주기 (초)", 3, 15,
            value=st.session_state.cycle_seconds,
            key="sb_cycle",
        )
        if new_cycle != st.session_state.cycle_seconds:
            st.session_state.cycle_seconds = new_cycle
            hot_update_slider(st.session_state.controller, "cycle_seconds", new_cycle)

        # --- 카메라 인덱스 ---
        new_cam = st.selectbox(
            "카메라 인덱스",
            options=[0, 1, 2],
            index=st.session_state.camera_device_id,
            key="sb_cam_idx",
        )
        if new_cam != st.session_state.camera_device_id:
            st.session_state.camera_device_id = new_cam
            hot_update_slider(st.session_state.controller, "camera_device_id", new_cam)

        st.divider()

        # --- Debug 모드: 개별 토글 ---
        if st.session_state.performance_profile == "debug":
            st.subheader("🔧 Debug 토글")
            st.session_state.camera_enabled = st.toggle(
                "카메라", value=st.session_state.camera_enabled, key="sb_cam_on"
            )
            st.session_state.face_analysis_enabled = st.toggle(
                "표정 분석 (DeepFace)", value=st.session_state.face_analysis_enabled, key="sb_face_on"
            )
            st.session_state.audio_enabled = st.toggle(
                "마이크", value=st.session_state.audio_enabled, key="sb_audio_on"
            )
            st.session_state.audio_analysis_enabled = st.toggle(
                "음성 분석 (librosa)", value=st.session_state.audio_analysis_enabled, key="sb_voice_on"
            )
            st.divider()

        # --- TTS ---
        new_tts = st.toggle(
            "음성 안내", value=st.session_state.tts_enabled, key="sb_tts",
            help="pyttsx3 필요. 기본 OFF."
        )
        if new_tts != st.session_state.tts_enabled:
            st.session_state.tts_enabled = new_tts
            hot_update_slider(st.session_state.controller, "tts_enabled", new_tts)

        new_vol = st.slider(
            "음성 볼륨 (%)", 0, 100,
            value=st.session_state.tts_volume,
            key="sb_vol",
        )
        if new_vol != st.session_state.tts_volume:
            st.session_state.tts_volume = new_vol
            hot_update_slider(st.session_state.controller, "tts_volume", new_vol)

        st.divider()
        st.caption("v0.2.0 | Python 3.11 권장")


# ============================================================
# 제어 패널
# ============================================================

def render_controls(state: AppState):
    col_start, col_stop, col_status = st.columns([1, 1, 3])

    with col_start:
        if st.button("▶ 시작", type="primary",
                     disabled=st.session_state.is_running,
                     use_container_width=True):
            controller = get_controller()
            if controller is not None:
                if not st.session_state.initialized:
                    controller.initialize()
                    st.session_state.initialized = True
                controller.start()
                st.session_state.is_running = True
                st.rerun()

    with col_stop:
        if st.button("■ 정지",
                     disabled=not st.session_state.is_running,
                     use_container_width=True):
            controller = st.session_state.controller
            if controller is not None:
                controller.stop()
            st.session_state.is_running = False
            st.rerun()

    with col_status:
        cam_icon = "🟢" if state.camera_active else "⚪"
        mic_icon = "🟢" if state.microphone_active else "⚪"

        # full mode에서 audio dependency 없으면 경고
        audio_warn = ""
        if st.session_state.current_mode in (RUN_MODE_VOICE, RUN_MODE_FULL):
            if st.session_state.audio_analysis_enabled and state.voice_status in ("sounddevice 미설치", "librosa 미설치"):
                audio_warn = " ⚠️ 음성 패키지 미설치"

        st.markdown(
            f"📷 {cam_icon} {state.face_status} &nbsp;|&nbsp; "
            f"🎤 {mic_icon} {state.voice_status}{audio_warn}"
        )


# ============================================================
# 결과 표시
# ============================================================

def render_results(state: AppState):
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("현재 감정")
        if state.current_emotion:
            emoji = EMOTION_EMOJI.get(state.current_emotion.dominant, "❓")
            conf = state.current_emotion.confidence
            conf_label = f"{conf:.0%}"

            # low confidence도 표시 (숨기지 않음)
            if conf < 0.6:
                conf_label += " ⚠️ low confidence"

            st.metric(
                label="분석 결과",
                value=f"{emoji} {state.current_emotion.dominant}",
                delta=conf_label,
            )
            src = state.current_emotion.source
            if "dummy" in src:
                st.caption("⚡ 더미 모드")
            elif src == "face":
                st.caption("📷 DeepFace")
            elif src == "smoothed":
                st.caption("📊 이동평균 적용")
        else:
            # 결과 없을 때 이유 표시
            face_status = state.face_status
            if face_status == "NO_FRAME":
                st.warning("📷 카메라 프레임을 읽을 수 없습니다")
            elif face_status == "NO_FACE":
                st.info("👤 얼굴이 감지되지 않습니다. 카메라를 정면으로 향하세요.")
            elif face_status == "DEEPFACE_ERROR":
                st.warning("🧠 표정 분석 실패. DeepFace 모델 문제일 수 있습니다.")
            elif "오류" in face_status:
                st.error(f"❌ {face_status}")
            else:
                st.info(f"분석 대기 중... (상태: {face_status})")

        st.subheader("LSTM 예측")
        if state.predicted_emotion:
            emoji = EMOTION_EMOJI.get(state.predicted_emotion.dominant, "❓")
            st.metric(
                label="예측 결과",
                value=f"{emoji} {state.predicted_emotion.dominant}",
                delta=f"신뢰도: {state.predicted_emotion.confidence:.0%}",
            )
        else:
            st.info(f"📊 {state.lstm_status}")

    with col_b:
        st.subheader("최근 평균 감정")
        if state.average_emotion:
            emoji = EMOTION_EMOJI.get(state.average_emotion.dominant, "❓")
            st.metric(
                label=f"평균 (주기: {st.session_state.cycle_seconds}초)",
                value=f"{emoji} {state.average_emotion.dominant}",
                delta=f"신뢰도: {state.average_emotion.confidence:.0%}",
            )
        else:
            st.info("데이터 수집 중...")

        st.subheader("변화 방향")
        if state.comparison_label:
            st.metric(
                label="평균 vs 예측",
                value=state.comparison_label,
                delta=f"변화폭: {state.comparison_magnitude:.2f}",
            )
        else:
            st.info("비교 대기 중...")


# ============================================================
# 감정 차트
# ============================================================

def render_chart(state: AppState):
    st.divider()
    st.subheader("📊 감정 점수 분포")

    if state.current_emotion:
        try:
            import pandas as pd
            scores = state.current_emotion.scores
            chart_data = pd.DataFrame({
                "감정": [f"{EMOTION_EMOJI.get(e, '')} {e}" for e in EMOTIONS],
                "점수": [scores.get(e, 0.0) for e in EMOTIONS],
            }).sort_values("점수", ascending=False)
            st.bar_chart(chart_data.set_index("감정"), height=200)
        except Exception:
            st.caption("차트 표시 오류")
    else:
        st.caption("분석이 시작되면 차트가 표시됩니다.")


# ============================================================
# 마이크 입력 상태
# ============================================================

def render_mic_status(state: AppState):
    """마이크 입력 레벨, 무음 여부, 장치 정보 표시"""
    st.divider()
    st.subheader("🎤 마이크 입력 상태")

    controller = st.session_state.controller
    if controller is None or not hasattr(controller, '_microphone') or controller._microphone is None:
        st.info("마이크가 초기화되지 않았습니다.")
        return

    mic = controller._microphone

    # 장치 정보
    device = mic.get_device_info()
    if device:
        col1, col2, col3 = st.columns(3)
        with col1:
            st.caption(f"장치: {device.name}")
        with col2:
            st.caption(f"SR: {int(device.sample_rate)}Hz | CH: {device.channels}")
        with col3:
            st.caption(f"ID: {device.device_id} {'(기본)' if device.is_default else ''}")

    # 실시간 메트릭
    metrics = mic.get_metrics()
    col1, col2, col3, col4 = st.columns(4)

    with col1:
        rms_pct = min(100, int(metrics.rms * 1000))
        st.metric("RMS", f"{metrics.rms:.4f}", delta=f"{rms_pct}%")

    with col2:
        st.metric("Peak", f"{metrics.peak:.3f}")

    with col3:
        st.metric("dBFS", f"{metrics.dbfs:.1f}")

    with col4:
        silence_badge = "🔇 무음" if metrics.is_silence else "🔊 소리 감지"
        st.metric("상태", silence_badge)

    # RMS 레벨 바 (간단한 시각화)
    threshold = controller.config.silence_threshold
    level = min(1.0, metrics.rms / max(threshold * 3, 0.001))
    st.progress(level, text=f"입력 레벨 (threshold: {threshold})")


# ============================================================
# 음성 분석 파이프라인 상태
# ============================================================

def render_voice_pipeline(state: AppState):
    """음성 파이프라인 단계별 진행 상태 + 특징 요약"""
    st.divider()
    st.subheader("🔊 음성 분석 상세")

    pipeline_state = getattr(state, 'voice_pipeline_state', None)

    # 분류기 모드 표시
    controller = st.session_state.controller
    if controller and hasattr(controller, '_voice_pipeline') and controller._voice_pipeline:
        mode = controller._voice_pipeline.classifier_mode
        st.caption(f"음성 모델: **{mode}**")
    else:
        st.caption("음성 모델: 비활성화")

    if pipeline_state is None:
        st.info("파이프라인 대기 중... (다음 주기 완료 시 업데이트)")
        return

    # 파이프라인 단계 표시
    stages = getattr(pipeline_state, 'stages', [])
    if stages:
        cols = st.columns(len(stages))
        status_icons = {
            "대기": "⬜", "진행 중": "🔄", "완료": "✅",
            "건너뜀": "⏭️", "오류": "❌"
        }
        for i, (col, stage) in enumerate(zip(cols, stages)):
            with col:
                icon = status_icons.get(stage.status, "⬜")
                st.caption(f"{icon}\n{stage.name}")

    # VAD 결과
    vad = getattr(pipeline_state, 'vad_result', None)
    if vad:
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.caption(f"발화 비율: {vad.voice_ratio:.0%}")
        with col2:
            st.caption(f"유효 시간: {vad.valid_seconds:.1f}s")
        with col3:
            st.caption(f"전체 시간: {vad.total_seconds:.1f}s")
        with col4:
            st.caption(f"판정: {vad.status}")

    # 특징 요약
    features = getattr(pipeline_state, 'features', None)
    if features and features.is_valid:
        st.caption("**특징 요약:**")
        summary = features.to_ui_summary()
        cols = st.columns(len(summary))
        for col, (key, val) in zip(cols, summary.items()):
            with col:
                st.caption(f"{key}: **{val}**")

    # 감정 결과
    emotion_result = getattr(pipeline_state, 'emotion_result', None)
    if emotion_result and emotion_result.emotion:
        e = emotion_result.emotion
        emoji = EMOTION_EMOJI.get(e.dominant, "❓")
        st.caption(
            f"결과: {emoji} **{e.dominant}** ({e.confidence:.0%}) | "
            f"신뢰도 등급: {emotion_result.confidence_tier} | "
            f"근거: {emotion_result.reason}"
        )


# ============================================================
# 로그
# ============================================================

def render_logs(state: AppState):
    st.divider()
    st.subheader("📋 로그")
    if state.log_messages:
        log_text = "\n".join(reversed(state.log_messages[-20:]))
        st.text_area("최근 로그", value=log_text, height=160, disabled=True)
    else:
        st.caption("로그가 여기에 표시됩니다.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()
