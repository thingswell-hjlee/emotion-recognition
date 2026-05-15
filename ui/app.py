"""
ui/app.py - Streamlit UI
감정 인식 설정, 제어, 결과 표시를 하나의 화면에서 제공합니다.

실행: streamlit run ui/app.py
"""

import sys
import os
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import streamlit as st
from config import Config, EMOTIONS, EMOTION_EMOJI
from utils.data_types import AppState
from controller import EmotionController


def init_session_state():
    """Streamlit 세션 상태 초기화"""
    if "controller" not in st.session_state:
        st.session_state.controller = None
    if "app_state" not in st.session_state:
        st.session_state.app_state = AppState()
    if "initialized" not in st.session_state:
        st.session_state.initialized = False


def get_controller() -> EmotionController:
    """Controller 인스턴스 가져오기 (없으면 생성)"""
    if st.session_state.controller is None:
        config = Config()
        controller = EmotionController(
            config=config,
            on_state_update=lambda s: setattr(st.session_state, 'app_state', s),
        )
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
    controller = get_controller()
    state = st.session_state.app_state

    # === 헤더 ===
    st.title("🧠 Multimodal Emotion State Monitor")

    # === 사이드바: 설정 ===
    with st.sidebar:
        st.header("⚙️ 설정")

        # 감정 인식 주기
        cycle = st.slider(
            "감정 인식 주기 (초)",
            min_value=5, max_value=20, value=state.cycle_seconds,
            help="분석 및 평균 계산 주기"
        )
        if cycle != state.cycle_seconds:
            controller.update_cycle(cycle)

        # 볼륨
        volume = st.slider(
            "음성 출력 볼륨 (%)",
            min_value=0, max_value=100, value=state.volume,
        )
        if volume != state.volume:
            controller.update_volume(volume)

        # 분석 종류
        mode_options = {
            "표정+음성 통합": "integrated",
            "표정만": "face_only",
            "음성만": "voice_only",
        }
        mode_labels = list(mode_options.keys())
        current_label = [k for k, v in mode_options.items()
                         if v == state.analysis_mode][0]
        selected_label = st.selectbox(
            "분석 종류", mode_labels,
            index=mode_labels.index(current_label),
        )
        selected_mode = mode_options[selected_label]
        if selected_mode != state.analysis_mode:
            controller.update_mode(selected_mode)

        # 음성 안내 토글
        voice_on = st.toggle("음성 안내", value=state.voice_feedback_enabled)
        if voice_on != state.voice_feedback_enabled:
            controller.update_voice_feedback(voice_on)

        st.divider()
        st.caption("v0.1.0 MVP")

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
                label=f"평균 (주기: {state.cycle_seconds}초)",
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
        scores = state.current_emotion.scores
        import pandas as pd
        chart_data = pd.DataFrame({
            "감정": [f"{EMOTION_EMOJI.get(e, '')} {e}" for e in EMOTIONS],
            "점수": [scores.get(e, 0.0) for e in EMOTIONS],
        }).sort_values("점수", ascending=False)
        st.bar_chart(chart_data.set_index("감정"), height=250)
    else:
        st.caption("분석이 시작되면 차트가 표시됩니다.")

    # === 로그 ===
    st.divider()
    st.subheader("📋 로그")
    if state.log_messages:
        log_text = "\n".join(reversed(state.log_messages[-20:]))
        st.text_area("최근 로그", value=log_text, height=200, disabled=True)
    else:
        st.caption("로그가 여기에 표시됩니다.")

    # === 안내문 ===
    st.divider()
    st.warning(
        "⚠️ 감정 분석 결과는 **참고용**이며, "
        "의학적·심리학적 진단이 아닙니다."
    )

    # === 자동 새로고침 (실행 중일 때) ===
    if state.is_running:
        time.sleep(2)
        st.rerun()


if __name__ == "__main__":
    main()
