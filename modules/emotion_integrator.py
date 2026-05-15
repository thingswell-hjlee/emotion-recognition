"""
modules/emotion_integrator.py - 멀티모달 감정 통합 모듈
표정 분석 결과와 음성 분석 결과를 가중 평균으로 통합합니다.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from typing import Optional
from config import EMOTIONS, Config, DEFAULT_CONFIG
from utils.data_types import EmotionScores


class EmotionIntegrator:
    """표정 + 음성 감정 결과 가중 통합"""

    def __init__(self, config: Config = DEFAULT_CONFIG):
        self.config = config

    def integrate(self,
                  face_scores: Optional[EmotionScores],
                  voice_scores: Optional[EmotionScores],
                  mode: Optional[str] = None) -> Optional[EmotionScores]:
        """
        표정과 음성 분석 결과를 통합합니다.

        Args:
            face_scores: 표정 분석 결과
            voice_scores: 음성 분석 결과
            mode: 분석 모드 (None이면 config 값 사용)

        Returns:
            통합 EmotionScores 또는 None
        """
        analysis_mode = mode or self.config.analysis_mode

        if analysis_mode == "face_only":
            return self._with_source(face_scores, "integrated")

        elif analysis_mode == "voice_only":
            return self._with_source(voice_scores, "integrated")

        elif analysis_mode == "integrated":
            return self._weighted_merge(face_scores, voice_scores)

        return None

    def _weighted_merge(self,
                        face: Optional[EmotionScores],
                        voice: Optional[EmotionScores]) -> Optional[EmotionScores]:
        """가중 평균으로 통합"""
        # 둘 다 없으면
        if face is None and voice is None:
            return None

        # 하나만 있으면 해당 결과만 사용
        if face is None:
            return self._with_source(voice, "integrated")
        if voice is None:
            return self._with_source(face, "integrated")

        # 가중 평균 계산
        fw = self.config.face_weight
        vw = self.config.voice_weight

        merged_scores = {}
        for emotion in EMOTIONS:
            f_score = face.scores.get(emotion, 0.0)
            v_score = voice.scores.get(emotion, 0.0)
            merged_scores[emotion] = f_score * fw + v_score * vw

        # 정규화
        total = sum(merged_scores.values())
        if total > 0:
            merged_scores = {k: v / total for k, v in merged_scores.items()}

        dominant = max(merged_scores, key=merged_scores.get)

        return EmotionScores(
            scores=merged_scores,
            dominant=dominant,
            confidence=merged_scores[dominant],
            source="integrated",
        )

    def _with_source(self, scores: Optional[EmotionScores],
                     source: str) -> Optional[EmotionScores]:
        """소스 레이블을 변경한 복사본 생성"""
        if scores is None:
            return None
        return EmotionScores(
            scores=scores.scores.copy(),
            dominant=scores.dominant,
            confidence=scores.confidence,
            source=source,
            timestamp=scores.timestamp,
        )
