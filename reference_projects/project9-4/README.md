# project9-4:自部署实时语音 Agent 骨架

基于开源 Qwen3-Omni + project9 自建 WebSocket 层的**可运行骨架**。配套文档:`../project9-2/自部署指南.md`。

## 定位
把 `自部署指南.md` 里的代码骨架补成能跑的 demo:
- **默认 fake 后端**(`OMNI_BACKEND=fake`)--无需 GPU/模型,即可跑通 WebSocket 层 + 事件协议 + VAD + barge-in 的完整链路。
- **可切换 vLLM 后端**(`OMNI_BACKEND=vllm`)--接真实的 Qwen3-Omni 流式服务(需 GPU + vLLM)。

## 文件结构
```
project9-4/
├── README.md                   # 本文档
├── requirements.txt
├── test_client.py              # 测试客户端(发音频、收事件)⭐
└── app/
    ├── __init__.py
    ├── main.py                 # FastAPI WebSocket 端点 + 后台流式生成 ⭐
    ├── connection_manager.py   # 连接管理器(复用 project9)⭐
    ├── models.py               # 事件类型常量(对齐 Qwen Realtime 协议)
    ├── vad.py                  # 能量 VAD(纯 Python,可换 Silero)⭐
    └── omni_client.py          # 模型客户端:Fake(能跑)+ vLLM(真实)⭐
```

## 快速开始(fake 模式,无需 GPU)
```bash
cd project9-4
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 终端1:起服务
uvicorn app.main:app --reload --port 8000

# 终端2:跑测试客户端
python test_client.py
```
预期:客户端发送假音频 -> commit -> 收到 `response.audio_transcript.delta`(假文本流)+ `response.audio.delta`(假音频)+ `response.done`。

## 切换真实后端(vLLM + Qwen3-Omni)
1. 先起 vLLM 模型服务(需 GPU):
   ```bash
   vllm serve Qwen/Qwen3-Omni-30B-A3B-Instruct --quantization awq --port 8001
   ```
2. 切后端:
   ```bash
   export OMNI_BACKEND=vllm
   export VLLM_BASE_URL=http://localhost:8001
   export VLLM_MODEL=Qwen/Qwen3-Omni-30B-A3B-Instruct
   uvicorn app.main:app --port 8000
   ```
> ⚠️ `omni_client.py` 里的 `VLLMOmniClient` 是示意结构:不同 vLLM 版本对音频输入/流式音频输出的 API 略有差异,需对照 vLLM 文档调整请求体与响应解析。生产化前请压测(见指南 §5 并发估算)。

## 事件协议(对齐 Qwen Realtime)
客户端->服务端:`session.update` / `input_audio_buffer.append` / `input_audio_buffer.commit`
服务端->客户端:`session.updated` / `response.create` / `response.audio_transcript.delta` / `response.audio.delta` / `response.done` / `response.cancelled` / `input_audio_buffer.speech_started` / `error`

音频统一 PCM16,base64 编码放进 JSON。

## 测试 barge-in(打断)
`test_client.py` 默认走"发音频->commit->收回复"。要测打断:在收到 `response.audio_transcript.delta` 期间,再用一个客户端(或改脚本并发)向同一 `client_id` 发 `input_audio_buffer.append`(高能量"说话"音频),服务端 VAD 会检测到并:
1. `cancel()` 当前生成任务
2. 推送 `input_audio_buffer.speech_started`
3. 原回复流以 `response.cancelled` 结束

## 与 project9 的关系
- **复用**:`ConnectionManager`、后台任务+事件推送模式、`while True: receive_text()` 双向通道。
- **新增**:VAD、音频流水线、barge-in、模型流式客户端。
- 把 project9-1 的 `FakeListChatModel` 换成 `omni_client`(fake 或 vLLM),再加一层实时音频工程。

详见 `../project9-2/自部署指南.md`。
