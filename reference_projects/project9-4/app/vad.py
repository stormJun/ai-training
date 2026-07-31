import struct


class SimpleEnergyVAD:
    """
    简单的能量 VAD(纯 Python,无第三方依赖)。
    通过 PCM16 的 RMS 能量判断是否在说话。

    仅用于骨架演示。生产环境换成:
      - Silero VAD(外挂,轻量准确)
      - 或 Qwen3-Omni 自带的 semantic VAD(语义级,和声/噪音不误打断)
    """

    def __init__(self, threshold: int = 500, silence_frames: int = 8):
        """
        :param threshold: RMS 阈值(PCM16 幅值 0~32767),高于视为说话
        :param silence_frames: 连续多少帧静音判定一句话结束
        """
        self.threshold = threshold
        self.silence_frames = silence_frames
        self._in_speech = False
        self._silence_count = 0

    @staticmethod
    def _rms(pcm: bytes) -> int:
        """计算 PCM16 little-endian 音频的 RMS。"""
        if len(pcm) < 2:
            return 0
        n = len(pcm) // 2
        samples = struct.unpack(f"<{n}h", pcm[: n * 2])
        mean_square = sum(s * s for s in samples) / n
        return int(mean_square ** 0.5)

    def is_speech(self, pcm: bytes) -> bool:
        """当前帧是否为说话。"""
        return self._rms(pcm) > self.threshold

    def utterance_end(self, pcm: bytes) -> bool:
        """
        返回 True 表示一句话刚结束(语音 -> 静音 的下降沿)。
        用于 server_vad 自动模式:一句话讲完自动触发生成。
        """
        if self.is_speech(pcm):
            self._in_speech = True
            self._silence_count = 0
            return False
        if self._in_speech:
            self._silence_count += 1
            if self._silence_count >= self.silence_frames:
                self._in_speech = False
                self._silence_count = 0
                return True
        return False
