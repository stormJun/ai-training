# P15 Ollama FastAPI 入门教程

这篇文档专门讲 [01_ollama_fastapi_server.py](/Users/songxijun/workspace/otherProject/ai-training/40_fastapi_llm_serving/01_ollama_fastapi_server.py) 和 [01_ollama_fastapi_client.py](/Users/songxijun/workspace/otherProject/ai-training/40_fastapi_llm_serving/01_ollama_fastapi_client.py) 这组最基础的 FastAPI demo。

它的目标不是做复杂工程封装，而是帮你先跑通下面这条最小链路：

```text
客户端请求
-> FastAPI 服务
-> Ollama 本地模型接口
-> FastAPI 返回结果
-> 客户端打印输出
```

如果你是第一次把本地 LLM 包装成 HTTP 服务，这个 demo 很适合作为起点。

## 一、这个 demo 想解决什么问题

很多人在本地跑通 Ollama 后，最初的调用方式通常是：

- 直接命令行交互
- 或者脚本里直接请求 Ollama 原生接口

但一旦想把它变成“可被前端、其他服务、测试脚本统一调用”的能力，就需要再包一层服务接口。

这个 demo 做的事情就是：

1. 用 FastAPI 暴露统一的 HTTP 接口
2. 把 Ollama 的生成和聊天能力包装成标准 REST API
3. 同时支持：
   - 非流式返回
   - 流式返回

可以把它理解成一个最小的“本地模型代理服务”。

## 二、两个文件分别负责什么

### 1. `01_ollama_fastapi_server.py`

这是服务端。

它负责：

- 创建 FastAPI 应用
- 定义请求数据模型
- 暴露 `/generate` 和 `/chat` 两类接口
- 把请求转发给本地 Ollama
- 把 Ollama 返回结果再包装成统一响应

你可以把它看成：

```text
FastAPI 代理层
```

### 2. `01_ollama_fastapi_client.py`

这是测试客户端。

它负责：

- 调 FastAPI 服务
- 分别测试：
  - 健康检查
  - 非流式生成
  - 流式生成
  - 非流式聊天
  - 流式聊天
- 把结果打印出来

你可以把它看成：

```text
最小测试入口
```

## 三、先决条件

在跑这个 demo 前，至少满足下面几件事。

### 1. 本地 Ollama 正在运行

默认地址写死在服务端里：

```python
OLLAMA_API_URL = "http://localhost:11434/api/generate"
OLLAMA_CHAT_URL = "http://localhost:11434/api/chat"
```

所以你需要先确认：

- Ollama 已启动
- `11434` 端口可访问

### 2. 本地已经拉好模型

当前代码默认模型名是：

```python
qwen3:8b
```

所以至少要保证这个模型存在。否则你要手动把请求里的 `model` 改成自己本机已有模型。

### 3. Python 依赖已安装

在目录 [40_fastapi_llm_serving](/Users/songxijun/workspace/otherProject/ai-training/40_fastapi_llm_serving) 下执行：

```bash
uv sync --locked
```

## 四、先看服务端代码结构

服务端代码虽然不长，但已经把 FastAPI 里几个最关键的基础点都串起来了。

### 1. 创建应用和路由

最开始这几行：

```python
app = FastAPI(title="Ollama FastAPI Proxy", version="1.0.0")
llm_api = APIRouter()
```

含义是：

- `app` 是整个 FastAPI 应用入口
- `llm_api` 是单独拆出来的一组路由

后面通过：

```python
app.include_router(llm_api, prefix="/api/v1", tags=["LLM"])
```

把这些路由挂到：

```text
/api/v1
```

下面。

所以最终接口路径变成：

- `/api/v1/generate`
- `/api/v1/chat`

### 2. 用 Pydantic 定义请求结构

服务端定义了两个请求模型：

- `GenerateRequest`
- `ChatRequest`

作用很直接：

- `GenerateRequest` 用于文本生成
- `ChatRequest` 用于聊天消息

这样做的好处是：

- 请求字段更清晰
- FastAPI 自动做参数校验
- Swagger 文档会自动生成

### 3. `/generate` 和 `/chat` 的角色分工

这两个接口分别对应 Ollama 两类能力：

- `/generate`
  - 适合单段 prompt 生成
- `/chat`
  - 适合消息列表形式的多轮聊天

这也是为什么 `GenerateRequest` 里有：

- `prompt`
- `max_tokens`

而 `ChatRequest` 里有：

- `messages`

### 4. 服务端本质上是在“转发请求”

无论是 `/generate` 还是 `/chat`，核心逻辑都是：

1. 先把前端 / 客户端传来的请求整理成 Ollama 需要的格式
2. 再用 `httpx.AsyncClient()` 请求 Ollama
3. 最后把返回结果重新包装后再交给调用方

也就是说，这个 FastAPI 服务并不自己推理，它只是：

```text
代理层 + 统一接口层
```

## 五、怎么跑起来

### 第一步：启动 Ollama

先确认本地 Ollama 可用。如果你已经能直接调用 Ollama，可以跳过这一步。

### 第二步：启动 FastAPI 服务

在 [40_fastapi_llm_serving](/Users/songxijun/workspace/otherProject/ai-training/40_fastapi_llm_serving) 目录下执行：

```bash
uvicorn 01_ollama_fastapi_server:app --host 0.0.0.0 --port 8000
```

如果启动成功，默认服务地址就是：

```text
http://localhost:8000
```

你也可以直接打开：

```text
http://localhost:8000/docs
```

看 FastAPI 自动生成的接口文档。

### 第三步：先测健康检查

浏览器或命令行访问：

```text
http://localhost:8000/health
```

如果正常，应该能拿到类似：

```json
{
  "status": "healthy",
  "message": "Ollama FastAPI Proxy is running"
}
```

## 六、怎么测试非流式调用

### 1. 非流式生成

客户端里对应的是：

- `test_generate_non_stream()`

它会向：

```text
/api/v1/generate
```

发送请求，参数里：

- `stream=False`

所以服务端走的是“普通 JSON 返回”逻辑。

服务端最终返回：

```json
{
  "generated_text": "..."
}
```

### 2. 非流式聊天

客户端里对应的是：

- `test_chat_non_stream()`

它会向：

```text
/api/v1/chat
```

发送 `messages` 列表，服务端拿到 Ollama 返回结果后，再包装成：

```json
{
  "message": {...}
}
```

这部分最适合先理解“消息格式的聊天接口是什么样子”。

## 七、怎么测试流式调用

这是这个 demo 最值得看的部分。

### 1. 服务端流式逻辑

无论是 `/generate` 还是 `/chat`，只要请求里：

```python
stream = True
```

服务端就不会一次性等完整结果，而是：

1. 用 `httpx.AsyncClient().stream(...)` 请求 Ollama
2. 持续读取 Ollama 返回的每一行
3. 每拿到一段内容，就立刻 `yield`
4. 最后交给：

```python
StreamingResponse(...)
```

返回给客户端

所以这里最重要的 FastAPI 知识点就是：

- `StreamingResponse`

它让服务端可以边生成边返回，而不是一次性返回整个结果。

### 2. 客户端流式逻辑

客户端里：

- `test_generate_stream()`
- `test_chat_stream()`

都用了：

```python
requests.post(..., stream=True)
```

然后通过：

```python
response.iter_lines()
```

逐行读取服务端返回的 chunk。

这一来一回，就形成了完整的流式链路：

```text
Ollama 流式输出
-> FastAPI StreamingResponse
-> requests.iter_lines()
-> 终端逐步打印
```

## 八、这个 demo 最值得学的 5 个点

### 1. FastAPI 如何快速包装本地模型能力

不是自己实现模型推理，而是先把已有的 Ollama 能力包装成统一 API。

### 2. Pydantic 请求模型怎么定义

通过 `GenerateRequest` 和 `ChatRequest`，把不同接口的输入结构清楚分开。

### 3. `APIRouter` 怎么组织接口

虽然这里只有两条主接口，但已经用了独立 router，这个习惯在后续更复杂项目里非常重要。

### 4. 非流式和流式的分支写法

同一个接口里，根据：

```python
request.stream
```

决定走普通 JSON 还是 `StreamingResponse`，这是 LLM 服务里很常见的写法。

### 5. client 脚本怎么配合服务端验证

这个 demo 不只是“写个服务端”，还配了一个独立客户端，方便你确认服务端到底有没有真的跑通。

## 九、常见问题怎么排查

### 1. `/health` 正常，但 `/generate` 或 `/chat` 报错

大概率说明：

- FastAPI 服务本身启动了
- 但 Ollama 没启动，或者模型名不对

优先检查：

- `http://localhost:11434` 是否可达
- `qwen3:8b` 是否存在

### 2. 请求返回 404

优先检查路径是不是写错了。

这个 demo 的主接口带有前缀：

```text
/api/v1/generate
/api/v1/chat
```

不是直接 `/generate` 或 `/chat`。

### 3. 流式调用没有逐步输出

优先检查：

- 客户端是否用了 `stream=True`
- 服务端是否真的返回了 `StreamingResponse`
- Ollama 本身是否开启流式返回

### 4. 模型输出为空

优先检查：

- prompt 是否太短或异常
- 请求参数是否正确传给了 Ollama
- Ollama 返回体中字段名是否和代码假设一致

## 十、推荐你接着看什么

如果这组 demo 你已经跑通，下一步建议这样接：

1. 继续看 [41_multimodal_fastapi_serving/P16-FastAPI-Qwen-VL-server.py](/Users/songxijun/workspace/otherProject/ai-training/41_multimodal_fastapi_serving/P16-FastAPI-Qwen-VL-server.py)
   - 看多模态版本的服务如何组织
2. 再看 [42_dockerized_service_apps](/Users/songxijun/workspace/otherProject/ai-training/42_dockerized_service_apps)
   - 看 FastAPI 服务怎么进入容器化
3. 再看 [06_langgraph_basics/23_langgraph_demo_project/langgraph_demo_project/src/langgraph_demo/apps](/Users/songxijun/workspace/otherProject/ai-training/06_langgraph_basics/23_langgraph_demo_project/langgraph_demo_project/src/langgraph_demo/apps)
   - 看 FastAPI 如何包装子代理服务

## 一句话总结

这组 P15 demo 的核心价值，是让你先跑通一个最小的“本地 LLM -> FastAPI 代理 -> 客户端调用”闭环，并理解流式与非流式服务分别是怎么写出来的。
