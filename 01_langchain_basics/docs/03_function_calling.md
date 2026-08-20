# Function Calling 与 Tool Use：从 API 协议到工程实践

> 配套代码：[03_function_calling.py](./03_function_calling.py)（OpenAI 兼容 API 最小 demo）
>
> 上游知识：Chat Completion API 基本用法（01/02）
>
> 下游应用：ReAct Agent（[p35-ReACT.md](../../06_finetuning_and_data_processing_and_routing_react_and_tools/p35-ReACT.md)）、LangChain `@tool`（[p36-tool.md](../../06_finetuning_and_data_processing_and_routing_react_and_tools/p36-tool.md)）、eino ToolsNode（[07_pregel_toolnode_demo](../../25_eino/03_graph/demo/07_pregel_toolnode_demo/pregel_toolnode_demo.md)）

---

## 一、Function Calling 是什么

普通 Chat Completion 的路径：

```
用户输入 → 模型生成文本 → 结束
```

Function Calling 的路径：

```
用户输入 → 模型决定调工具 → 生成结构化 tool_use → 本地执行工具 → tool_result 回传 → 模型生成最终回答
```

核心转变：**模型从"只会说话"变成"会提要求"**。模型不直接执行工具，它输出一个结构化的"调用指令"，由 runtime（你的代码）执行后把结果塞回对话。

---

## 二、API 协议详解

### 2.1 tools 参数

在 `chat.completions.create()` 中传入 `tools` 参数，告诉模型有哪些工具可用：

```python
tools = [
    {
        "type": "function",           # 目前只有 "function" 这一种类型
        "function": {
            "name": "get_weather",    # 工具名称——模型用这个名字选工具
            "description": "查询指定城市的当前天气",  # 描述——模型靠这个判断什么时候该用
            "parameters": {           # JSON Schema——模型按这个生成参数
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名称，如北京、上海"
                    },
                    "unit": {
                        "type": "string",
                        "enum": ["celsius", "fahrenheit"],
                        "description": "温度单位"
                    }
                },
                "required": ["city"]   # 必填字段
            }
        }
    }
]

response = client.chat.completions.create(
    model="qwen-plus",
    messages=[{"role": "user", "content": "北京今天冷吗？"}],
    tools=tools,
)
```

**模型拿到 `tools` 后做了什么？**

1. 读取每个工具的 `name` + `description`，判断用户的请求是否匹配某个工具
2. 如果匹配，生成 `tool_calls`（结构化的调用指令）
3. 按 `parameters` JSON Schema 生成参数值

### 2.2 模型返回的 tool_calls 结构

当模型决定调用工具时，响应的 `message` 里会多出 `tool_calls` 字段：

```python
response.choices[0].message.tool_calls[0]
# {
#     "id": "call_abc123",              # 本次调用的唯一 ID——回传时要用
#     "type": "function",
#     "function": {
#         "name": "get_weather",        # 要调的工具名
#         "arguments": "{\"city\": \"北京\", \"unit\": \"celsius\"}"
#                                          # JSON 字符串，不是 dict！需要 json.loads
#     }
# }
```

**关键点：**

- `arguments` 是 **JSON 字符串**，不是 Python dict，必须 `json.loads()` 解析
- `id` 是配对用的——一个 `tool_call_id` 必须对应一个 `tool_result`
- 模型可以同时生成**多个** `tool_calls`（见 2.5 parallel_tool_calls）

### 2.3 回传 tool_result

执行工具后，把结果作为 `role: "tool"` 消息追加到对话，再次调用 API：

```python
# 1. 把 assistant 消息（含 tool_calls）追加进对话
messages.append(response.choices[0].message)

# 2. 执行工具，构造 tool_result 消息
import json

tool_call = response.choices[0].message.tool_calls[0]
args = json.loads(tool_call.function.arguments)
result = get_weather(args["city"], args.get("unit", "celsius"))

messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,       # ← 必须和 tool_call.id 一致
    "name": "get_weather",              # 工具名（部分 API 要求）
    "content": json.dumps(result, ensure_ascii=False)  # 结果字符串
})

# 3. 再次调用 API，模型看到工具结果后生成最终回答
final = client.chat.completions.create(
    model="qwen-plus",
    messages=messages,
    tools=tools,
)
print(final.choices[0].message.content)
# "北京今天气温 5°C，体感较冷，建议穿厚外套。"
```

### 2.4 完整消息流

一次完整的 Function Calling 交互，消息列表如下：

```text
[1] role: user        → "北京今天冷吗？"
[2] role: assistant   → tool_calls: [{name: "get_weather", args: {city: "北京"}}]
[3] role: tool        → tool_call_id: "call_abc123", content: '{"temp": 5, "desc": "晴"}'
[4] role: assistant   → "北京今天气温 5°C，体感较冷。"
```

**消息编号 1→2 是第一次 API 调用，3→4 是第二次。** 每次调用模型都看到完整对话历史。

如果模型拿到工具结果后还想调另一个工具，会再次生成 `tool_calls`，循环继续：

```text
[1] user        → "北京天气如何？需要带伞吗？"
[2] assistant   → tool_calls: [{name: "get_weather", args: {city: "北京"}}]
[3] tool        → '{"temp": 5, "rain": false}'
[4] assistant   → tool_calls: [{name: "get_uv_index", args: {city: "北京"}}]  ← 继续调
[5] tool        → '{"uv": 2}'
[6] assistant   → "北京今天 5°C，无雨不用带伞，紫外线低。"                  ← 最终回答
```

这就是 **多轮 tool_use ↔ tool_result 循环**。

### 2.5 tool_choice：控制模型是否/如何选工具

`tool_choice` 参数控制模型对工具的选择行为，有四种模式：

| 模式 | 值 | 行为 | 典型场景 |
|---|---|---|---|
| **auto**（默认） | `"auto"` | 模型自行决定：调工具或直接回答 | 通用场景 |
| **required** | `"required"` | 模型**必须**调工具，不能直接回答 | 强制走工具流程（如必须查数据库） |
| **none** | `"none"` | 模型**不能**调工具，只能直接回答 | 纯聊天场景，临时屏蔽工具 |
| **指定函数** | `{"type": "function", "function": {"name": "get_weather"}}` | 模型**必须**调用指定函数 | 单工具路由（如 intent 先确定，再强制调对应工具） |

```python
# auto：模型自由选择
response = client.chat.completions.create(
    model="qwen-plus", messages=messages, tools=tools,
    tool_choice="auto",
)

# required：必须调工具（即使问题不需要工具）
response = client.chat.completions.create(
    model="qwen-plus", messages=messages, tools=tools,
    tool_choice="required",
)

# none：禁止调工具
response = client.chat.completions.create(
    model="qwen-plus", messages=messages, tools=tools,
    tool_choice="none",
)

# 指定函数：强制调 get_weather
response = client.chat.completions.create(
    model="qwen-plus", messages=messages, tools=tools,
    tool_choice={"type": "function", "function": {"name": "get_weather"}},
)
```

**什么时候用哪种？**

- **auto**：绝大多数情况。模型足够聪明，能判断是否需要工具。
- **required**：你希望模型**永远不要直接回答**，必须过一遍工具。例如客服场景中，所有回答都必须经过知识库检索。
- **none**：临时屏蔽工具。例如闲聊阶段不需要工具，只有确认了意图后才开工具。
- **指定函数**：你已经通过 intent 识别确定了要调哪个工具，直接强制调用，避免模型选错。

### 2.6 parallel_tool_calls：并行调用

当用户的问题需要多个工具时，模型可以在一次响应中生成多个 `tool_calls`：

```python
# 用户问："北京和上海的天气如何？"
# 模型一次返回两个 tool_calls：

response.choices[0].message.tool_calls
# [
#   {id: "call_1", function: {name: "get_weather", arguments: '{"city": "北京"}'}},
#   {id: "call_2", function: {name: "get_weather", arguments: '{"city": "上海"}'}}
# ]
```

**parallel_tool_calls 参数**（OpenAI 支持）：

```python
response = client.chat.completions.create(
    model="gpt-4o", messages=messages, tools=tools,
    parallel_tool_calls=True,   # 默认 True，允许并行调用
)
```

- `True`（默认）：模型可以一次生成多个 `tool_calls`
- `False`：模型每次最多生成一个 `tool_call`

**关闭并行的场景**：工具之间有依赖关系（工具 B 需要 A 的结果），或者需要严格顺序执行。

**处理并行调用的代码模式：**

```python
assistant_msg = response.choices[0].message
messages.append(assistant_msg)

for tool_call in assistant_msg.tool_calls:
    args = json.loads(tool_call.function.arguments)
    result = dispatch_tool(tool_call.function.name, args)  # 执行工具
    messages.append({
        "role": "tool",
        "tool_call_id": tool_call.id,          # 每个 tool_call_id 必须对应
        "name": tool_call.function.name,
        "content": json.dumps(result, ensure_ascii=False),
    })

# 所有结果追加完毕后，再次调用 API
final = client.chat.completions.create(
    model="qwen-plus", messages=messages, tools=tools,
)
```

**注意**：并行调用时，每个 `tool_result` 必须和对应的 `tool_call.id` 精确配对。遗漏任何一个都会导致 API 报错。

---

## 三、工具定义的 Schema 体系

> **本节是概览。** 完整的深度讲解见 [03_schema_system_deep_dive.md](./03_schema_system_deep_dive.md)，涵盖：为什么需要 Schema、JSON Schema 在协议中的角色、Input/Output/Error 设计原则、Pydantic 自动生成、校验分层模型、校验失败后的处理、Schema 版本演进。

一个完整的工具定义不只是 `name` + `func`，它应该包含三个 Schema：

### 3.1 Input Schema（参数 Schema）

**作用**：告诉模型"这个工具接受什么参数"，模型按此生成 `arguments`。

```python
{
    "name": "transfer_money",
    "description": "从用户账户向目标账户转账",
    "parameters": {
        "type": "object",
        "properties": {
            "to_account": {
                "type": "string",
                "description": "目标账户号",
                "pattern": "^\\d{10,20}$"    # 正则校验
            },
            "amount": {
                "type": "number",
                "description": "转账金额（元）",
                "minimum": 0.01,              # 最小值
                "maximum": 50000              # 最大值
            },
            "currency": {
                "type": "string",
                "enum": ["CNY", "USD", "EUR"],  # 枚举约束
                "description": "币种"
            }
        },
        "required": ["to_account", "amount"]
    }
}
```

**Input Schema 是模型和 runtime 的契约**：

- 模型端：按 Schema 生成结构化参数
- Runtime 端：按 Schema **校验**模型生成的参数（模型不保证 100% 遵守）

**Runtime 校验示例**：

```python
import jsonschema

TOOL_SCHEMAS = {
    "transfer_money": {
        "type": "object",
        "properties": {
            "to_account": {"type": "string", "pattern": r"^\d{10,20}$"},
            "amount": {"type": "number", "minimum": 0.01, "maximum": 50000},
        },
        "required": ["to_account", "amount"],
    }
}

def validate_tool_input(tool_name: str, arguments: dict) -> dict:
    """校验模型生成的工具参数是否符合 Input Schema"""
    schema = TOOL_SCHEMAS.get(tool_name)
    if not schema:
        return arguments  # 无 Schema 的工具跳过校验
    try:
        jsonschema.validate(arguments, schema)
        return arguments
    except jsonschema.ValidationError as e:
        raise ValueError(f"工具 {tool_name} 参数校验失败: {e.message}")

# 使用
args = json.loads(tool_call.function.arguments)
validated_args = validate_tool_input("transfer_money", args)  # 校验后才执行
result = transfer_money(**validated_args)
```

**为什么需要校验？** 模型可能生成不符合 Schema 的参数（幻觉、格式错误），尤其是：
- 数值超出范围（如 `amount: -100`）
- 枚举值不在列表中（如 `currency: "JPY"`）
- 必填字段缺失
- 类型不匹配（如 `amount: "一百"` 而非数字）

### 3.2 Output Schema（返回 Schema）

**作用**：规范化工具的返回结构，让模型和下游消费者能预测返回格式。

API 层面 `tool_result.content` 是自由格式的字符串，但**内部定义**返回 Schema 有三大好处：

1. **模型理解更稳定**：结构化的返回比自然语言更容易让模型准确提取信息
2. **下游集成更可靠**：其他工具或流程可以按 Schema 解析结果
3. **文档即契约**：Schema 自身就是工具行为的文档

```python
# 不好的做法：返回自然语言
def get_weather(city):
    return "北京今天晴，气温5度，北风3级"  # 模型需要 NLU 来提取信息

# 好的做法：返回结构化数据
def get_weather(city):
    return {
        "city": "北京",
        "temperature": 5,
        "unit": "celsius",
        "condition": "晴",
        "wind": {"speed": 3, "direction": "北"}
    }
```

**Output Schema 定义**（不在 API 协议中，是工程约定）：

```python
WEATHER_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "city":         {"type": "string"},
        "temperature":  {"type": "number"},
        "unit":         {"type": "string", "enum": ["celsius", "fahrenheit"]},
        "condition":    {"type": "string"},
        "wind": {
            "type": "object",
            "properties": {
                "speed":     {"type": "number"},
                "direction": {"type": "string"}
            }
        }
    }
}
```

### 3.3 Error Schema（错误 Schema）

**作用**：标准化错误信息，让模型能理解错误并做出合理反应（重试、换参数、告知用户）。

API 的 `tool_result` 有 `is_error` 标志，但错误内容的格式需要自行约定：

```python
# API 层面：tool_result 可以标记为错误
messages.append({
    "role": "tool",
    "tool_call_id": tool_call.id,
    "content": "账户不存在",             # 错误信息是自由文本
    # OpenAI API 支持：但多数兼容 API 不支持
})
```

**好的做法：定义 Error Schema**：

```python
ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "error_code": {"type": "string", "description": "错误码"},
        "message":    {"type": "string", "description": "人可读的错误信息"},
        "retryable":  {"type": "boolean", "description": "是否可重试"},
        "suggestion": {"type": "string", "description": "给模型的建议（如换参数）"},
    },
    "required": ["error_code", "message", "retryable"]
}

# 使用
def transfer_money(to_account, amount):
    if not account_exists(to_account):
        return {
            "error_code": "ACCOUNT_NOT_FOUND",
            "message": f"账户 {to_account} 不存在",
            "retryable": False,
            "suggestion": "请用户确认目标账户号"
        }
    if amount > get_balance():
        return {
            "error_code": "INSUFFICIENT_BALANCE",
            "message": f"余额不足，当前余额 {get_balance()} 元",
            "retryable": True,
            "suggestion": "减少转账金额或先充值"
        }
    # 正常执行...
```

**为什么 Error Schema 重要？**

没有 Error Schema 时，模型收到的是一个无法判断严重程度的字符串，可能：
- 不该重试的错误反复重试（如"账户不存在"）
- 该重试的错误直接放弃（如"网络超时"）
- 无法给用户有意义的建议

有了 Error Schema，模型可以：
- 看 `retryable: true` → 自动重试或调整参数
- 看 `retryable: false` → 直接告知用户
- 看 `suggestion` → 按建议行动

### 3.4 三个 Schema 的关系

```text
Input Schema     → 约束"进"：模型生成参数 + Runtime 校验参数
Output Schema    → 约束"出"：工具返回结构 + 下游解析
Error Schema     → 约束"错"：错误分类 + 模型决策重试/放弃

三者共同构成工具的完整契约。
```

---

## 四、工具选择：模型如何决定调哪个工具

### 4.1 模型选工具的依据

模型选择工具时主要看两个信号：

1. **工具的 `description`**：最关键。描述越精确，模型选得越准。
2. **用户请求的语义**：模型会匹配用户意图和工具描述的语义相似度。

```python
# ❌ 差的描述——太笼统，模型无法区分
{"name": "search", "description": "搜索信息"}

# ✅ 好的描述——精确到使用场景
{"name": "search_product", "description": "在商品库中搜索商品，支持按名称、类别、价格区间筛选"}
```

### 4.2 description 工程技巧

| 技巧 | 说明 | 示例 |
|---|---|---|
| **说清什么时候用** | 明确触发条件 | "当用户询问物流运费时使用" |
| **说清什么时候不用** | 排除歧义 | "仅支持国内快递，不适用国际物流" |
| **给出示例参数** | 帮助模型理解参数格式 | "城市名如'北京'、'上海'" |
| **标注副作用** | 让模型和用户知道风险 | "⚠️ 此操作会修改数据库记录" |

### 4.3 tool_choice 的策略模式

在实际工程中，`tool_choice` 通常不是写死的，而是根据场景动态切换：

```python
def get_tool_choice(intent: str) -> str | dict:
    """根据识别到的意图决定 tool_choice 策略"""

    # 纯闲聊 → 禁用工具
    if intent == "chitchat":
        return "none"

    # 已确定意图 → 强制调对应工具
    if intent in TOOL_MAP:
        return {
            "type": "function",
            "function": {"name": TOOL_MAP[intent]}
        }

    # 其他 → 模型自由选择
    return "auto"
```

这种 **intent → tool_choice** 的模式在很多生产系统中使用（参见 [23apply/金融可信智能体](../../23_agent_case_studies/金融可信智能体：Agentic%20Engineering%20的工程实践与演进.md) 的四工坊架构）。

---

## 五、工具治理

### 5.1 权限等级

工具不应该只有"能用"和"不能用"两种状态。按风险分级：

| 等级 | 标签 | 示例 | 执行策略 |
|---|---|---|---|
| 🟢 只读 | `read` | 查询天气、搜索商品、查询订单 | 自动执行，无需确认 |
| 🟡 写入 | `write` | 修改设置、添加购物车、发送消息 | 需用户确认后执行 |
| 🔴 破坏性 | `destructive` | 删除数据、转账、下架商品 | 需二次确认 + 审计日志 |

```python
TOOL_PERMISSIONS = {
    "get_weather":      {"level": "read"},
    "search_product":   {"level": "read"},
    "add_to_cart":      {"level": "write"},
    "send_message":     {"level": "write"},
    "transfer_money":   {"level": "destructive"},
    "delete_account":   {"level": "destructive"},
}

def execute_tool_with_permission(tool_name: str, args: dict, user_id: str) -> dict:
    """按权限等级执行工具"""
    perm = TOOL_PERMISSIONS.get(tool_name, {"level": "read"})
    level = perm["level"]

    if level == "read":
        return dispatch_tool(tool_name, args)

    elif level == "write":
        if not confirm_with_user(f"确认执行 {tool_name}?"):
            return {"error_code": "USER_DENIED", "message": "用户拒绝执行", "retryable": False}
        return dispatch_tool(tool_name, args)

    elif level == "destructive":
        if not confirm_with_user(f"⚠️ 此操作不可逆，确认执行 {tool_name}?"):
            return {"error_code": "USER_DENIED", "message": "用户拒绝执行", "retryable": False}
        audit_log(tool_name, args, user_id)  # 审计日志
        return dispatch_tool(tool_name, args)
```

### 5.2 参数校验

在 3.1 节已经讲了 Input Schema 校验。这里补充**业务层校验**——超越 JSON Schema 能表达的规则：

```python
def validate_business_rules(tool_name: str, args: dict, user_context: dict) -> None:
    """业务规则校验——JSON Schema 无法覆盖的部分"""

    if tool_name == "transfer_money":
        # 规则1：每日限额
        today_total = get_today_transfer_total(user_context["user_id"])
        if today_total + args["amount"] > 100000:
            raise ValueError("超出每日转账限额 10 万元")

        # 规则2：不能给自己转
        if args["to_account"] == user_context["account_id"]:
            raise ValueError("不能向自己转账")

        # 规则3：非工作时间大额转账需额外验证
        if args["amount"] > 10000 and not is_business_hours():
            raise ValueError("非工作时间大额转账需要短信验证")
```

**校验分层**：

```text
第 1 层：JSON Schema 校验（类型、格式、枚举、范围）→ 自动、通用
第 2 层：业务规则校验（额度、权限、时间约束）      → 需要上下文
第 3 层：运行时校验（账户是否存在、库存是否足够）    → 需要查数据
```

### 5.3 调用审计

对工具调用做全链路记录，用于：

- **排查问题**：用户说"我没转账"→ 查审计日志确认
- **安全合规**：金融、医疗等行业监管要求
- **成本分析**：哪些工具调用最频繁、最耗时

```python
import time
import uuid
from datetime import datetime

class ToolAuditor:
    def __init__(self):
        self.logs = []  # 生产环境替换为数据库/消息队列

    def record(self, tool_name: str, args: dict, result: dict,
               user_id: str, duration_ms: float, status: str):
        self.logs.append({
            "trace_id":   str(uuid.uuid4()),       # 唯一追踪 ID
            "timestamp":  datetime.now().isoformat(),
            "user_id":    user_id,
            "tool_name":  tool_name,
            "input":      args,                     # 入参（注意脱敏）
            "output":     result,                   # 返回值
            "duration_ms": duration_ms,             # 耗时
            "status":     status,                   # success / error / denied
        })

auditor = ToolAuditor()

def execute_with_audit(tool_name: str, args: dict, user_id: str) -> dict:
    start = time.time()
    try:
        result = dispatch_tool(tool_name, args)
        duration = (time.time() - start) * 1000
        auditor.record(tool_name, args, result, user_id, duration, "success")
        return result
    except Exception as e:
        duration = (time.time() - start) * 1000
        auditor.record(tool_name, args, {"error": str(e)}, user_id, duration, "error")
        raise
```

**审计日志要脱敏**：入参中的密码、卡号、手机号等敏感字段不能明文存储。

### 5.4 超时、重试与失败恢复

#### 超时

工具执行不能无限等待。按工具类型设置不同超时：

```python
TOOL_TIMEOUTS = {
    "get_weather":     5,     # 只读查询，5 秒
    "search_product":  10,    # 搜索可能慢，10 秒
    "transfer_money":  30,    # 涉及资金，允许更长
}

async def execute_with_timeout(tool_name: str, args: dict):
    timeout = TOOL_TIMEOUTS.get(tool_name, 10)
    try:
        return await asyncio.wait_for(
            call_tool_async(tool_name, args),
            timeout=timeout
        )
    except asyncio.TimeoutError:
        return {
            "error_code": "TIMEOUT",
            "message": f"工具 {tool_name} 执行超时（{timeout}s）",
            "retryable": True,
            "suggestion": "稍后重试"
        }
```

#### 重试

不是所有错误都该重试。按 Error Schema 的 `retryable` 字段决定：

```python
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception

def is_retryable(exc):
    """只重试可恢复的错误"""
    if isinstance(exc, ToolError):
        return exc.retryable
    return True  # 未知错误默认可重试

@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    retry=retry_if_exception(is_retryable),
)
def execute_with_retry(tool_name: str, args: dict):
    result = dispatch_tool(tool_name, args)
    if isinstance(result, dict) and result.get("error_code"):
        err = ToolError(result["error_code"], result["message"], result.get("retryable", False))
        if err.retryable:
            raise err  # 触发重试
        return result   # 不可重试，直接返回错误
    return result
```

#### 失败恢复策略

| 策略 | 适用场景 | 做法 |
|---|---|---|
| **重试** | 网络抖动、临时故障 | 指数退避重试 2-3 次 |
| **降级** | 主服务不可用 | 切到备用数据源（如缓存） |
| **兜底** | 工具完全不可用 | 返回预设默认值 + 告知用户 |
| **部分失败** | 并行调用中部分失败 | 成功的结果正常返回，失败的走兜底 |

```python
def execute_with_fallback(tool_name: str, args: dict) -> dict:
    """带降级和兜底的执行"""
    try:
        return dispatch_tool(tool_name, args)
    except ServiceUnavailable:
        # 降级：切到缓存
        cached = get_from_cache(tool_name, args)
        if cached:
            return {**cached, "_source": "cache", "_warning": "数据可能不是最新"}
        # 兜底
        return {
            "error_code": "SERVICE_UNAVAILABLE",
            "message": f"{tool_name} 暂时不可用，请稍后再试",
            "retryable": True,
            "suggestion": "稍后重试"
        }
```

### 5.5 Trace 记录

在多工具调用的 Agent 循环中，一次用户请求可能触发多次工具调用。Trace 把这些调用串成一条链路：

```text
用户: "帮我查北京天气，然后订一张去北京的机票"

Trace [req-001]:
  ├─ turn 1: tool_call get_weather(city="北京") → 5°C 晴  [3ms]
  ├─ turn 2: tool_call search_flight(to="北京", date="...") → CA1234 ¥800  [120ms]
  └─ turn 3: 最终回答 → "北京今天 5°C 晴，已找到 CA1234 航班 800 元..."
```

实现方式可以接入 OpenTelemetry、Langfuse 等。最简版用 `trace_id` 串联：

```python
import contextvars

current_trace_id = contextvars.ContextVar("trace_id", default=None)
current_turn = contextvars.ContextVar("turn", default=0)

def start_trace() -> str:
    trace_id = str(uuid.uuid4())
    current_trace_id.set(trace_id)
    current_turn.set(0)
    return trace_id

def next_turn():
    current_turn.set(current_turn.get() + 1)
    return current_turn.get()

# 每次工具调用时记录
def trace_tool_call(tool_name, args, result, duration_ms):
    print(f"Trace [{current_trace_id.get()}] turn {current_turn.get()}: "
          f"{tool_name} → {result}  [{duration_ms:.0f}ms]")
```

---

## 六、Anthropic 的 tool_use 与 OpenAI 的差异

两者机制类似，但 API 格式有差异：

| 维度 | OpenAI | Anthropic |
|---|---|---|
| 参数位置 | `tools` | `tools` |
| tool_choice | `"auto"` / `"required"` / `"none"` / 指定函数 | `"auto"` / `"any"` / 指定函数 |
| 并行调用 | `parallel_tool_calls=True/False` | 默认支持并行 |
| tool_result 位置 | `role: "tool"` 消息 | `role: "user"` 消息中的 `tool_result` block |
| 错误标记 | 无内建 `is_error` | `is_error: true` |
| ID 配对 | `tool_call_id` | `tool_use_id` |

**Anthropic 的 tool_result 是 user message block**（不是独立的 role），这是最大的格式差异：

```python
# Anthropic Messages API
response = client.messages.create(
    model="claude-sonnet-5-20250514",
    messages=[{"role": "user", "content": "北京天气如何？"}],
    tools=[...],
)

# 模型返回 tool_use block
tool_use_block = response.content[0]  # type: "tool_use"

# 回传 tool_result（作为 user message 的 content block）
client.messages.create(
    model="claude-sonnet-5-20250514",
    messages=[
        {"role": "user", "content": "北京天气如何？"},
        {"role": "assistant", "content": [tool_use_block]},
        {"role": "user", "content": [{
            "type": "tool_result",
            "tool_use_id": tool_use_block.id,
            "content": '{"temp": 5}',
            "is_error": False,          # Anthropic 支持标记错误
        }]},
    ],
    tools=[...],
)
```

更多 Anthropic tool_use 的实现细节，参见 [tool-use-and-tool-result.md](../../21_claude_code_source_analysis/tool-use-and-tool-result.md)（Claude Code 源码分析）。

---

## 七、完整代码示例

以下是一个综合了本篇所有概念的最小可运行示例：

```python
"""Function Calling 完整示例：天气 + 转账场景，覆盖三 Schema + tool_choice + 治理"""

import json
import time
import uuid
from datetime import datetime

import jsonschema
from openai import OpenAI

# ── 1. 工具定义（含 Input Schema） ──────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气。仅支持国内城市。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名，如'北京'、'上海'"},
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "transfer_money",
            "description": "⚠️ 从用户账户向目标账户转账。此操作不可逆。",
            "parameters": {
                "type": "object",
                "properties": {
                    "to_account": {
                        "type": "string",
                        "description": "目标账户号（10-20 位数字）",
                        "pattern": r"^\d{10,20}$",
                    },
                    "amount": {
                        "type": "number",
                        "description": "转账金额（元）",
                        "minimum": 0.01,
                        "maximum": 50000,
                    },
                },
                "required": ["to_account", "amount"],
            },
        },
    },
]

# ── 2. Input Schema 校验 ──────────────────────────────────────

INPUT_SCHEMAS = {
    t["function"]["name"]: t["function"]["parameters"] for t in TOOLS
}

def validate_input(tool_name: str, arguments: dict) -> dict:
    schema = INPUT_SCHEMAS.get(tool_name)
    if schema:
        jsonschema.validate(arguments, schema)
    return arguments

# ── 3. 权限等级 ─────────────────────────────────────────────

TOOL_PERMISSIONS = {
    "get_weather":     {"level": "read"},
    "transfer_money":  {"level": "destructive"},
}

# ── 4. 审计 ──────────────────────────────────────────────────

audit_logs = []

def audit(tool_name, args, result, user_id, duration_ms, status):
    audit_logs.append({
        "trace_id": str(uuid.uuid4()),
        "timestamp": datetime.now().isoformat(),
        "user_id": user_id,
        "tool_name": tool_name,
        "input_hash": hash(json.dumps(args, sort_keys=True)),  # 脱敏
        "duration_ms": duration_ms,
        "status": status,
    })

# ── 5. 工具实现 ──────────────────────────────────────────────

def get_weather(city: str) -> dict:
    """返回结构化天气（Output Schema）"""
    mock = {"北京": {"temp": 5, "condition": "晴"}, "上海": {"temp": 12, "condition": "阴"}}
    if city not in mock:
        return {"error_code": "CITY_NOT_SUPPORTED", "message": f"不支持 {city}",
                "retryable": False, "suggestion": "目前仅支持北京、上海"}
    return {"city": city, **mock[city], "unit": "celsius"}

def transfer_money(to_account: str, amount: float) -> dict:
    if not account_exists(to_account):
        return {"error_code": "ACCOUNT_NOT_FOUND", "message": f"账户 {to_account} 不存在",
                "retryable": False, "suggestion": "请确认账户号"}
    return {"transaction_id": f"TXN-{uuid.uuid4().hex[:8]}", "amount": amount, "status": "success"}

def account_exists(account: str) -> bool:
    return account.startswith("6222")  # mock

# ── 6. 统一分发 + 治理 ──────────────────────────────────────

def dispatch(tool_name: str, args: dict, user_id: str = "user_001") -> dict:
    start = time.time()
    try:
        # 校验
        validate_input(tool_name, args)

        # 权限
        perm = TOOL_PERMISSIONS.get(tool_name, {"level": "read"})
        if perm["level"] in ("write", "destructive"):
            # 生产环境弹确认，demo 直接拒绝
            pass

        # 执行
        if tool_name == "get_weather":
            result = get_weather(args["city"])
        elif tool_name == "transfer_money":
            result = transfer_money(args["to_account"], args["amount"])
        else:
            result = {"error_code": "UNKNOWN_TOOL", "message": f"未知工具 {tool_name}",
                      "retryable": False}

        duration = (time.time() - start) * 1000
        audit(tool_name, args, result, user_id, duration, "success")
        return result

    except jsonschema.ValidationError as e:
        duration = (time.time() - start) * 1000
        result = {"error_code": "INVALID_INPUT", "message": e.message, "retryable": True}
        audit(tool_name, args, result, user_id, duration, "error")
        return result
    except Exception as e:
        duration = (time.time() - start) * 1000
        result = {"error_code": "INTERNAL_ERROR", "message": str(e), "retryable": True}
        audit(tool_name, args, result, user_id, duration, "error")
        return result

# ── 7. Agent 循环 ─────────────────────────────────────────────

def run_agent(user_input: str, client: OpenAI, model: str = "qwen-plus"):
    messages = [{"role": "user", "content": user_input}]

    for turn in range(5):  # 最多 5 轮 tool_use 循环
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        assistant_msg = response.choices[0].message
        messages.append(assistant_msg)

        # 没有工具调用 → 最终回答
        if not assistant_msg.tool_calls:
            print(f"最终回答: {assistant_msg.content}")
            break

        # 处理每个 tool_call
        for tc in assistant_msg.tool_calls:
            print(f"[turn {turn}] 调用 {tc.function.name}({tc.function.arguments})")
            args = json.loads(tc.function.arguments)
            result = dispatch(tc.function.name, args)
            print(f"[turn {turn}] 结果: {json.dumps(result, ensure_ascii=False)}")

            messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "name": tc.function.name,
                "content": json.dumps(result, ensure_ascii=False),
            })
    else:
        print("⚠️ 达到最大轮次，Agent 循环终止")

    print(f"\n审计日志: {len(audit_logs)} 条")

# ── 8. 运行 ──────────────────────────────────────────────────

if __name__ == "__main__":
    client = OpenAI(
        base_url="https://dashscope.aliyuncs.com/compatible-mode/v1",
        api_key=os.environ.get("DASHSCOPE_API_KEY"),
    )
    run_agent("北京今天冷吗？", client)
```

---

## 八、知识地图

```text
本文档（API 协议 + Schema + 治理）
  │
  ├─→ p35-ReACT.md        — ReAct 模式：用 Function Calling 做 Thought-Action-Observation 循环
  ├─→ p36-tool.md         — LangChain @tool 装饰器：自动从函数签名生成 Input Schema
  ├─→ p47-tool.md         — 动态工具加载 + 异常处理（重试/超时/缓存/热重载）
  ├─→ p20-mcp.md          — MCP 协议：从 Function Calling 到远程工具发现
  ├─→ 07_pregel_toolnode  — 图编排层：ToolsNode 把多工具包成单顶点
  ├─→ tool-use-and-tool-result.md — Claude Code 源码：tool_use/tool_result 的流式实现
  └─→ tool-resolution-and-permission-isolation.md — Claude Code 源码：工具解析与权限隔离
```
