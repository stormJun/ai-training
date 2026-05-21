# A2A 与 LangGraph

本主题提供 A2A 协作与 LangGraph 结合的最小脚本示例，重点展示：

- 如何先实现一个可调用工具的 LangGraph Agent
- 如何再把这个 Agent 封装成 A2A 协议服务

## 内容

- `p28-A2A-LangGraph.py`
  - LangGraph 搜索 Agent 本体
- `p28-A2A-LangGraph2.py`
  - A2A 服务封装层

## 两个文件分别做什么

### `p28-A2A-LangGraph.py`

这个文件主要实现一个基于 LangGraph 的搜索型 Agent，本质上是“Agent 逻辑层”。

它包含的核心内容有：

- `search_tavily(...)`
  - 使用 Tavily 执行 Web 搜索的工具函数
- `ResponseFormat`
  - 约束 Agent 最终输出状态的结构化模型
- `SearchAgent`
  - 封装 LangGraph Agent 的主类
  - 根据环境变量选择模型来源（Google 或 OpenAI 兼容接口）
  - 使用 `create_react_agent(...)` 构建带搜索工具的 Agent
  - 提供同步调用 `invoke(...)` 和流式调用 `stream(...)`

如果只看这个文件，可以把它理解成：

> “先做出一个能搜索网络并生成回答的 LangGraph Agent”

### `p28-A2A-LangGraph2.py`

这个文件不重新实现搜索逻辑，而是把前一个文件里的 `SearchAgent` 包装成 A2A 协议服务，本质上是“服务接入层”。

它包含的核心内容有：

- 动态加载 `p28-A2A-LangGraph.py`
  - 取出 `SearchAgent` 和 `ResponseFormat`
- `SearchAgentExecutor`
  - 把 `SearchAgent` 适配成 A2A 可调用执行器
- `AgentSkill`
  - 描述这个 Agent 对外提供的技能（搜索）
- `AgentCard`
  - 描述这个 Agent 的元信息、输入输出模式和能力
- `DefaultRequestHandler`
  - 组合任务存储、推送配置和执行器
- `A2AStarletteApplication`
  - 最终通过 `uvicorn` 启动成一个 A2A HTTP 服务

如果只看这个文件，可以把它理解成：

> “把已经写好的 LangGraph Agent 对外发布为 A2A 服务”

## 两个文件的关系

这两个文件是上下游关系：

1. `p28-A2A-LangGraph.py`
   - 先实现 Agent 的核心能力
2. `p28-A2A-LangGraph2.py`
   - 再把这个 Agent 接到 A2A 协议层

也可以理解成：

- `p28-A2A-LangGraph.py`：Agent 逻辑
- `p28-A2A-LangGraph2.py`：Agent 服务化

## 建议阅读顺序

建议按下面顺序看：

1. 先看 `p28-A2A-LangGraph.py`
   - 理解 Agent 如何调用搜索工具
   - 理解 LangGraph Agent 的输入、输出和会话状态
2. 再看 `p28-A2A-LangGraph2.py`
   - 理解 A2A 如何包装已有 Agent
   - 理解 `AgentCard`、`AgentSkill`、请求处理器和服务启动流程

## 开始方式

先阅读两个脚本的职责分工，再按下面顺序准备环境并运行。

### 1. 创建并激活本地虚拟环境

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/06_langgraph_basics/06_protocols_and_integrations/03_a2a_with_langgraph
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装依赖

```bash
pip install langgraph langchain-core langchain-openai langchain-google-genai tavily-python "a2a-sdk[http-server]==0.3.26" click httpx uvicorn python-dotenv pydantic pytest
```

说明：

- 当前脚本使用的 A2A 导入路径与 `a2a-sdk 0.3.x` 兼容，因此示例里固定使用 `0.3.26`
- `langchain-google-genai` 仍然保留安装，是为了兼容脚本里的 Google 路径

### 3. 配置环境变量

可以直接使用本目录的环境模板：

```bash
cp .env.example .env
```

当前推荐的最小可运行配置是 **DashScope / OpenAI 兼容模式**：

```env
model_source=openai
DASHSCOPE_API_KEY=your_dashscope_key
TOOL_LLM_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
TOOL_LLM_NAME=qwen-plus
```

关于其他变量：

- `GOOGLE_API_KEY` / `GEMINI_API_KEY`
  - 仅在你主动选择 Google 模型路线时需要
- `TAVILY_API_KEY`
  - 用于真实 Web 搜索
  - 如果未配置，服务仍然可以启动，但搜索工具会进入降级模式

### 4. 运行脚本

#### 运行 LangGraph 搜索 Agent 本体

```bash
.venv/bin/python p28-A2A-LangGraph.py
```

该脚本会直接发起一次示例调用，并打印结构化结果。

#### 启动 A2A 服务

```bash
.venv/bin/python p28-A2A-LangGraph2.py --host localhost --port 10001
```

启动成功后，A2A 服务会监听：

```text
http://localhost:10001
```

## 当前运行特性

结合当前脚本实现，这个目录现在具备以下行为：

- 只配置 `DASHSCOPE_API_KEY` 也可以运行
- 不强制要求 `GOOGLE_API_KEY / GEMINI_API_KEY`
- 不强制要求 `TAVILY_API_KEY`
- 缺少 `TAVILY_API_KEY` 时：
  - `p28-A2A-LangGraph2.py` 仍可启动
  - `search_tavily(...)` 会返回清晰的降级信息，而不是直接抛异常

## 常见问题

### 1. `No module named 'a2a.server.apps'`

这通常表示安装的是不兼容的 A2A SDK 版本。请确认当前环境使用的是：

```bash
pip install "a2a-sdk[http-server]==0.3.26"
```

### 2. `API key required for Gemini Developer API`

这说明脚本走到了 Google 模型路线，但当前没有配置 `GOOGLE_API_KEY / GEMINI_API_KEY`。

如果你不打算使用 Google 模型，请在 `.env` 中设置：

```env
model_source=openai
DASHSCOPE_API_KEY=your_dashscope_key
```

### 3. `TAVILY_API_KEY environment variable not set`

旧版本脚本会在缺少 Tavily key 时直接中断。当前版本已经支持降级：

- `p28-A2A-LangGraph2.py` 会给出 warning，但继续启动
- 搜索工具执行时会返回“当前 Web 搜索不可用”的错误信息
