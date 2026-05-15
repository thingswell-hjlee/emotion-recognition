"""
ui/app.py - Streamlit UI
감정 인식 설정, 제어, 결과 표시를 하나의 화면에서 제공합니다.

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
    VALID_RUN_MODES, RUN_MODE_MINIMAL, RUN_MODE_FACE, RUN_MODE_VOICE, RUN_MODE_FULL
)
from utils.data_types import AppState


def init_session_state():
    """Streamlit 세션 상태 초기화"""
    if "controller" not in st.session_state:
        st.session_state.controller = None
    if "app_state" not in st.session_state:
        st.session_state.app_state = AppState()
    if "initialized" not in st.session_state:
        st.session_state.initialized = False
    if "errors" not in st.session_state:
        st.session_state.errors = []


def get_controller():
    """Controller 인스턴스 가져오기"""
    if st.session_state.controller is None:
        from controller import EmotionController
        config = Config()
        controller = EmotionController(config=config)
        st.session_state.controller = controller
    return st.session_state.controller


def main():
    """메인 UI"""
    st.set_page_config(
        page_title="Emotion Monitor",
        page_icon="🧠",
        layout="wide",
    )

    init_session_state()

    try:
        controller = get_controller()
    except Exception as e:
        st.error(f"⚠️ 컨트롤러 초기화 실패: {e}")
        st.info("requirements-minimal.txt 설치를 확인하세요.")
        return

    state = st.session_state.app_state

    # === 헤더 ===
    st.title("🧠 Multimodal Emotion State Monitor")

    # === 사이드바: 설정 ===
    with st.sidebar:
        st.header("⚙️ 설정")

        # 실행 모드
        mode_labels = {
            RUN_MODE_MINIMAL: "🟢 Minimal (안정 모드)",
            RUN_MODE_FACE: "📷 표정 분석",
            RUN_MODE_VOICE: "🎤 음성 분석",
            RUN_MODE_FULL: "🔄 전체 기능",
        }
        current_mode = controller.config.run_mode
        selected_mode = st.selectbox(
            "실행 모드",
            options=VALID_RUN_MODES,
            format_func=lambda x: mode_labels.get(x, x),
            index=VALID_RUN_MODES.index(current_mode),
            help="minimal: 첫 실행 권장 (의존성 최소)\n"
                 "face: DeepFace 표정 분석\n"
                 "voice: librosa 음성 분석\n"
                 "full: 전체 기능"
        )
        if selected_mode != current_mode:
            controller.update_run_mode(selected_mode)
            st.rerun()

        st.divider()

        # 카메라 인덱스
        camera_idx = st.selectbox(
            "카메라 인덱스",
            options=[0, 1, 2],
            index=controller.config.camera_device_id,
            help="0: 기본 내장 카메라, 1-2: 외부 카메라"
        )
        if camera_idx != controller.config.camera_device_id:
            controller.update_camera_index(camera_idx)

        # 감정 인식 주기
        cycle = st.slider(
            "감정 인식 주기 (초)", 5, 20,
            value=controller.config.cycle_seconds,
        )
        if cycle != controller.config.cycle_seconds:
            controller.update_cycle(cycle)

        # 볼륨
        volume = st.slider(
            "음성 출력 볼륨 (%)", 0, 100,
            value=controller.config.tts_volume,
        )
        if volume != controller.config.tts_volume:
            controller.update_volume(volume)

        # 음성 안내 (기본 OFF)
        voice_on = st.toggle(
            "음성 안내",
            value=controller.config.tts_enabled,
            help="기본 OFF. pyttsx3 설치 필요."
        )
        if voice_on != controller.config.tts_enabled:
            controller.update_voice_feedback(voice_on)

        st.divider()
        st.caption(f"모드: {selected_mode} | Python path OK")

    # === 제어 패널 ===
    col_start, col_stop, col_status = st.columns([1, 1, 2])

    with col_start:
        if st.button("▶ 시작", type="primary", disabled=state.is_running,
                     use_container_width=True):
            if not st.session_state.initialized:
                controller.initialize()
                st.session_state.initialized = True
            controller.start()
            st.rerun()

    with col_stop:
        if st.button("■ 정지", disabled=not state.is_running,
                     use_container_width=True):
            controller.stop()
            st.rerun()

    with col_status:
        cam_icon = "🟢" if state.camera_active else "⚪"
        mic_icon = "🟢" if state.microphone_active else "⚪"
        st.markdown(
            f"📷 카메라: {cam_icon} {state.face_status} &nbsp;&nbsp;&nbsp; "
            f"🎤 마이크: {mic_icon} {state.voice_status}"
        )

    st.divider()

    # === 결과 표시 ===
    col_a, col_b = st.columns(2)

    with col_a:
        st.subheader("현재 감정")
        if state.current_emotion:
            emoji = EMOTION_EMOJI.get(state.current_emotion.dominant, "❓")
            st.metric(
                label="분석 결과",
                value=f"{emoji} {state.current_emotion.dominant}",
                delta=f"신뢰도: {state.current_emotion.confidence:.0%}",
            )
            # 소스 표시
            src = state.current_emotion.source
            if "dummy" in src:
                st.caption("⚡ 더미 모드 (minimal)")
            elif src == "face":
                st.caption("📷 DeepFace 분석")
        else:
            st.info("분석 대기 중...")

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
                label=f"평균 (주기: {controller.config.cycle_seconds}초)",
                value=f"{emoji} {state.average_emotion.dominant}",
                delta=f"신뢰도: {state.average_emotion.confidence:.0%}",
            )
        else:
            st.info("데이터 수집 중...")

        st.subheader("변화 방향")
        if state.comparison_label:
            st.metric(
                label="평균 vs 예측 비교",
                value=state.comparison_label,
                delta=f"변화폭: {state.comparison_magnitude:.2f}",
            )
        else:
            st.info("비교 대기 중...")

    # === 감정 점수 차트 ===
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

    # === 로그 ===
    st.divider()
    st.subheader("📋 로그")
    if state.log_messages:
        log_text = "\n".join(reversed(state.log_messages[-20:]))
        st.text_area("최근 로그", value=log_text, height=180, disabled=True)
    else:
        st.caption("로그가 여기에 표시됩니다.")

    # === 안내문 ===
    st.divider()
    st.warning(
        "⚠️ 감정 분석 결과는 **참고용**이며, "
        "의학적·심리학적 진단이 아닙니다. "
        "모든 영상/음성은 로컬에서만 처리되며 저장·전송되지 않습니다."
    )

    # === 자동 새로고침 ===
    if state.is_running:
        time.sleep(2)
        st.rerun()


if __name__ == "__main__":
    main()
