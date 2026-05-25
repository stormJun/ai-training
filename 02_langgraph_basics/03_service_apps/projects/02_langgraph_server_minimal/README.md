# LangGraph 最小服务示例

本目录是一个基于 LangGraph 的最小服务示例，用来演示如何把一个简单图封装成可本地运行的 LangGraph Server，并配合 LangGraph Studio 进行调试。

当前核心逻辑定义在 `src/agent/graph.py`，它实现了一个单节点图：接收输入状态，读取运行时上下文，并返回一段固定格式的输出。这个示例适合用于学习以下内容：

- LangGraph 项目的最小目录结构
- `langgraph.json` 的图入口配置方式
- `langgraph dev` 的本地开发启动流程
- LangGraph Studio 与本地 API 的联调方式

如果你要扩展为更复杂的工作流，可以在此基础上继续添加节点、边、状态字段和配置项。

## 当前示例做了什么

当前图只包含一个节点 `call_model`，执行逻辑非常简单：

1. 接收输入状态 `State`
2. 从 `runtime.context` 中读取 `my_configurable_param`
3. 返回固定格式的字符串结果

同时，图的定义也按更适合学习的标准步骤展开：

1. 定义 `State`
2. 定义 `Context`
3. 编写节点函数
4. 创建 `StateGraph` builder
5. 添加节点和边
6. `compile()` 得到可执行图

这意味着它本质上是一个“最小可运行示例”，重点不在业务逻辑，而在服务化、图结构定义和调试流程本身。

## 快速开始

### 1. 创建并激活本地虚拟环境

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/03_service_apps/projects/02_langgraph_server_minimal
python3 -m venv .venv
source .venv/bin/activate
```

### 2. 安装项目依赖和 LangGraph CLI

```bash
pip install -e . "langgraph-cli[inmem]"
```

这里的 `langgraph-cli` 用于提供 `langgraph dev` 命令；没有它时，图代码虽然可以通过 Python 直接调用，但无法按 LangGraph Server 的方式启动本地服务。

### 3. 创建本地环境配置

```bash
cp .env.example .env
```

如果你希望在 Studio 中看到 LangSmith 的 tracing / runs，需要在 `.env` 中配置：

```env
LANGSMITH_PROJECT=new-agent
LANGSMITH_API_KEY=lsv2...
```

如果不配置 `LANGSMITH_API_KEY`，本地图依然可以运行，只是 Studio 中不会显示 LangSmith tracing。

### 4. 启动本地开发服务

```bash
langgraph dev
```

启动成功后，通常会看到以下地址：

- API: `http://127.0.0.1:2024`
- API 文档: `http://127.0.0.1:2024/docs`
- Studio: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

## `langgraph.json` 说明

`langgraph.json` 是 LangGraph 项目的入口配置文件。`langgraph dev` 启动时，会优先读取它来确定：

- 当前项目依赖如何解析
- 哪个图对象要作为服务入口
- 环境变量从哪个文件加载

当前文件内容如下：

```json
{
  "$schema": "https://langgra.ph/schema.json",
  "dependencies": ["."],
  "graphs": {
    "agent": "./src/agent/graph.py:graph"
  },
  "env": ".env",
  "image_distro": "wolfi"
}
```

各字段含义如下：

- `$schema`
  用于告诉编辑器和工具，这个 JSON 应该遵循哪份 schema，主要作用是提供结构校验和自动补全。

- `dependencies`
  指定项目依赖来源。这里的 `"."` 表示依赖当前目录这个 Python 项目本身。

- `graphs`
  指定可以被 LangGraph Server 暴露的图入口。
  当前配置表示：
  - 图名称是 `agent`
  - 图对象位于 `./src/agent/graph.py`
  - 真正导出的对象名是 `graph`

- `env`
  指定启动时要加载的环境变量文件。这里使用的是当前目录下的 `.env`。

- `image_distro`
  主要用于容器化或部署场景，表示默认镜像分发基础。对本地学习 `langgraph dev` 的影响较小，可以先把它理解为部署相关配置。

需要注意的是，`langgraph.json` 是标准 JSON 文件，本身不支持注释。如果要补充说明，推荐像当前这样写在 README 中，而不是直接往 JSON 文件里插入注释。

## 常用访问方式

### 查看 API 文档

浏览器打开：

```text
http://127.0.0.1:2024/docs
```

如果这个地址可以打开，说明本地 LangGraph API 已经正常启动。

### 打开 LangGraph Studio

直接打开终端里打印出来的 Studio URL。通常格式如下：

```text
https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024
```

如果你的 LangSmith 账号关联了特定组织，URL 中可能还会附带 `organizationId=...` 参数。

## 常见问题排查

### 1. `Failed to initialize Studio`

这个提示通常表示：浏览器已经打开了 Studio，但 Studio 无法连接到本地 LangGraph API。

优先检查：

1. `langgraph dev` 是否仍在运行
2. `http://127.0.0.1:2024/docs` 是否能正常打开
3. 是否使用了当前这次启动输出的 Studio URL，而不是旧标签页中的历史地址

只要 API 地址不可访问，Studio 就无法初始化。

### 2. `Not seeing LangSmith runs?`

这个提示表示：

- 本地 LangGraph API 已经启动
- 但当前服务没有配置 `LANGSMITH_API_KEY`
- 因此 LangSmith tracing 未启用

解决方式：

1. 在 `.env` 中加入 `LANGSMITH_API_KEY`
2. 重启 `langgraph dev`

如果不需要 LangSmith tracing，这条提示可以忽略，不影响本地运行和 API 调试。

### 3. `langgraph: command not found`

这表示本地环境里没有安装 LangGraph CLI。通常原因有两个：

1. 还没有执行 `pip install -e . "langgraph-cli[inmem]"`
2. 当前终端没有激活 `.venv`

先执行：

```bash
source .venv/bin/activate
```

再运行：

```bash
langgraph --version
```

如果命令仍不存在，再重新安装 CLI。

## 如何扩展这个示例

你可以从两个方向扩展：

### 1. 扩展运行时配置

修改 `src/agent/graph.py` 中的 `Context`，暴露更多运行时上下文参数，例如：

- 动态系统提示词
- 当前用户 ID
- 模型选择参数
- 外部服务地址

### 2. 扩展图结构

当前图只有一个节点。你可以继续添加：

- 多个处理节点
- 条件边
- 工具调用
- 中断与恢复
- 检查点与记忆

这个示例的价值在于：它已经把 LangGraph Server 的最小运行骨架搭好了，你只需要在图逻辑上继续扩展即可。

## 相关文件

- `src/agent/graph.py`
  当前示例图的核心实现
- `langgraph.json`
  LangGraph 项目入口配置
- `.env.example`
  本地环境变量示例
- `tests/test_graph.py`
  最小测试示例

## 说明

本目录适合作为 “LangGraph 服务最小示例 / 最小可运行项目” 来学习，不适合作为复杂业务工作流示例。如果你想看更接近实际业务逻辑的 LangGraph 服务项目，建议继续阅读同级的 `../03_order_workflow_app/`。  
