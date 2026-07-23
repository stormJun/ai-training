# 算子化数据资产 Demo

这是一个基于 `../算子设计方案.md` 的最小可运行 Demo。

## 启动

在仓库根目录执行：

```bash
PYTHONPATH=openclaw uvicorn operator_demo.app:app --reload --port 8010
```

浏览器打开：

```text
http://127.0.0.1:8010
```

## 功能

- `GET /operators`：查看已注册算子。
- `POST /operators/{name}/{version}/execute`：执行单个算子。
- `POST /workflows/default/run`：执行默认工作流。
- `GET /runs/history`：查看执行历史。

默认工作流：

```text
data_access -> clean -> quality_eval
```

示例数据在 `data/users.csv`。
