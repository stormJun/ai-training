# 事件类型常量(对齐 Qwen Realtime 协议,便于统一引用)
class EventType:
    # 客户端 -> 服务端
    SESSION_UPDATE = "session.update"
    INPUT_AUDIO_APPEND = "input_audio_buffer.append"
    INPUT_AUDIO_COMMIT = "input_audio_buffer.commit"

    # 服务端 -> 客户端
    SESSION_UPDATED = "session.updated"
    RESPONSE_CREATE = "response.create"
    RESPONSE_AUDIO_DELTA = "response.audio.delta"
    RESPONSE_TRANSCRIPT_DELTA = "response.audio_transcript.delta"
    RESPONSE_DONE = "response.done"
    RESPONSE_CANCELLED = "response.cancelled"
    SPEECH_STARTED = "input_audio_buffer.speech_started"
    ERROR = "error"
