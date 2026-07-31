# 工具三 Schema 体系：Input / Output / Error 的契约设计

> 上游：[03_function_calling_guide.md](./03_function_calling_guide.md)（Function Calling API 协议）
>
> 现有相关：[tool_schemas.py](../reference_projects/project1_1/tools/tool_schemas.py)（Pydantic 定义示例）、[P19-纵深防御体系.py](../09_dsl/03_dsl_agent_and_db_gateway/P19-纵深防御体系.py)（输入校验示例）
>
> 下游：[p36-tool.md](../06_finetuning_and_data_processing_and_routing_react_and_tools/p36-tool.md)（LangChain `@tool` 自动生成 Schema）、[tool-use-and-tool-result.md](../21_claudecode_source_analysis/tool-use-and-tool-result.md)（Claude Code 工具结果序列化）

---

## 一、为什么需要 Schema 体系

### 1.1 核心问题：模型输出不可信

普通 Chat Completion 中，模型输出自然语言，用户阅读后自行判断。即使模型说错，后果有限。

Function Calling 不同——模型的输出是**结构化指令**，会直接驱动代码执行。如果模型生成错误的参数：

```text
用户: "转账 500 元到 6222...1234"
模型: tool_calls: [{name: "transfer_money", arguments: '{"to_account": "62221234", "amount": 50000}'}]
                                                          ↑ 金额从 500 变成 50000 ↑
```

没有校验 → 50000 元被转走。**这是真实的安全事故，不是理论风险。**

### 1.2 没有 Schema 的世界

```python
# 没有 Input Schema —— 模型自由发挥，runtime 无法校验
def transfer_money(args):  # args 是什么结构？有哪些字段？类型是什么？
    ...                     # 谁也不知道，出了 bug 只能事后排查

# 没有 Output Schema —— 返回值格式不可预测
result = transfer_money(args)  # 返回字符串？dict？还是抛异常？
model_sees = str(result)       # 模型看到什么取决于 str() 的结果

# 没有 Error Schema —— 模型不知道能不能重试
if result.startswith("错误"):   # 模型要靠自然语言理解判断错误类型
    ...                          # "账户不存在"和"网络超时"该同样处理吗？
```

### 1.3 有 Schema 的世界

```text
                    ┌─────────────────────────────────┐
                    │         工具的完整契约            │
                    │                                 │
  Input Schema ──── │  "我接受什么参数，什么格式"       │ ──── 模型按此生成参数
                    │                                 │      Runtime 按此校验
  Output Schema ── │  "正常时返回什么结构"             │ ──── 下游按此解析
                    │                                 │      模型按此理解结果
  Error Schema ─── │  "出错时返回什么结构，能否重试"   │ ──── 模型按此决策
                    │                                 │
                    └─────────────────────────────────┘
```

三个 Schema 覆盖工具调用的**三种可能结果**：

| 结果 | Schema | 作用 |
|---|---|---|
| 模型生成参数 → 进入工具 | **Input** | 约束"进"，校验模型输出 |
| 工具正常返回 | **Output** | 约束"出"，结构化成功路径 |
| 工具执行出错 | **Error** | 约束"错"，分类失败路径 |

### 1.4 Schema 是"协议"，不是"文档"

关键认知：**Schema 是模型和 runtime 之间的机器可读协议，不是给人看的设计文档。**

- 模型**消费** Input Schema 来生成参数
- Runtime **消费** Input Schema 来校验参数
- 下游**消费** Output Schema 来解析结果
- 模型**消费** Error Schema 来决定下一步行动

文档会过时，但 Schema 是运行时强制的。如果 Schema 和代码不一致，校验就会失败——这恰恰是 Schema 的价值所在。

---

## 二、JSON Schema 在协议中的角色

### 2.1 API 层面：模型看到的 Schema

OpenAI / Anthropic / Qwen 等兼容 API 都用 JSON Schema 定义工具参数。当你在 `tools` 参数中传入：

```python
{
    "type": "function",
    "function": {
        "name": "transfer_money",
        "description": "转账",
        "parameters": {                    # ← 这就是 JSON Schema
            "type": "object",
            "properties": {
                "to_account": {"type": "string"},
                "amount": {"type": "number"}
            },
            "required": ["to_account", "amount"]
        }
    }
}
```

API 把这段 JSON Schema **原封不动地编入 prompt**。模型在推理时看到的就是这段结构定义，然后按它生成 `arguments`。

**这意味着**：你写的 JSON Schema 质量，直接影响模型生成参数的准确性。

### 2.2 模型生成的 arguments 不保证合规

模型看到 Schema ≠ 模型严格遵守 Schema。常见违规：

| 违规类型 | 模型可能生成的 | Schema 要求的 |
|---|---|---|
| 类型错误 | `"amount": "五百"` | `"amount": {"type": "number"}` |
| 缺少必填 | `{"to_account": "6222..."}` | `required: ["to_account", "amount"]` |
| 枚举越界 | `"currency": "JPY"` | `"enum": ["CNY", "USD", "EUR"]` |
| 范围越界 | `"amount": -100` | `"minimum": 0.01` |
| 额外字段 | `{"to_account": "...", "note": "test"}` | `additionalProperties: false` |
| 格式错误 | `"date": "昨天"` | `"format": "date"` |

所以 **runtime 必须校验**，不能信任模型的输出。

### 2.3 JSON Schema 能力边界

JSON Schema 能做的校验：

| 能力 | 示例 |
|---|---|
| 类型检查 | `"type": "string"` / `"number"` / `"boolean"` |
| 必填约束 | `"required": ["to_account", "amount"]` |
| 枚举约束 | `"enum": ["CNY", "USD", "EUR"]` |
| 数值范围 | `"minimum": 0.01, "maximum": 50000` |
| 字符串模式 | `"pattern": "^\\d{10,20}$"` |
| 格式约束 | `"format": "date"` / `"format": "email"` |
| 数组约束 | `"minItems": 1, "maxItems": 10` |
| 嵌套对象 | `"properties": {"wind": {"properties": ...}}` |
| 条件逻辑 | `"oneOf"`, `"anyOf"`, `"if/then/else"` |
| 禁止额外字段 | `"additionalProperties": false` |

JSON Schema **做不到**的校验（需要业务层）：

- 账户是否存在（需要查数据库）
- 余额是否充足（需要查实时状态）
- 每日限额（需要聚合历史记录）
- 非工作时间大额限制（需要业务规则引擎）
- 数据权限（需要用户上下文）

### 2.4 JSON Schema 的版本注意

OpenAI 官方文档声明支持 JSON Schema 的一个子集。实际使用中要注意：

```python
# ✅ 大多数 API 都支持的基础特性
{
    "type": "object",
    "properties": { ... },
    "required": [ ... ]
}

# ⚠️ 部分 API 不支持的高级特性
{
    "$ref": "#/definitions/Account",    # 引用——不一定支持
    "if": {...}, "then": {...},         # 条件——不一定支持
    "oneOf": [...],                      # 互斥——可能被忽略
    "additionalProperties": false,       # 禁额外字段——不一定生效
    "format": "date-time"               # 格式——可能被忽略
}
```

**原则：用 JSON Schema 的基础子集定义工具参数，高级校验放到 runtime 层做。**

---

## 三、Input Schema 设计

### 3.1 设计原则

**原则 1：为模型写 description，不只是为开发者写注释**

```python
# ❌ 开发者视角的 description——模型不知道该传什么
"city": {"type": "string", "description": "城市"}

# ✅ 模型视角的 description——告诉模型具体的值域和格式
"city": {"type": "string", "description": "中国城市名，如'北京'、'上海'、'广州'"}
```

模型不是开发者，它靠 description 理解"我该传什么值"。description 越具体，模型生成正确参数的概率越高。

**原则 2：用枚举约束闭集，用 description 引导开集**

```python
# 闭集（值有限、可枚举）→ 用 enum
"currency": {"type": "string", "enum": ["CNY", "USD", "EUR"], "description": "币种"}

# 开集（值无限、不可枚举）→ 用 description + pattern
"phone": {"type": "string", "pattern": "^1[3-9]\\d{9}$", "description": "中国大陆手机号，如'13800138000'"}
```

**原则 3：必填 vs 可选——只把模型一定能推断的字段设为必填**

```python
# ❌ 把用户没说的字段设为必填 → 模型只能编造
"parameters": {
    "properties": {
        "city": {"type": "string", "description": "城市名"},
        "date": {"type": "string", "description": "日期"}
    },
    "required": ["city", "date"]  # 用户只说"北京天气"，没说日期，模型会编造
}

# ✅ 可推断的必填，不可推断的设默认值或可选
"parameters": {
    "properties": {
        "city": {"type": "string", "description": "城市名"},
        "date": {"type": "string", "description": "日期，默认今天，格式 YYYY-MM-DD"}
    },
    "required": ["city"]  # date 不是必填，工具内部默认今天
}
```

**原则 4：避免过度嵌套**

```python
# ❌ 三层嵌套——模型生成参数的准确率随嵌套深度下降
"address": {
    "type": "object",
    "properties": {
        "location": {
            "type": "object",
            "properties": {
                "city": {"type": "string"}
            }
        }
    }
}

# ✅ 扁平化——一层就能表达清楚
"city": {"type": "string", "description": "城市名"}
"district": {"type": "string", "description": "区县名（可选）"}
```

**原则 5：用 examples 辅助模型理解复杂格式**

```python
"parameters": {
    "type": "object",
    "properties": {
        "date_range": {
            "type": "object",
            "description": "日期范围",
            "properties": {
                "start": {"type": "string", "description": "开始日期，如 2024-01-01"},
                "end":   {"type": "string", "description": "结束日期，如 2024-01-31"}
            },
            "required": ["start", "end"]
        }
    }
}
# 如果 description 里的示例还不够清晰，可以在工具的 description 里加示例：
# "查询指定日期范围的订单。示例：date_range={\"start\":\"2024-01-01\",\"end\":\"2024-01-31\"}"
```

### 3.2 常见模式

#### 枚举 + description 联合

```python
"sort_order": {
    "type": "string",
    "enum": ["asc", "desc"],
    "description": "排序方向：asc=升序，desc=降序"
}
```

枚举限制了取值范围，description 解释每个值的含义。两者缺一不可：
- 没有 enum → 模型可能输出 `"ascending"` 而不是 `"asc"`
- 没有 description → 模型可能不理解 `asc` 的含义而选错

#### 可选字段 + 默认值说明

```python
"page_size": {
    "type": "integer",
    "description": "每页条数，默认 20，最大 100",
    "minimum": 1,
    "maximum": 100,
    "default": 20
}
# 不是 required 字段，工具内部有默认值
```

#### 数组 + 元素约束

```python
"product_ids": {
    "type": "array",
    "items": {"type": "string", "pattern": "^[A-Z]\\d{3}$"},
    "minItems": 1,
    "maxItems": 10,
    "description": "商品代码列表，每个为1个大写字母+3位数字，如['A001','B002']，最多10个"
}
```

#### 互斥参数用 description 标注

JSON Schema 的 `oneOf` 在 Function Calling 中支持不完善。替代方案：

```python
"parameters": {
    "type": "object",
    "properties": {
        "order_id":  {"type": "string", "description": "订单号（与 tracking_number 二选一）"},
        "tracking_number": {"type": "string", "description": "运单号（与 order_id 二选一）"}
    },
    "description": "查询物流状态。请提供 order_id 或 tracking_number 之一，不要同时提供。"
}
# 在工具的顶层 description 里说明互斥关系，让模型理解约束
```

### 3.3 Pydantic → JSON Schema 自动生成

手写 JSON Schema 容易出错且维护成本高。生产环境推荐用 Pydantic 定义模型，自动生成 Schema：

```python
from pydantic import BaseModel, Field
from typing import Optional
from enum import Enum

class Currency(str, Enum):
    CNY = "CNY"
    USD = "USD"
    EUR = "EUR"

class TransferInput(BaseModel):
    """转账工具参数"""
    to_account: str = Field(
        ...,
        description="目标账户号（10-20 位数字）",
        pattern=r"^\d{10,20}$",
        examples=["6222123456789012"],
    )
    amount: float = Field(
        ...,
        description="转账金额（元），0.01 - 50000",
        gt=0,
        le=50000,
    )
    currency: Currency = Field(
        default=Currency.CNY,
        description="币种，默认 CNY",
    )
    note: Optional[str] = Field(
        default=None,
        description="转账备注（可选），最多 50 字",
        max_length=50,
    )

# 自动生成 JSON Schema —— 和手写的一模一样，但类型安全
schema = TransferInput.model_json_schema()
print(json.dumps(schema, indent=2, ensure_ascii=False))
```

输出：

```json
{
  "title": "TransferInput",
  "description": "转账工具参数",
  "type": "object",
  "properties": {
    "to_account": {
      "type": "string",
      "description": "目标账户号（10-20 位数字）",
      "pattern": "^\\d{10,20}$",
      "examples": ["6222123456789012"]
    },
    "amount": {
      "type": "number",
      "description": "转账金额（元），0.01 - 50000",
      "exclusiveMinimum": 0,
      "maximum": 50000
    },
    "currency": {
      "allOf": [{"$ref": "#/$defs/Currency"}],
      "description": "币种，默认 CNY",
      "default": "CNY"
    },
    "note": {
      "anyOf": [{"type": "string", "maxLength": 50}, {"type": "null"}],
      "description": "转账备注（可选），最多 50 字",
      "default": null
    }
  },
  "required": ["to_account", "amount"],
  "$defs": {
    "Currency": {
      "enum": ["CNY", "USD", "EUR"],
      "title": "Currency",
      "type": "string"
    }
  }
}
```

**Pydantic 的优势**：

| 维度 | 手写 JSON Schema | Pydantic 自动生成 |
|---|---|---|
| 类型安全 | 无——写错类型运行时才发现 | 有——IDE 提示 + 类型检查 |
| 校验能力 | 需要单独写 jsonschema.validate | `TransferInput(**args)` 一行完成 |
| 维护成本 | 改字段要同步改 Schema 和代码 | 改模型自动更新 Schema |
| 默认值 | Schema 里写了但代码不一定一致 | Pydantic `default=` 即代码默认值 |
| 文档化 | description 容易遗漏 | Field(description=) 强制填写 |

**⚠️ 注意**：Pydantic v2 生成的 Schema 可能包含 `$ref` / `$defs`（如上例的 Currency），部分 Function Calling API 不支持。需要展平：

```python
def flatten_schema(schema: dict) -> dict:
    """将 $ref 展平为内联定义，兼容 Function Calling API"""
    defs = schema.pop("$defs", {})
    
    def resolve(obj):
        if isinstance(obj, dict):
            if "$ref" in obj:
                ref_path = obj["$ref"].split("/")[-1]
                resolved = defs.get(ref_path, {})
                merged = {k: v for k, v in obj.items() if k != "$ref"}
                resolved.update(merged)
                return resolved
            return {k: resolve(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [resolve(v) for v in obj]
        return obj
    
    return resolve(schema)
```

### 3.4 Input Schema 校验的分层模型

```text
┌─────────────────────────────────────────────────────────┐
│ 第 0 层：API 层                                          │
│ 模型生成 arguments → API 返回 tool_calls                  │
│ 这一层没有任何校验，模型想生成什么就生成什么                 │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 第 1 层：JSON Schema 校验（结构层）                       │
│ 类型、必填、枚举、范围、格式、模式                          │
│ jsonschema.validate(arguments, input_schema)             │
│ 速度快、无副作用、100% 自动化                              │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 第 2 层：业务规则校验（上下文层）                           │
│ 额度、权限、时间约束、用户状态                              │
│ 需要用户上下文 + 配置/数据库                               │
│ 不能自动化——规则随业务变化                                 │
└──────────────────────┬──────────────────────────────────┘
                       ▼
┌─────────────────────────────────────────────────────────┐
│ 第 3 层：运行时校验（数据层）                              │
│ 账户是否存在、库存是否足够、文件是否存在                     │
│ 需要实时查询外部系统                                      │
│ 有副作用（网络、数据库）——按需执行，非每次必跑               │
└─────────────────────────────────────────────────────────┘
```

每层的校验代码：

```python
import jsonschema
from dataclasses import dataclass

@dataclass
class UserContext:
    user_id: str
    account_id: str
    role: str

# ── 第 1 层：JSON Schema 校验 ──

def validate_schema(tool_name: str, arguments: dict) -> None:
    """结构层校验——自动、无副作用、快速"""
    schema = TOOL_INPUT_SCHEMAS.get(tool_name)
    if not schema:
        return
    try:
        jsonschema.validate(arguments, schema)
    except jsonschema.ValidationError as e:
        raise ToolInputError(
            code="SCHEMA_VIOLATION",
            message=f"参数不符合 Schema: {e.message}",
            path=list(e.absolute_path),
            retryable=True,   # 模型可能换个值重试
            suggestion=f"检查 {e.json_path} 的值",
        )

# ── 第 2 层：业务规则校验 ──

def validate_business(tool_name: str, arguments: dict, ctx: UserContext) -> None:
    """上下文层校验——需要用户上下文，无外部副作用"""
    if tool_name == "transfer_money":
        # 每日限额
        today_total = get_today_total(ctx.user_id)  # 可缓存
        if today_total + arguments["amount"] > 100000:
            raise ToolInputError(
                code="DAILY_LIMIT_EXCEEDED",
                message=f"今日已转 {today_total} 元，额度剩余 {100000 - today_total} 元",
                retryable=False,  # 换参数也没用
                suggestion="减少金额或明日再转",
            )

        # 非工作时间大额限制
        if arguments["amount"] > 10000 and not is_business_hours():
            raise ToolInputError(
                code="OFF_HOURS_LARGE_TRANSFER",
                message="非工作时间不支持 1 万元以上转账",
                retryable=True,   # 等到工作时间重试
                suggestion="在工作时间（9:00-17:00）重试",
            )

# ── 第 3 层：运行时校验 ──

def validate_runtime(tool_name: str, arguments: dict, ctx: UserContext) -> None:
    """数据层校验——有外部副作用（网络/数据库），按需执行"""
    if tool_name == "transfer_money":
        # 账户是否存在
        if not check_account_exists(arguments["to_account"]):  # 数据库查询
            raise ToolInputError(
                code="ACCOUNT_NOT_FOUND",
                message=f"账户 {arguments['to_account']} 不存在",
                retryable=False,
                suggestion="请用户确认账户号",
            )

        # 余额是否足够
        balance = get_balance(ctx.account_id)  # 数据库查询
        if arguments["amount"] > balance:
            raise ToolInputError(
                code="INSUFFICIENT_BALANCE",
                message=f"余额 {balance} 元，不足 {arguments['amount']} 元",
                retryable=True,
                suggestion="减少金额或先充值",
            )

# ── 组合校验 ──

def validate_tool_input(tool_name: str, arguments: dict, ctx: UserContext) -> dict:
    """按层依次校验——早失败，省资源"""
    validate_schema(tool_name, arguments)           # 第 1 层：最快，无副作用
    validate_business(tool_name, arguments, ctx)     # 第 2 层：需上下文，无外部调用
    validate_runtime(tool_name, arguments, ctx)      # 第 3 层：有副作用，最后执行
    return arguments
```

**为什么要分层？**

- 第 1 层不过 → 没必要跑第 2、3 层（省资源）
- 第 2 层不过 → 没必要查数据库（省 I/O）
- 层级越深，成本越高，越要放到最后

### 3.5 校验失败后怎么办

校验失败不是终点——模型需要知道**为什么失败**和**该怎么办**。

```python
class ToolInputError(Exception):
    """统一的输入校验错误，携带 Error Schema 信息"""
    def __init__(self, code: str, message: str, retryable: bool,
                 suggestion: str = "", path: list = None):
        self.code = code
        self.message = message
        self.retryable = retryable
        self.suggestion = suggestion
        self.path = path or []

    def to_tool_result(self, tool_call_id: str) -> dict:
        """转换为 tool_result 消息——模型能看到错误信息"""
        return {
            "role": "tool",
            "tool_call_id": tool_call_id,
            "content": json.dumps({
                "error_code": self.code,
                "message": self.message,
                "retryable": self.retryable,
                "suggestion": self.suggestion,
                "invalid_path": ".".join(str(p) for p in self.path) if self.path else None,
            }, ensure_ascii=False),
        }
```

**关键**：校验失败时，不是简单地抛异常或返回空，而是把错误信息作为 `tool_result` 回传给模型。模型看到 `retryable: true` + `suggestion` 后，可能会自动修正参数重试。

```text
[turn 1] 用户: "转账 50000 美元到 6222...1234"
[turn 2] 模型:   tool_calls: [{name: "transfer_money", args: {to_account: "6222...1234", amount: 50000, currency: "USD"}}]
[turn 3] Runtime: 校验失败 → tool_result: {error_code: "DAILY_LIMIT_EXCEEDED", retryable: false, suggestion: "减少金额或明日再转"}
[turn 4] 模型:   "抱歉，您今天的转账额度已用完，无法再转 50000 美元。建议您明天再操作，或减少金额。"
```

如果校验错误只是抛异常不回传模型，模型会在下一轮再次尝试同样的参数，陷入死循环。

---

## 四、Output Schema 设计

### 4.1 为什么需要 Output Schema

API 的 `tool_result.content` 是自由格式的字符串。但工具返回值的格式直接影响模型的理解准确度。

**对比实验**：

```python
# ❌ 自然语言返回——模型需要 NLU 来提取结构
def get_weather(city):
    return "北京今天天气晴，气温5摄氏度，北风3级，湿度45%，空气质量指数82"
# 模型需要理解这段话才能回答"北京冷吗？""需要带口罩吗？""风大吗？"

# ✅ 结构化返回——模型直接读字段
def get_weather(city):
    return {
        "city": "北京",
        "temperature": {"value": 5, "unit": "celsius"},
        "condition": "晴",
        "wind": {"speed_kmh": 15, "direction": "北", "level": 3},
        "humidity_pct": 45,
        "aqi": 82,
        "aqi_level": "良",
    }
# 模型直接看 temperature.value=5 判断冷不冷，看 aqi=82 判断空气质量
```

结构化返回的模型准确率显著高于自然语言返回，尤其在：
- 数值比较（"温度低于 10 度的城市"）
- 多条件筛选（"有雨且温度低于 15 度"）
- 信息提取（"风速是多少"）

### 4.2 Output Schema 设计原则

**原则 1：原子化数值——把数值和单位分开**

```python
# ❌ 数值和单位耦合——模型无法做数值比较
"temperature": "5°C"

# ✅ 数值和单位分离——模型可以直接比较
"temperature": {"value": 5, "unit": "celsius"}
```

**原则 2：预计算衍生信息——帮模型省一步推理**

```python
# ❌ 只给原始数据——模型要自己算
"aqi": 82

# ✅ 同时给衍生标签——模型直接用
"aqi": 82,
"aqi_level": "良",       # 0-50 优 / 51-100 良 / 101-150 轻度污染 ...
```

**原则 3：列表型结果带总数和分页信息**

```python
# ❌ 只返回列表——模型不知道还有多少
"products": [{"name": "iPhone 15", "price": 7999}, ...]

# ✅ 带元信息——模型知道全貌
"total_count": 156,
"page": 1,
"page_size": 10,
"products": [{"name": "iPhone 15", "price": 7999}, ...],
"has_more": True
```

**原则 4：包含足够的上下文，避免模型二次追问**

```python
# ❌ 只返回订单状态——用户不知道"已发货"意味着什么
"status": "shipped"

# ✅ 带解释和时间线
"status": "shipped",
"status_description": "已发货，预计3天内送达",
"timeline": [
    {"time": "2024-01-10 09:00", "event": "订单创建"},
    {"time": "2024-01-10 10:30", "event": "付款成功"},
    {"time": "2024-01-11 14:00", "event": "已发货"},
]
```

### 4.3 Output Schema 定义方式

Output Schema 不在 Function Calling API 中声明（API 只认 Input Schema），它是**工程约定**，定义方式有三种：

**方式 1：Pydantic 模型（推荐——类型安全 + 自动校验）**

```python
class WeatherOutput(BaseModel):
    """天气查询输出"""
    city: str = Field(description="城市名")
    temperature: TemperatureInfo = Field(description="温度信息")
    condition: str = Field(description="天气状况：晴/阴/雨/雪")
    humidity_pct: float = Field(ge=0, le=100, description="湿度百分比")
    aqi: int = Field(ge=0, description="空气质量指数")
    aqi_level: str = Field(description="空气质量等级")

class TemperatureInfo(BaseModel):
    value: float = Field(description="温度数值")
    unit: str = Field(description="温度单位", enum=["celsius", "fahrenheit"])

# 工具实现时用 Pydantic 保证返回结构
def get_weather(city: str) -> dict:
    raw = fetch_weather_data(city)
    output = WeatherOutput(
        city=city,
        temperature=TemperatureInfo(value=raw["temp"], unit="celsius"),
        condition=raw["condition"],
        humidity_pct=raw["humidity"],
        aqi=raw["aqi"],
        aqi_level=classify_aqi(raw["aqi"]),
    )
    return output.model_dump()  # 序列化为 dict → json.dumps → tool_result.content
```

**方式 2：JSON Schema 文档（用于文档和跨语言协作）**

```python
WEATHER_OUTPUT_SCHEMA = {
    "type": "object",
    "properties": {
        "city":         {"type": "string", "description": "城市名"},
        "temperature":  {
            "type": "object",
            "properties": {
                "value": {"type": "number"},
                "unit":  {"type": "string", "enum": ["celsius", "fahrenheit"]}
            }
        },
        "condition":    {"type": "string"},
        "humidity_pct": {"type": "number", "minimum": 0, "maximum": 100},
        "aqi":          {"type": "integer", "minimum": 0},
        "aqi_level":    {"type": "string"},
    }
}
```

**方式 3：TypedDict + 运行时校验（轻量级）**

```python
from typing import TypedDict, List

class WeatherOutput(TypedDict):
    city: str
    temperature: dict   # {"value": float, "unit": str}
    condition: str
    humidity_pct: float
    aqi: int
    aqi_level: str

# 运行时用 jsonschema 校验
def validate_output(tool_name: str, output: dict) -> dict:
    schema = TOOL_OUTPUT_SCHEMAS.get(tool_name)
    if schema:
        jsonschema.validate(output, schema)
    return output
```

### 4.4 Output Schema 校验的意义

你可能会问：工具是我自己写的，返回值我能控制，为什么还要校验 Output？

原因：
1. **工具可能调用外部服务**——外部服务的返回格式可能变化
2. **工具可能被多人维护**——Schema 是团队契约
3. **调试**——Output 校验失败 = 工具有 bug，比模型行为异常更容易定位

```python
def get_weather(city: str) -> dict:
    raw = call_weather_api(city)          # 外部 API，格式可能变
    output = normalize_weather(raw)       # 我们的标准化逻辑
    validate_output("get_weather", output)  # 校验——早发现格式漂移
    return output
```

---

## 五、Error Schema 设计

### 5.1 为什么需要 Error Schema

工具执行有三种结果：成功、可恢复错误、不可恢复错误。没有 Error Schema 时，模型只能靠自然语言理解错误，无法做出正确的重试/放弃决策。

```text
模型收到 tool_result: "网络超时"
→ 这能重试吗？模型不确定 → 可能直接告诉用户"服务不可用" → 用户体验差

模型收到 tool_result: {"error_code": "TIMEOUT", "retryable": true, "suggestion": "3秒后重试"}
→ 模型知道能重试 → 自动重试 → 用户无感知
```

### 5.2 Error Schema 的最小字段

```python
ERROR_SCHEMA = {
    "type": "object",
    "properties": {
        "error_code":    {"type": "string",  "description": "机器可读的错误码"},
        "message":       {"type": "string",  "description": "人可读的错误描述"},
        "retryable":     {"type": "boolean", "description": "是否建议重试"},
        "suggestion":    {"type": "string",  "description": "给模型的具体建议"},
    },
    "required": ["error_code", "message", "retryable"]
}
```

每个字段的用途：

| 字段 | 消费者 | 用途 |
|---|---|---|
| `error_code` | Runtime / 监控 | 分类统计、告警、去重 |
| `message` | 模型 / 用户 | 理解发生了什么 |
| `retryable` | 模型 / Runtime | 决策是否重试 |
| `suggestion` | 模型 | 给出具体行动建议 |

### 5.3 错误分类

按**可恢复性**分类：

```python
# ── 不可恢复错误（retryable=False）──
# 含义：无论重试多少次，同样的参数都会失败
# 模型应该：告知用户，或换一种方式

ACCOUNT_NOT_FOUND    # 账户不存在——换账号
INVALID_INPUT        # 参数格式错误——换参数
PERMISSION_DENIED    # 无权限——不可能通过重试获得权限
CITY_NOT_SUPPORTED   # 不支持该城市——换城市
DAILY_LIMIT_EXCEEDED # 超出限额——明天再来

# ── 可恢复错误（retryable=True）──
# 含义：稍后重试可能成功，或调整参数后可能成功
# 模型应该：等待后重试，或按 suggestion 调整

TIMEOUT              # 超时——网络可能恢复
SERVICE_UNAVAILABLE  # 服务不可用——可能恢复
RATE_LIMITED         # 限流——等几秒重试
INSUFFICIENT_BALANCE # 余额不足——减少金额后重试
CONCURRENT_CONFLICT  # 并发冲突——重试可能成功
```

按**错误来源**分类：

```python
# ── 模型侧错误（模型生成的参数有问题）──
SCHEMA_VIOLATION     # 不符合 Input Schema → 模型换参数
INVALID_INPUT        # 业务规则不满足       → 模型按 suggestion 调整

# ── Runtime 侧错误（工具执行环境有问题）──
TIMEOUT              # 工具执行超时         → 等待后重试
SERVICE_UNAVAILABLE  # 下游服务不可用       → 等待后重试
RATE_LIMITED         # 被限流               → 退避后重试

# ── 工具侧错误（工具逻辑正常但业务条件不满足）──
ACCOUNT_NOT_FOUND    # 目标不存在           → 告知用户
INSUFFICIENT_BALANCE # 资源不足             → 减少数量或告知用户
```

**为什么要区分来源？**

- 模型侧错误 → 模型可以自己修正（换参数）
- Runtime 侧错误 → 模型只能等待重试
- 工具侧错误 → 模型应该告知用户，让用户决策

### 5.4 错误码设计规范

```python
# 命名规范：SCREAMING_SNAKE_CASE
# 格式：<来源>_<描述>
# 原则：机器可匹配，人可理解

ERROR_CODES = {
    # ── 通用 ──
    "INTERNAL_ERROR":          {"retryable": True,  "http_equiv": 500},
    "TIMEOUT":                 {"retryable": True,  "http_equiv": 408},
    "SERVICE_UNAVAILABLE":     {"retryable": True,  "http_equiv": 503},
    "RATE_LIMITED":            {"retryable": True,  "http_equiv": 429},

    # ── 输入校验 ──
    "SCHEMA_VIOLATION":        {"retryable": True,  "http_equiv": 400},
    "INVALID_INPUT":           {"retryable": True,  "http_equiv": 400},
    "PERMISSION_DENIED":       {"retryable": False, "http_equiv": 403},

    # ── 业务 ──
    "ACCOUNT_NOT_FOUND":       {"retryable": False, "http_equiv": 404},
    "INSUFFICIENT_BALANCE":    {"retryable": True,  "http_equiv": 409},
    "DAILY_LIMIT_EXCEEDED":    {"retryable": False, "http_equiv": 429},
    "CONCURRENT_CONFLICT":     {"retryable": True,  "http_equiv": 409},
}
```

### 5.5 Error Schema 与重试策略的配合

```python
import asyncio
from tenacity import (
    retry, stop_after_attempt, wait_exponential,
    retry_if_exception, retry_any,
)

class ToolError(Exception):
    def __init__(self, code: str, message: str, retryable: bool, suggestion: str = ""):
        self.code = code
        self.message = message
        self.retryable = retryable
        self.suggestion = suggestion

def is_retryable_error(exc: ToolError) -> bool:
    """只重试可恢复错误"""
    return exc.retryable

def is_rate_limited(exc: ToolError) -> bool:
    """限流错误用更长退避"""
    return exc.code == "RATE_LIMITED"

# 通用重试策略
@retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, max=10),
    retry=retry_if_exception(is_retryable_error),
)
def execute_with_retry(tool_name: str, args: dict) -> dict:
    result = dispatch_tool(tool_name, args)
    if isinstance(result, dict) and "error_code" in result:
        err = ToolError(
            result["error_code"],
            result["message"],
            result.get("retryable", False),
            result.get("suggestion", ""),
        )
        if err.retryable:
            raise err  # 触发 tenacity 重试
        return result   # 不可重试，直接返回给模型
    return result

# 限流专用重试——更长退避
@retry(
    stop=stop_after_attempt(5),
    wait=wait_exponential(multiplier=2, max=60),
    retry=retry_if_exception(is_rate_limited),
)
def execute_rate_limited(tool_name: str, args: dict) -> dict:
    ...
```

---

## 六、三个 Schema 的协作

### 6.1 端到端数据流

```text
                        Input Schema
                       ┌────────────┐
  用户请求 → 模型选工具 → 生成 arguments │
                       └─────┬──────┘
                             │
                    ┌────────▼────────┐
                    │  Runtime 校验    │
                    │  第1层: Schema   │
                    │  第2层: 业务     │
                    │  第3层: 运行时   │
                    └────┬───────┬────┘
                         │       │
                    校验通过   校验失败
                         │       │
              ┌──────────▼┐  ┌──▼───────────┐
              │  执行工具   │  │ Error Schema │
              └──────┬─────┘  │ 生成错误结果  │
                     │        └──────┬───────┘
              ┌──────▼──────┐       │
              │ Output Schema│      │
              │ 结构化返回   │      │
              └──────┬──────┘      │
                     │              │
                     ▼              ▼
              ┌──────────────────────────┐
              │  tool_result 回传给模型    │
              │  模型决定：最终回答 /      │
              │  继续调工具 / 重试         │
              └──────────────────────────┘
```

### 6.2 Contract-First 开发模式

传统方式：先写工具代码，后补 Schema（Schema 经常和代码不一致）。

推荐方式：**先定义 Schema，再写实现**。

```python
# ── 第 1 步：定义三个 Schema ──

class TransferInput(BaseModel):
    to_account: str = Field(pattern=r"^\d{10,20}$", description="目标账户号")
    amount: float = Field(gt=0, le=50000, description="转账金额")

class TransferOutput(BaseModel):
    transaction_id: str = Field(description="交易流水号")
    amount: float = Field(description="实际转账金额")
    status: str = Field(description="状态", enum=["success", "pending"])

class TransferError(BaseModel):
    error_code: str = Field(description="错误码")
    message: str = Field(description="错误信息")
    retryable: bool = Field(description="是否可重试")
    suggestion: str = Field(default="", description="建议")

# ── 第 2 步：注册工具时用 Schema 生成 API 参数 ──

TRANSFER_TOOL = {
    "type": "function",
    "function": {
        "name": "transfer_money",
        "description": "从用户账户向目标账户转账",
        "parameters": flatten_schema(TransferInput.model_json_schema()),
    }
}

# ── 第 3 步：实现工具时用 Schema 保证返回结构 ──

def transfer_money(to_account: str, amount: float) -> dict:
    # Input 校验——Pydantic 自动做
    inp = TransferInput(to_account=to_account, amount=amount)

    try:
        # 业务逻辑
        tx_id = do_transfer(inp.to_account, inp.amount)

        # Output 校验——Pydantic 保证结构
        out = TransferOutput(transaction_id=tx_id, amount=inp.amount, status="success")
        return out.model_dump()

    except AccountNotFoundError:
        err = TransferError(
            error_code="ACCOUNT_NOT_FOUND",
            message=f"账户 {inp.to_account} 不存在",
            retryable=False,
            suggestion="请确认目标账户号",
        )
        return err.model_dump()

    except InsufficientBalanceError as e:
        err = TransferError(
            error_code="INSUFFICIENT_BALANCE",
            message=f"余额不足，当前余额 {e.balance} 元",
            retryable=True,
            suggestion=f"减少金额至 {e.balance} 元以下",
        )
        return err.model_dump()
```

**好处**：Schema 和代码永远一致——改 Schema 会导致 Pydantic 校验失败，改代码会导致 Schema 不匹配。任何不一致都在开发阶段暴露，不会到生产环境才发现。

### 6.3 Schema 版本演进

工具的 Schema 会随业务变化。如何安全演进？

```text
兼容性规则：
  加可选字段 → ✅ 兼容（模型可以不传）
  加必填字段 → ❌ 不兼容（旧模型不知道要传）
  删字段     → ❌ 不兼容（旧模型还在传）
  改枚举值   → ⚠️ 可能不兼容（加值兼容，删值不兼容）
  改类型     → ❌ 不兼容
```

```python
# ✅ 安全演进：加可选字段
# v1
class TransferInputV1(BaseModel):
    to_account: str
    amount: float

# v2 — 加了可选的 currency 和 note，旧调用不受影响
class TransferInputV2(BaseModel):
    to_account: str
    amount: float
    currency: str = "CNY"          # 新增可选
    note: Optional[str] = None     # 新增可选

# ❌ 不安全演进：加必填字段
class TransferInputV3(BaseModel):
    to_account: str
    amount: float
    currency: str                   # 新增必填！旧模型不知道要传
    verification_code: str          # 新增必填！旧模型不知道要传
```

如果必须加必填字段，使用**版本化工具名**：

```python
TOOLS = [
    {"function": {"name": "transfer_money_v1", ...}},  # 旧版
    {"function": {"name": "transfer_money_v2", ...}},  # 新版
]
# 逐步迁移模型到 v2，确认稳定后下线 v1
```

---

## 七、Schema 体系与现有项目的关系

| 本文档概念 | 现有项目中的对应 |
|---|---|
| Input Schema (JSON Schema) | `tool_schemas.py` 的 Pydantic `Field` + `schema_extra` |
| Input Schema (校验) | `P19-纵深防御体系.py` 的 `InputSanitizer`（第 2 层——安全模式校验） |
| Output Schema | `p36-tool.md` 的 `@tool` 装饰器自动从返回类型推断 |
| Error Schema | `tool-use-and-tool-result.md` 的 `is_error` 标志 + `mapToolResultToToolResultBlockParam` |
| 权限分级 | `tool-resolution-and-permission-isolation.md` 的 `toolPermissionContext` |
| Pydantic 自动生成 | `tool_schemas.py` 的 `WeatherQuery` / `NewsSearch`（但缺少校验和 Error Schema） |

**现有项目需要补充的**：

1. `tool_schemas.py` 只有 Input（Pydantic 模型），没有 Output 和 Error Schema
2. `InputSanitizer` 只做安全模式匹配，没有 JSON Schema 层的结构校验
3. 工具调用没有统一的 Error Schema——错误信息是自由格式的字符串
4. 缺少 `validate_tool_input()` → `execute_tool()` → `validate_tool_output()` 的标准化流水线
