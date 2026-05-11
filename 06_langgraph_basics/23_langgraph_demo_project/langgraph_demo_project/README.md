# 23_langgraph_demo_project/langgraph_demo_project

一个可运行的 `LangGraph Master / Subagent` 演示项目，参考
`AIAgent/第7章/7.7/LangGraph-a2a`，但去掉了外部模型、A2A 协议依赖和绝对路径数据，改成离线可运行的本地版本。

## 项目结构

```text
23_langgraph_demo_project/langgraph_demo_project
├── src/langgraph_demo
│   ├── apps/
│   │   ├── stock_service.py
│   │   └── analysis_service.py
│   ├── data/stocks.json
│   ├── analysis_agent.py
│   ├── host_agent.py
│   ├── models.py
│   ├── run_all.py
│   ├── stock_agent.py
│   └── store.py
└── tests/test_demo.py
```

## 这份 demo 串起来的技术

- `LangGraph`
  - `StockAgent`：子代理 1，负责单股票信息查询
  - `AnalysisAgent`：子代理 2，负责多股票分析与排序
  - `HostAgent`：主控代理，负责路由、分发、汇总
- `FastAPI`
  - 暴露两个子代理服务接口
- `httpx`
  - 主控通过 HTTP 调用子代理
- `本地 JSON 数据`
  - 代替外部行情接口，保证可离线运行

## 快速开始

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/23_langgraph_demo_project/langgraph_demo_project
python3 -m venv .venv
source .venv/bin/activate
pip install '.[dev]'
```

### 方式 1：一条命令直接跑完整 demo

```bash
python -m langgraph_demo.run_all --query "对比一下 300750 和 600519，哪家更值得关注？"
```

这个命令会：

1. 自动启动两个 FastAPI 子代理服务
2. 让 Host Agent 通过 HTTP 分发请求
3. 输出最终汇总结果
4. 自动关闭服务

### 方式 2：分别启动两个子代理服务

终端 1：

```bash
uvicorn langgraph_demo.apps.stock_service:app --host 127.0.0.1 --port 8011
```

终端 2：

```bash
uvicorn langgraph_demo.apps.analysis_service:app --host 127.0.0.1 --port 8012
```

终端 3：

```bash
python -m langgraph_demo.host_agent --mode remote --query "300750 是什么公司？"
python -m langgraph_demo.host_agent --mode remote --query "对比一下 300750、600519、000651，哪家更值得关注？"
```

### 方式 3：不启动服务，直接本地调用

```bash
python -m langgraph_demo.host_agent --mode direct --query "600519 是什么公司？"
```

## 示例查询

- `300750 是什么公司？`
- `查询一下贵州茅台的最新股价表现`
- `对比一下 300750 和 600519，哪家更值得关注？`
- `分析 300750、600519、000651 的基本面和价格表现`

## 测试

```bash
pytest
```
