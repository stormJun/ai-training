# plugin_hot_reload_demo

一个最小可运行的 LangGraph 插件热重载 demo，用来演示这条链路：

```text
/reload
  -> PluginManager 重新扫描插件目录
  -> importlib.reload() 重新加载插件模块
  -> GraphManager 基于新插件重建 graph
  -> 后续新请求切到新 graph
  -> 已持有旧 graph 的请求继续跑旧逻辑
```

## 目录结构

```text
plugin_hot_reload_demo
├── pyproject.toml
├── README.md
├── src/plugin_hot_reload_demo
│   ├── api.py
│   ├── graph_manager.py
│   ├── models.py
│   ├── plugin_manager.py
│   └── plugins
│       ├── greeting.py
│       └── invoice.py
└── tests/test_hot_reload.py
```

## 安装

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo
python3 -m venv .venv
source .venv/bin/activate
pip install '.[dev]'
```

## 运行测试

```bash
.venv/bin/python -m pytest tests/test_hot_reload.py -q
```

## 启动服务

```bash
source .venv/bin/activate
uvicorn plugin_hot_reload_demo.api:app --host 127.0.0.1 --port 8020
```

## 试用接口

健康检查：

```bash
curl http://127.0.0.1:8020/health
```

对话：

```bash
curl -X POST http://127.0.0.1:8020/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"hello"}'
```

默认会命中 `greeting` 插件，返回：

```json
{"response":"greeting-v1:hello"}
```

## 手工验证热重载

1. 打开 [greeting.py](/Users/songxijun/workspace/otherProject/ai-training/04_workflow_orchestration/langchain_langgraph_foundations/plugin_hot_reload_demo/src/plugin_hot_reload_demo/plugins/greeting.py)
2. 把 `greeting-v1` 改成 `greeting-v2`
3. 调用 `/reload`

```bash
curl -X POST http://127.0.0.1:8020/reload
```

4. 再次调用 `/chat`

```bash
curl -X POST http://127.0.0.1:8020/chat \
  -H 'Content-Type: application/json' \
  -d '{"query":"hello"}'
```

这次会返回：

```json
{"response":"greeting-v2:hello"}
```

## 原理

- `PluginManager` 负责发现 `plugins/` 下的模块，并用 `importlib.import_module()` / `importlib.reload()` 重新加载模块代码
- `GraphManager` 不直接修改旧 graph，而是基于当前插件对象重新编译一张新的 LangGraph
- `/chat` 每次请求都会获取当前 graph 引用，所以 reload 之后的新请求会自动进入新 graph
- 旧请求如果已经拿到了旧 graph，它仍然会沿着旧引用执行完，不会被中途替换
