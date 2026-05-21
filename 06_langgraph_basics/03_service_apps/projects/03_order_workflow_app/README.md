# 电商订单处理工作流

基于LangGraph构建的电商订单处理工作流，集成通义千问大模型，支持意图识别和条件路由。

## 功能特性

- **意图识别**: 自动识别用户的订单相关意图（查询、修改、取消、客服咨询等）
- **通义大模型集成**: 调用通义千问处理复杂的用户问题
- **条件路由**: 根据意图和处理结果智能路由到不同的处理节点
- **工程化设计**: 完整的项目结构，包含服务层、模型定义和测试用例
- **LangSmith监控**: 支持LangSmith监控工作流运行过程

## 项目结构

```
03_order_workflow_app/
├── src/
│   └── agent/
│       ├── __init__.py          # 模块初始化
│       ├── graph.py             # 工作流图定义
│       ├── models.py            # 数据模型
│       ├── services.py          # 服务层
│       └── config.py            # 配置文件
├── tests/
│   └── test_workflow.py         # 测试用例
└── README.md                    # 项目说明
```

## 工作流架构

### 节点说明

1. **意图识别节点** (`intent_recognition_node`)
   - 分析用户输入，识别订单相关意图
   - 支持的意图类型：查询订单、修改订单、取消订单、客服咨询等

2. **通义大模型节点** (`tongyi_llm_node`)
   - 调用通义千问生成专业的客服回复
   - 根据不同意图使用相应的提示模板

3. **订单处理节点** (`order_processing_node`)
   - 执行具体的订单操作
   - 返回处理结果和下一步操作建议

### 边的逻辑

1. **条件边** (`should_continue`)
   - 根据意图识别结果决定是否需要进一步处理
   - 客服相关问题会路由到订单处理节点

2. **处理后路由边** (`route_after_processing`)
   - 根据处理结果决定下一步操作
   - 需要人工转接时会再次调用大模型生成说明

## 快速开始

### 1. 环境配置

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/06_langgraph_basics/03_service_apps/projects/03_order_workflow_app
python3 -m venv .venv
source .venv/bin/activate

# 安装项目依赖
pip install -e .

# 创建本地环境配置
cp .env.example .env
```

`.env` 中只有 `DASHSCOPE_API_KEY` 和 `LANGSMITH_API_KEY` 需要按需填写：

- `DASHSCOPE_API_KEY`
  可选。填写后会调用真实的通义千问；不填时工作流会自动降级到内置兜底逻辑。
- `LANGSMITH_API_KEY`
  可选。仅在你需要 LangSmith tracing / Studio 运行记录时填写。

#### 获取通义千问 API Key

1. 访问 [阿里云DashScope控制台](https://dashscope.console.aliyun.com/)
2. 注册/登录阿里云账号
3. 开通DashScope服务
4. 创建API密钥
5. 将密钥配置到环境变量 `DASHSCOPE_API_KEY`

### 2. 启动 LangGraph 本地服务

```bash
langgraph dev
```

启动成功后，通常可以访问：

- API: `http://127.0.0.1:2024`
- API 文档: `http://127.0.0.1:2024/docs`
- Studio: `https://smith.langchain.com/studio/?baseUrl=http://127.0.0.1:2024`

### 3. 直接运行图

```python
from agent.graph import State, graph

initial_state = State(
    user_input="我想查询我的订单状态",
    intent="",
    order_info={},
    response="",
    next_action="",
    messages=[],
)

result = graph.invoke(
    initial_state,
    context={"user_id": "demo-user", "session_id": "demo-session"},
)
print(result)
```

### 4. 运行测试

```bash
.venv/bin/pytest tests/test_workflow.py -v
```

## 支持的意图类型

| 意图类型 | 关键词示例 | 处理方式 |
|---------|-----------|----------|
| query_order | 查询、查看、订单状态 | 引导用户提供订单号进行查询 |
| modify_order | 修改、更改、地址 | 提供订单修改流程指导 |
| cancel_order | 取消、退单、撤销 | 说明取消政策和退款流程 |
| customer_service | 投诉、问题、客服 | 转接人工客服或提供专业回复 |
| payment_issue | 支付、付款、退款 | 处理支付相关问题 |
| product_inquiry | 商品、产品、规格 | 提供产品信息和购买建议 |

## 配置说明

### 通义千问配置

在 `config.py` 中配置通义千问相关参数：

```python
DASHSCOPE_API_KEY = "your_api_key"
TONGYI_MODEL = "qwen-turbo"
TONGYI_MAX_TOKENS = 2000
TONGYI_TEMPERATURE = 0.7
```

**重要说明**：
- 意图识别节点使用通义千问进行智能意图分析
- 大模型节点调用真实的通义千问API生成回复
- 如果API调用失败，会自动降级到预设回复
- 如果不配置 `DASHSCOPE_API_KEY`，图仍然可以启动和运行，只是不会调用真实模型

### LangSmith监控配置

```python
LANGSMITH_API_KEY = "your_langsmith_api_key"
LANGSMITH_PROJECT = "ecommerce-order-workflow"
```

如果没有 `LANGSMITH_API_KEY`，`langgraph dev` 仍可正常启动；只是不会把运行记录上报到 LangSmith。

## 扩展开发

### 添加新的意图类型

1. 在 `services.py` 的 `IntentRecognitionService` 中添加新的关键词
2. 在 `graph.py` 中更新相应的处理逻辑
3. 在 `config.py` 中添加意图映射配置

### 集成通义千问API

在 `services.py` 的 `TongyiLLMService` 中实现API调用：

```python
def _mock_api_call(self, prompt: str, system_prompt: str) -> str:
    # 实现真实的通义千问API调用
    # 参考阿里云DashScope文档
    pass
```
