# Langchain

**目录**

1. [LangChain 概述](#1-langchain-概述)
2. [快速开始](#2-快速开始)
3. [快速入门](#3-快速入门)
4. [智能体 (Agents)](#4-智能体-agents)
5. [模型 (Models)](#5-模型-models)
6. [消息 (Messages)](#6-消息-messages)
7. [工具 (Tools)](#7-工具-tools)
8. [短期记忆 (Short-term Memory)](#8-短期记忆-short-term-memory)
9. [流式传输 (Streaming)](#9-流式传输-streaming)
10. [结构化输出 (Structured Output)](#10-结构化输出-structured-output)
11. [中间件 (Middleware)](#11-中间件-middleware)
12. [运行时 (Runtime)](#12-运行时-runtime)
13. [上下文工程 (Context Engineering)](#13-上下文工程-context-engineering)
14. [人工介入 (Human-in-the-loop)](#14-人工介入-human-in-the-loop)
15. [长期记忆 (Long-term Memory)](#15-长期记忆-long-term-memory)

---

## 1. LangChain 概述

LangChain 是一个开源框架，它拥有预构建的智能体架构，并且能够与任何模型或工具集成，因此你可以构建出能像生态系统一样快速进化的智能体。

LangChain是开始构建由大语言模型（LLMs）驱动的完全自定义智能体和应用程序的简便方法。仅用不到10行代码，你就可以连接到OpenAI、Anthropic、谷歌以及更多平台。LangChain提供了预制的智能体架构和模型集成，帮助你快速上手，并将大语言模型无缝整合到你的智能体和应用程序中。

## 2. 快速开始

### 安装

```bash
pip install -qU langchain "langchain[anthropic]"
```

### 基础示例

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

# Run the agent
agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)
```

## 3. 快速入门

本快速入门指南将在短短几分钟内带您从简单设置过渡到功能完备的AI智能体。

### LangChain文档MCP服务器

如果你正在使用AI编码助手或集成开发环境（例如Claude Code或Cursor），你应该安装LangChain Docs MCP服务器以充分发挥其作用。这能确保你的智能体可以访问最新的LangChain文档和示例。

### 要求

对于这些示例，你需要：

1. 安装LangChain包
2. 创建一个Claude（Anthropic）账户并获取API密钥
3. 在终端中设置`ANTHROPIC_API_KEY`环境变量

> 虽然这些示例使用了Claude，但你可以通过更改代码中的模型名称并设置相应的API密钥来使用任何受支持的模型。

### 构建一个基础智能体

首先创建一个能够回答问题和调用工具的简单智能体。该智能体将使用Claude Sonnet 4.5作为其语言模型，一个基本的天气函数作为工具，以及一个简单的提示词来指导其行为。

```python
from langchain.agents import create_agent

def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_weather],
    system_prompt="You are a helpful assistant",
)

# Run the agent
agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather in sf"}]}
)
```

> 要了解如何使用LangSmith跟踪你的智能体，请参阅LangSmith文档。

### 构建一个真实世界的智能体

接下来，构建一个实用的天气预报智能体，以展示关键的生产概念：

- 详细的系统提示以获得更好的代理行为
- 创建与外部数据集成的工具
- 模型配置以获得一致的响应
- 结构化输出以获得可预测的结果
- 对话记忆，用于类聊天互动

让我们逐步了解每一步：

#### 1. 定义系统提示

系统提示定义了您的代理的角色和行为。保持它的具体和可操作：

```python
SYSTEM_PROMPT = """You are an expert weather forecaster, who speaks in puns.

You have access to two tools:

- get_weather_for_location: use this to get the weather for a specific location
- get_user_location: use this to get the user's location

If a user asks you for the weather, make sure you know the location. If you can tell from the question that they mean wherever they are, use the get_user_location tool to find their location."""
```

#### 2. 创建工具

工具允许模型通过调用你定义的函数与外部系统交互。工具可以依赖运行时上下文，也可以与智能体内存进行交互。

请注意下面的`get_user_location`工具是如何使用运行时上下文的：

```python
from dataclasses import dataclass
from langchain.tools import tool, ToolRuntime

@tool
def get_weather_for_location(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

@dataclass
class Context:
    """Custom runtime context schema."""
    user_id: str

@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Retrieve user information based on user ID."""
    user_id = runtime.context.user_id
    return "Florida" if user_id == "1" else "SF"
```

> 工具应当有完善的文档说明：它们的名称、描述和参数名称会成为模型提示词的一部分。LangChain的`@tool`会添加元数据，并支持通过`ToolRuntime`参数进行运行时注入。

#### 3. 配置您的模型

为你的使用场景设置具有正确参数的语言模型：

```python
from langchain.chat_models import init_chat_model

model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    temperature=0.5,
    timeout=10,
    max_tokens=1000
)
```

> 根据所选的模型和提供商，初始化参数可能会有所不同；详情请参考它们的参考页面。

#### 4. 定义响应格式

如果需要智能体的响应符合特定模式，您可以选择性地定义结构化的响应格式。

```python
from dataclasses import dataclass

# We use a dataclass here, but Pydantic models are also supported.
@dataclass
class ResponseFormat:
    """Response schema for the agent."""
    # A punny response (always required)
    punny_response: str
    # Any interesting information about the weather if available
    weather_conditions: str | None = None
```

#### 5. 添加内存

为你的智能体添加记忆，使其能在交互过程中保持状态。这能让智能体记住之前的对话和上下文。

```python
from langgraph.checkpoint.memory import InMemorySaver

checkpointer = InMemorySaver()
```

> 在生产环境中，请使用持久化检查点将消息历史保存到数据库。有关更多详细信息，请参阅添加和管理内存。

#### 6. 创建并运行智能体

现在将所有组件组装到你的智能体中并运行它！

```python
from langchain.agents.structured_output import ToolStrategy

agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_user_location, get_weather_for_location],
    context_schema=Context,
    response_format=ToolStrategy(ResponseFormat),
    checkpointer=checkpointer
)

# `thread_id` is a unique identifier for a given conversation.
config = {"configurable": {"thread_id": "1"}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather outside?"}]},
    config=config,
    context=Context(user_id="1")
)

print(response['structured_response'])
# ResponseFormat(
#     punny_response="Florida is still having a 'sun-derful' day! The sunshine is playing 'ray-dio' hits all day long! I'd say it's the perfect weather for some 'solar-bration'! If you were hoping for rain, I'm afraid that idea is all 'washed up' - the forecast remains 'clear-ly' brilliant!",
#     weather_conditions="It's always sunny in Florida!"
# )

# Note that we can continue the conversation using the same `thread_id`.
response = agent.invoke(
    {"messages": [{"role": "user", "content": "thank you!"}]},
    config=config,
    context=Context(user_id="1")
)

print(response['structured_response'])
# ResponseFormat(
#     punny_response="You're 'thund-erfully' welcome! It's always a 'breeze' to help you stay 'current' with the weather. I'm just 'cloud'-ing around waiting to 'shower' you with more forecasts whenever you need them. Have a 'sun-sational' day in the Florida sunshine!",
#     weather_conditions=None
# )
```

### 完整示例代码

```python
from dataclasses import dataclass

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.tools import tool, ToolRuntime
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents.structured_output import ToolStrategy


# Define system prompt
SYSTEM_PROMPT = """You are an expert weather forecaster, who speaks in puns.

You have access to two tools:

- get_weather_for_location: use this to get the weather for a specific location
- get_user_location: use this to get the user's location

If a user asks you for the weather, make sure you know the location. If you can tell from the question that they mean wherever they are, use the get_user_location tool to find their location."""

# Define context schema
@dataclass
class Context:
    """Custom runtime context schema."""
    user_id: str

# Define tools
@tool
def get_weather_for_location(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

@tool
def get_user_location(runtime: ToolRuntime[Context]) -> str:
    """Retrieve user information based on user ID."""
    user_id = runtime.context.user_id
    return "Florida" if user_id == "1" else "SF"

# Configure model
model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    temperature=0
)

# Define response format
@dataclass
class ResponseFormat:
    """Response schema for the agent."""
    # A punny response (always required)
    punny_response: str
    # Any interesting information about the weather if available
    weather_conditions: str | None = None

# Set up memory
checkpointer = InMemorySaver()

# Create agent
agent = create_agent(
    model=model,
    system_prompt=SYSTEM_PROMPT,
    tools=[get_user_location, get_weather_for_location],
    context_schema=Context,
    response_format=ToolStrategy(ResponseFormat),
    checkpointer=checkpointer
)

# Run agent
# `thread_id` is a unique identifier for a given conversation.
config = {"configurable": {"thread_id": "1"}}

response = agent.invoke(
    {"messages": [{"role": "user", "content": "what is the weather outside?"}]},
    config=config,
    context=Context(user_id="1")
)

print(response['structured_response'])
# ResponseFormat(
#     punny_response="Florida is still having a 'sun-derful' day! The sunshine is playing 'ray-dio' hits all day long! I'd say it's the perfect weather for some 'solar-bration'! If you were hoping for rain, I'm afraid that idea is all 'washed up' - the forecast remains 'clear-ly' brilliant!",
#     weather_conditions="It's always sunny in Florida!"
# )

# Note that we can continue the conversation using the same `thread_id`.
response = agent.invoke(
    {"messages": [{"role": "user", "content": "thank you!"}]},
    config=config,
    context=Context(user_id="1")
)

print(response['structured_response'])
# ResponseFormat(
#     punny_response="You're 'thund-erfully' welcome! It's always a 'breeze' to help you stay 'current' with the weather. I'm just 'cloud'-ing around waiting to 'shower' you with more forecasts whenever you need them. Have a 'sun-sational' day in the Florida sunshine!",
#     weather_conditions=None
# )
```

### 总结

恭喜！您现在拥有一个可以：

- 理解语境并记住对话
- 智能使用多种工具
- 提供结构化的回应，格式保持一致
- 通过上下文处理用户特定信息
- 在交互过程中保持对话状态

## 4. 智能体 (Agents)

智能体将语言模型与工具相结合，创建出能够对任务进行推理、决定使用哪些工具并迭代地朝着解决方案努力的系统。

`create_agent`提供了可用于生产环境的智能体实现。

### 智能体工作原理

大型语言模型智能体通过循环运行工具来实现目标。智能体会一直运行，直到满足停止条件——即模型输出最终结果或达到迭代次数限制。

`create_agent`使用LangGraph构建基于图的智能体运行时。图由节点（步骤）和边（连接）组成，这些节点和边定义了智能体处理信息的方式。智能体会在该图中移动，执行诸如模型节点（用于调用模型）、工具节点（用于执行工具）或中间件之类的节点。

### 核心组件

#### 模型 (Model)

模型是智能体的推理引擎。它可以通过多种方式指定，支持静态和动态模型选择。

##### 静态模型

静态模型在创建智能体时配置一次，并且在整个执行过程中保持不变。这是最常见且最简单直接的方法。

从一个模型标识符字符串初始化静态模型：

```python
from langchain.agents import create_agent

agent = create_agent("openai:gpt-5", tools=tools)
```

> 模型标识符字符串支持自动推断（例如，"gpt-5" 将被推断为 "openai:gpt-5"）。

如需更好地控制模型配置，请直接使用提供程序包初始化模型实例：

```python
from langchain.agents import create_agent
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-5",
    temperature=0.1,
    max_tokens=1000,
    timeout=30
    # ... (other params)
)
agent = create_agent(model, tools=tools)
```

##### 动态模型

动态模型在运行时基于当前状态和上下文进行选择。这实现了复杂的路由逻辑和成本优化。

要使用动态模型，请使用`@wrap_model_call`装饰器创建中间件：

```python
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse


basic_model = ChatOpenAI(model="gpt-4.1-mini")
advanced_model = ChatOpenAI(model="gpt-4.1")

@wrap_model_call
def dynamic_model_selection(request: ModelRequest, handler) -> ModelResponse:
    """Choose model based on conversation complexity."""
    message_count = len(request.state["messages"])

    if message_count > 10:
        # Use an advanced model for longer conversations
        model = advanced_model
    else:
        model = basic_model

    return handler(request.override(model=model))

agent = create_agent(
    model=basic_model,  # Default model
    tools=tools,
    middleware=[dynamic_model_selection]
)
```

> 使用结构化输出时，不支持预绑定模型（已调用bind_tools的模型）。

#### 工具 (Tools)

工具赋予智能体采取行动的能力。智能体超越了单纯的模型工具绑定，其作用在于：

- （由单个提示触发的）多工具连续调用
- 在适当的时候进行并行工具调用
- 基于先前结果的动态工具选择
- 工具重试逻辑与错误处理
- 工具调用间的状态持久性

##### 静态工具

静态工具在创建智能体时就已定义，并且在整个执行过程中保持不变。

```python
from langchain.tools import tool
from langchain.agents import create_agent


@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

@tool
def get_weather(location: str) -> str:
    """Get weather information for a location."""
    return f"Weather in {location}: Sunny, 72°F"

agent = create_agent(model, tools=[search, get_weather])
```

> 如果提供的工具列表为空，智能体将由单个LLM节点组成，且不具备工具调用能力。

##### 动态工具

借助动态工具，智能体可用的工具集是在运行时修改的，而非预先全部定义好。并非每种工具都适用于所有情况。工具过多可能会让模型不堪重负（上下文过载）并增加错误；工具过少则会限制功能。

当工具在运行时被发现或创建时（例如从MCP服务器加载、基于用户数据生成或从远程注册表获取），需要同时注册工具并动态处理其执行：

```python
from langchain.tools import tool
from langchain.agents import create_agent
from langchain.agents.middleware import AgentMiddleware, ModelRequest, ToolCallRequest

# A tool that will be added dynamically at runtime
@tool
def calculate_tip(bill_amount: float, tip_percentage: float = 20.0) -> str:
    """Calculate the tip amount for a bill."""
    tip = bill_amount * (tip_percentage / 100)
    return f"Tip: ${tip:.2f}, Total: ${bill_amount + tip:.2f}"

class DynamicToolMiddleware(AgentMiddleware):
    """Middleware that registers and handles dynamic tools."""

    def wrap_model_call(self, request: ModelRequest, handler):
        # Add dynamic tool to the request
        updated = request.override(tools=[*request.tools, calculate_tip])
        return handler(updated)

    def wrap_tool_call(self, request: ToolCallRequest, handler):
        # Handle execution of the dynamic tool
        if request.tool_call["name"] == "calculate_tip":
            return handler(request.override(tool=calculate_tip))
        return handler(request)

agent = create_agent(
    model="gpt-4o",
    tools=[get_weather],  # Only static tools registered here
    middleware=[DynamicToolMiddleware()],
)

# The agent can now use both get_weather AND calculate_tip
result = agent.invoke({
    "messages": [{"role": "user", "content": "Calculate a 20% tip on $85"}]
})
```

这种方法最适用于以下情况：

- 工具在运行时被发现（例如，从MCP服务器）
- 工具会根据用户数据或配置动态生成
- 你正在与外部工具注册表集成

> 对于运行时注册的工具，`wrap_tool_call`钩子是必需的，因为智能体需要知道如何执行那些不在原始工具列表中的工具。如果没有它，智能体将不知道如何调用动态添加的工具。

##### 过滤预注册工具

当所有可能的工具在智能体创建时都已知晓，你可以预先注册这些工具，并根据状态、权限或上下文动态筛选哪些工具对模型可见。

###### 基于State过滤

仅在特定对话里程碑后启用高级工具：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@wrap_model_call
def state_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on conversation State."""
    # Read from State: check if user has authenticated
    state = request.state
    is_authenticated = state.get("authenticated", False)
    message_count = len(state["messages"])

    # Only enable sensitive tools after authentication
    if not is_authenticated:
        tools = [t for t in request.tools if t.name.startswith("public_")]
        request = request.override(tools=tools)
    elif message_count < 5:
        # Limit tools early in conversation
        tools = [t for t in request.tools if t.name != "advanced_search"]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-4.1",
    tools=[public_search, private_search, advanced_search],
    middleware=[state_based_tools]
)
```

###### 基于Store过滤

根据用户偏好或Store中的功能标志筛选工具：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable
from langgraph.store.memory import InMemoryStore

@dataclass
class Context:
    user_id: str

@wrap_model_call
def store_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on Store preferences."""
    user_id = request.runtime.context.user_id

    # Read from Store: get user's enabled features
    store = request.runtime.store
    feature_flags = store.get(("features",), user_id)

    if feature_flags:
        enabled_features = feature_flags.value.get("enabled_tools", [])
        # Only include tools that are enabled for this user
        tools = [t for t in request.tools if t.name in enabled_features]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-4.1",
    tools=[search_tool, analysis_tool, export_tool],
    middleware=[store_based_tools],
    context_schema=Context,
    store=InMemoryStore()
)
```

###### 基于Runtime Context过滤

根据运行时上下文中的用户权限筛选工具：

```python
from dataclasses import dataclass
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable

@dataclass
class Context:
    user_role: str

@wrap_model_call
def context_based_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse]
) -> ModelResponse:
    """Filter tools based on Runtime Context permissions."""
    # Read from Runtime Context: get user role
    if request.runtime is None or request.runtime.context is None:
        # If no context provided, default to viewer (most restrictive)
        user_role = "viewer"
    else:
        user_role = request.runtime.context.user_role

    if user_role == "admin":
        # Admins get all tools
        pass
    elif user_role == "editor":
        # Editors can't delete
        tools = [t for t in request.tools if t.name != "delete_data"]
        request = request.override(tools=tools)
    else:
        # Viewers get read-only tools
        tools = [t for t in request.tools if t.name.startswith("read_")]
        request = request.override(tools=tools)

    return handler(request)

agent = create_agent(
    model="gpt-4.1",
    tools=[read_data, write_data, delete_data],
    middleware=[context_based_tools],
    context_schema=Context
)
```

以下情况最适合采用这种方法：

- 所有可能的工具在编译/启动时都是已知的
- 你希望基于权限、功能标志或对话状态进行筛选
- 工具是静态的，但其可用性是动态的

##### 工具错误处理

要自定义工具错误的处理方式，请使用`@wrap_tool_call`装饰器来创建中间件：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_tool_call
from langchain.messages import ToolMessage


@wrap_tool_call
def handle_tool_errors(request, handler):
    """Handle tool execution errors with custom messages."""
    try:
        return handler(request)
    except Exception as e:
        # Return a custom error message to the model
        return ToolMessage(
            content=f"Tool error: Please check your input and try again. ({str(e)})",
            tool_call_id=request.tool_call["id"]
        )

agent = create_agent(
    model="gpt-4.1",
    tools=[search, get_weather],
    middleware=[handle_tool_errors]
)
```

#### ReAct循环中的工具使用

智能体遵循ReAct（"推理+行动"）模式，在简短的推理步骤与有针对性的工具调用之间交替进行，并将产生的观察结果纳入后续决策，直至能够提供最终答案。

**ReAct循环示例：**

```
提示：找出当前最受欢迎的无线耳机并确认其库存。

推理："popularity具有时效性，我需要使用提供的搜索工具。"
行动：调用search_products("wireless headphones")

================================== Ai Message ==================================
Tool Calls:
  search_products (call_abc123)
 Call ID: call_abc123
  Args:
    query: wireless headphones

================================= Tool Message =================================

Found 5 products matching "wireless headphones". Top 5 results: WH-1000XM5, ...

推理："我需要先确认排名最高的商品是否有货，然后再作答。"
行动：调用check_inventory("WH-1000XM5")

================================== Ai Message ==================================
Tool Calls:
  check_inventory (call_def456)
 Call ID: call_def456
  Args:
    product_id: WH-1000XM5

================================= Tool Message =================================

Product WH-1000XM5: 10 units in stock

推理："我掌握了最受欢迎的型号及其库存状态。现在我可以回答用户的问题了。"
行动：生成最终答案

================================== Ai Message ==================================

I found wireless headphones (model WH-1000XM5) with 10 units in stock...
```

#### 系统提示 (System Prompt)

你可以通过提供提示词来塑造你的智能体处理任务的方式。`system_prompt`参数可以作为字符串提供：

```python
agent = create_agent(
    model,
    tools,
    system_prompt="You are a helpful assistant. Be concise and accurate."
)
```

> 当未提供`system_prompt`时，智能体将直接从消息中推断其任务。

`system_prompt`参数接受`str`或`SystemMessage`。使用`SystemMessage`可以让你对提示结构有更多控制，这对于特定于提供商的功能（如Anthropic的提示缓存）很有用：

```python
from langchain.agents import create_agent
from langchain.messages import SystemMessage, HumanMessage

literary_agent = create_agent(
    model="anthropic:claude-sonnet-4-5",
    system_prompt=SystemMessage(
        content=[
            {
                "type": "text",
                "text": "You are an AI assistant tasked with analyzing literary works.",
            },
            {
                "type": "text",
                "text": "<the entire contents of 'Pride and Prejudice'>",
                "cache_control": {"type": "ephemeral"}
            }
        ]
    )
)

result = literary_agent.invoke(
    {"messages": [HumanMessage("Analyze the major themes in 'Pride and Prejudice'.")]}
)
```

##### 动态系统提示

对于需要根据运行时上下文或智能体状态修改系统提示的更高级用例，您可以使用中间件。`@dynamic_prompt`装饰器会创建中间件，该中间件基于模型请求生成系统提示：

```python
from typing import TypedDict

from langchain.agents import create_agent
from langchain.agents.middleware import dynamic_prompt, ModelRequest


class Context(TypedDict):
    user_role: str

@dynamic_prompt
def user_role_prompt(request: ModelRequest) -> str:
    """Generate system prompt based on user role."""
    user_role = request.runtime.context.get("user_role", "user")
    base_prompt = "You are a helpful assistant."

    if user_role == "expert":
        return f"{base_prompt} Provide detailed technical responses."
    elif user_role == "beginner":
        return f"{base_prompt} Explain concepts simply and avoid jargon."

    return base_prompt

agent = create_agent(
    model="gpt-4.1",
    tools=[web_search],
    middleware=[user_role_prompt],
    context_schema=Context
)

# The system prompt will be set dynamically based on context
result = agent.invoke(
    {"messages": [{"role": "user", "content": "Explain machine learning"}]},
    context={"user_role": "expert"}
)
```

#### 名称 (Name)

为智能体设置一个可选的`name`。在多智能体系统中将智能体作为子图添加时，此名称会用作节点标识符：

```python
agent = create_agent(
    model,
    tools,
    name="research_assistant"
)
```

> 智能体名称首选snake_case（例如，使用research_assistant而非Research Assistant）。部分模型提供商不接受包含空格或特殊字符的名称。仅使用字母数字字符、下划线和连字符可确保在所有提供商处的兼容性。

#### 调用 (Invocation)

你可以通过向智能体的State传递更新来调用它。所有智能体的状态中都包含一个消息序列；要调用智能体，只需传递一条新消息即可：

```python
result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's the weather in San Francisco?"}]}
)
```

否则，该智能体遵循LangGraph图API，并支持所有相关方法，例如`stream`和`invoke`。

### 高级概念

#### 结构化输出 (Structured Output)

在某些情况下，你可能希望智能体以特定格式返回输出。LangChain通过`response_format`参数提供了结构化输出的策略。

##### ToolStrategy

`ToolStrategy`使用人工工具调用生成结构化输出。这适用于任何支持工具调用的模型。当原生结构化输出不可用或不可靠时，应使用`ToolStrategy`。

```python
from pydantic import BaseModel
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy


class ContactInfo(BaseModel):
    name: str
    email: str
    phone: str

agent = create_agent(
    model="gpt-4.1-mini",
    tools=[search_tool],
    response_format=ToolStrategy(ContactInfo)
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
})

result["structured_response"]
# ContactInfo(name='John Doe', email='john@example.com', phone='(555) 123-4567')
```

##### ProviderStrategy

`ProviderStrategy`采用模型提供商的原生结构化输出生成方式。这种方式更可靠，但仅适用于支持原生结构化输出的提供商：

```python
from langchain.agents.structured_output import ProviderStrategy

agent = create_agent(
    model="gpt-4.1",
    response_format=ProviderStrategy(ContactInfo)
)
```

> 在langchain 1.0中，只需传递一个模式（例如`response_format=ContactInfo`），如果模型支持原生结构化输出，将默认使用`ProviderStrategy`；否则，将回退到`ToolStrategy`。

#### 记忆 (Memory)

智能体通过消息状态自动保存对话历史。你也可以配置智能体使用自定义状态模式，以在对话过程中记住额外信息。

状态中存储的信息可以被视为智能体的短期记忆。自定义状态模式必须作为`TypedDict`扩展`AgentState`。

定义自定义状态有两种方式：

##### 通过中间件定义状态

当你的自定义状态需要被特定的中间件钩子和附加到该中间件的工具访问时，请使用中间件来定义自定义状态。

```python
from langchain.agents import AgentState
from langchain.agents.middleware import AgentMiddleware
from typing import Any


class CustomState(AgentState):
    user_preferences: dict

class CustomMiddleware(AgentMiddleware):
    state_schema = CustomState
    tools = [tool1, tool2]

    def before_model(self, state: CustomState, runtime) -> dict[str, Any] | None:
        ...

agent = create_agent(
    model,
    tools=tools,
    middleware=[CustomMiddleware()]
)

# The agent can now track additional state beyond messages
result = agent.invoke({
    "messages": [{"role": "user", "content": "I prefer technical explanations"}],
    "user_preferences": {"style": "technical", "verbosity": "detailed"},
})
```

##### 通过state_schema定义状态

使用`state_schema`参数作为快捷方式来定义仅在工具中使用的自定义状态。

```python
from langchain.agents import AgentState


class CustomState(AgentState):
    user_preferences: dict

agent = create_agent(
    model,
    tools=[tool1, tool2],
    state_schema=CustomState
)

# The agent can now track additional state beyond messages
result = agent.invoke({
    "messages": [{"role": "user", "content": "I prefer technical explanations"}],
    "user_preferences": {"style": "technical", "verbosity": "detailed"},
})
```

> 自langchain 1.0起，自定义状态模式必须是`TypedDict`类型。Pydantic模型和数据类不再受支持。

#### 流处理 (Streaming)

我们已经了解到可以通过`invoke`调用智能体来获取最终响应。如果智能体执行多个步骤，这可能需要一段时间。为了展示中间进度，我们可以在消息出现时将其流式返回。

```python
from langchain.messages import AIMessage, HumanMessage

for chunk in agent.stream({
    "messages": [{"role": "user", "content": "Search for AI news and summarize the findings"}]
}, stream_mode="values"):
    # Each chunk contains the full state at that point
    latest_message = chunk["messages"][-1]
    if latest_message.content:
        if isinstance(latest_message, HumanMessage):
            print(f"User: {latest_message.content}")
        elif isinstance(latest_message, AIMessage):
            print(f"Agent: {latest_message.content}")
    elif latest_message.tool_calls:
        print(f"Calling tools: {[tc['name'] for tc in latest_message.tool_calls]}")
```

#### 中间件 (Middleware)

中间件为在执行的不同阶段自定义智能体行为提供了强大的扩展性。您可以使用中间件来：

- 在调用模型之前处理状态（例如，消息截断、上下文注入）
- 修改或验证模型的响应（例如，安全护栏、内容过滤）
- 使用自定义逻辑处理工具执行错误
- 基于状态或上下文实现动态模型选择
- 添加自定义日志记录、监控或分析

中间件能无缝集成到智能体的执行过程中，让你可以在关键节点拦截和修改数据流，而无需更改智能体的核心逻辑。

## 5. 模型 (Models)

[大语言模型（LLMs）](https://en.wikipedia.org/wiki/Large_language_model)是强大的人工智能工具，能够像人类一样解释和生成文本。它们足够通用，可以编写内容、翻译语言、摘要和回答问题，而无需针对每项任务进行专门训练。

除文本生成外，许多模型还支持：

- **工具调用** - 调用外部工具（如数据库查询或API调用）并在响应中使用结果
- **结构化输出** - 模型的响应被约束为遵循定义的格式
- **多模态** - 处理和返回文本以外的数据，如图像、音频和视频
- **推理** - 模型执行多步骤推理以得出结论

模型是智能体的推理引擎。它们驱动智能体的决策过程，确定调用哪些工具、如何解释结果以及何时提供最终答案。

您选择的模型的质量和能力直接影响智能体的基线可靠性和性能。不同的模型擅长不同的任务——有些更擅长遵循复杂指令，有些更擅长结构化推理，有些支持更大的上下文窗口来处理更多信息。

LangChain的标准模型接口让您可以访问许多不同的提供商集成，这使得实验和在模型之间切换变得容易，以找到最适合您用例的模型。

### 基本用法

模型可以通过两种方式使用：

1. **与智能体一起** - 在创建智能体时可以动态指定模型
2. **独立使用** - 可以直接调用模型（在智能体循环之外）执行文本生成、分类或提取等任务，无需智能体框架

#### 初始化模型

在LangChain中开始使用独立模型的最简单方法是使用`init_chat_model`从您选择的聊天模型提供商初始化一个模型：

**OpenAI**

```bash
pip install -U "langchain[openai]"
```

```python
import os
from langchain.chat_models import init_chat_model

os.environ["OPENAI_API_KEY"] = "sk-..."

model = init_chat_model("gpt-4.1")
```

**Anthropic**

```bash
pip install -U "langchain[anthropic]"
```

```python
import os
from langchain.chat_models import init_chat_model

os.environ["ANTHROPIC_API_KEY"] = "sk-..."

model = init_chat_model("claude-sonnet-4-5-20250929")
```

**Google Gemini**

```bash
pip install -U "langchain[google-genai]"
```

```python
import os
from langchain.chat_models import init_chat_model

os.environ["GOOGLE_API_KEY"] = "..."

model = init_chat_model("google_genai:gemini-2.5-flash-lite")
```

**调用模型**

```python
response = model.invoke("Why do parrots talk?")
```

#### 支持的模型

LangChain支持所有主要模型提供商，包括OpenAI、Anthropic、Google、Azure、AWS Bedrock等。每个提供商提供各种具有不同功能的模型。

### 参数

聊天模型接受可用于配置其行为的参数。支持的完整参数集因模型和提供商而异，但标准参数包括：

| 参数 | 类型 | 说明 |
|------|------|------|
| `model` | string | 要使用的特定模型的名称或标识符。也可以使用`{model_provider}:{model}`格式同时指定模型及其提供商 |
| `api_key` | string | 用于与模型提供商进行身份验证的密钥 |
| `temperature` | number | 控制模型输出的随机性。较高的值使响应更有创意；较低的值使其更具确定性 |
| `max_tokens` | number | 限制响应中的总token数，有效控制输出的长度 |
| `timeout` | number | 在取消请求之前等待模型响应的最长时间（秒） |
| `max_retries` | number | 如果由于网络超时或速率限制等问题导致请求失败，系统将重新发送请求的最大尝试次数。默认为6 |

```python
model = init_chat_model(
    "claude-sonnet-4-5-20250929",
    temperature=0.7,
    timeout=30,
    max_tokens=1000,
    max_retries=6,
)
```

---

### 调用方法

必须调用聊天模型才能生成输出。有三种主要调用方法，每种方法适用于不同的用例。

#### Invoke

调用模型最直接的方法是使用`invoke()`和单个消息或消息列表。

**单条消息**

```python
response = model.invoke("Why do parrots have colorful feathers?")
print(response)
```

**消息列表（对话历史）**

```python
from langchain.messages import HumanMessage, AIMessage, SystemMessage

conversation = [
    SystemMessage("You are a helpful assistant that translates English to French."),
    HumanMessage("Translate: I love programming."),
    AIMessage("J'adore la programmation."),
    HumanMessage("Translate: I love building applications.")
]

response = model.invoke(conversation)
print(response)  # AIMessage("J'adore créer des applications.")
```

#### Stream

大多数模型可以在生成输出内容时进行流式传输。通过逐步显示输出，流式传输显著改善用户体验，特别是对于较长的响应。

```python
for chunk in model.stream("Why do parrots have colorful feathers?"):
    print(chunk.text, end="|", flush=True)
```

与`invoke()`不同（后者在模型完成生成完整响应后返回单个`AIMessage`），`stream()`返回多个`AIMessageChunk`对象，每个对象包含输出文本的一部分。每个流中的块都被设计为通过求和聚合成完整消息：

```python
full = None
for chunk in model.stream("What color is the sky?"):
    full = chunk if full is None else full + chunk
    print(full.text)

# The
# The sky
# The sky is
# The sky is typically
# The sky is typically blue
# ...
```

#### Batch

将一组独立请求批处理到模型可以显著提高性能并降低成本，因为处理可以并行完成：

```python
responses = model.batch([
    "Why do parrots have colorful feathers?",
    "How do airplanes fly?",
    "What is quantum computing?"
])
for response in responses:
    print(response)
```

---

### 工具调用 (Tool Calling)

模型可以请求调用执行诸如从数据库获取数据、搜索网络或运行代码等任务的工具。工具是以下内容的配对：

1. 模式，包括工具名称、描述和/或参数定义（通常是JSON模式）
2. 要执行的函数或协程

要使您定义的工具可供模型使用，必须使用`bind_tools`绑定它们。在后续调用中，模型可以根据需要选择调用任何绑定的工具。

```python
from langchain.tools import tool

@tool
def get_weather(location: str) -> str:
    """Get the weather at a location."""
    return f"It's sunny in {location}."

model_with_tools = model.bind_tools([get_weather])

response = model_with_tools.invoke("What's the weather like in Boston?")
for tool_call in response.tool_calls:
    print(f"Tool: {tool_call['name']}")
    print(f"Args: {tool_call['args']}")
```

#### 工具执行循环

当模型返回工具调用时，您需要执行工具并将结果传回模型。这创建了一个对话循环，模型可以使用工具结果生成其最终响应。

```python
model_with_tools = model.bind_tools([get_weather])

# Step 1: 模型生成工具调用
messages = [{"role": "user", "content": "What's the weather in Boston?"}]
ai_msg = model_with_tools.invoke(messages)
messages.append(ai_msg)

# Step 2: 执行工具并收集结果
for tool_call in ai_msg.tool_calls:
    tool_result = get_weather.invoke(tool_call)
    messages.append(tool_result)

# Step 3: 将结果传回模型以获取最终响应
final_response = model_with_tools.invoke(messages)
print(final_response.text)
```

#### 强制工具调用

默认情况下，模型可以自由选择根据用户输入使用哪个绑定工具。但是，您可能希望强制选择工具：

```python
# 强制使用任何工具
model_with_tools = model.bind_tools([tool_1], tool_choice="any")

# 强制使用特定工具
model_with_tools = model.bind_tools([tool_1], tool_choice="tool_1")
```

#### 并行工具调用

许多模型支持在适当时并行调用多个工具。这允许模型同时从不同来源收集信息。

```python
model_with_tools = model.bind_tools([get_weather])

response = model_with_tools.invoke("What's the weather in Boston and Tokyo?")

print(response.tool_calls)
# [
#   {'name': 'get_weather', 'args': {'location': 'Boston'}, 'id': 'call_1'},
#   {'name': 'get_weather', 'args': {'location': 'Tokyo'}, 'id': 'call_2'},
# ]
```

---

### 结构化输出 (Structured Output)

模型可以被请求以匹配给定模式的格式提供响应。这对于确保输出可以轻松解析并在后续处理中使用非常有用。LangChain支持多种模式类型和方法来强制执行结构化输出。

#### 使用Pydantic

```python
from pydantic import BaseModel, Field

class Movie(BaseModel):
    """A movie with details."""
    title: str = Field(..., description="The title of the movie")
    year: int = Field(..., description="The year the movie was released")
    director: str = Field(..., description="The director of the movie")
    rating: float = Field(..., description="The movie's rating out of 10")

model_with_structure = model.with_structured_output(Movie)
response = model_with_structure.invoke("Provide details about the movie Inception")
print(response)  # Movie(title="Inception", year=2010, ...)
```

#### 使用TypedDict

```python
from typing_extensions import TypedDict, Annotated

class MovieDict(TypedDict):
    """A movie with details."""
    title: Annotated[str, ..., "The title of the movie"]
    year: Annotated[int, ..., "The year the movie was released"]
    director: Annotated[str, ..., "The director of the movie"]
    rating: Annotated[float, ..., "The movie's rating out of 10"]

model_with_structure = model.with_structured_output(MovieDict)
response = model_with_structure.invoke("Provide details about the movie Inception")
```

---

### 高级主题

#### 模型配置文件 (Model Profiles)

LangChain聊天模型可以通过`.profile`属性公开支持的功能和能力的字典：

```python
model.profile
# {
#   "max_input_tokens": 400000,
#   "image_inputs": True,
#   "reasoning_output": True,
#   "tool_calling": True,
#   ...
# }
```

#### 多模态 (Multimodal)

某些模型可以处理和返回非文本数据，如图像、音频和视频。您可以通过提供内容块将非文本数据传递给模型。

```python
response = model.invoke("Create a picture of a cat")
print(response.content_blocks)
# [
#     {"type": "text", "text": "Here's a picture of a cat"},
#     {"type": "image", "base64": "...", "mime_type": "image/jpeg"},
# ]
```

#### 推理 (Reasoning)

许多模型能够执行多步骤推理以得出结论。如果底层模型支持，您可以显示此推理过程以更好地理解模型如何得出最终答案。

```python
for chunk in model.stream("Why do parrots have colorful feathers?"):
    reasoning_steps = [r for r in chunk.content_blocks if r["type"] == "reasoning"]
    print(reasoning_steps if reasoning_steps else chunk.text)
```

#### 本地模型

LangChain支持在您自己的硬件上本地运行模型。这对于数据隐私至关重要、想要调用自定义模型或想要避免使用云端模型时产生的成本的情况非常有用。

[Ollama](https://ollama.ai/)是在本地运行聊天和嵌入模型的最简单方法之一。

#### 提示缓存 (Prompt Caching)

许多提供商提供提示缓存功能，以减少重复处理相同token的延迟和成本。这些功能可以是**隐式**或**显式**的：

- **隐式提示缓存：** 提供商将自动传递成本节省，如果请求命中缓存。例如：OpenAI和Gemini。
- **显式缓存：** 提供商允许您手动指示缓存点以获得更大控制或保证成本节省。例如：Anthropic的`AnthropicPromptCachingMiddleware`。

#### 服务端工具使用

某些提供商支持服务端工具调用循环：模型可以在单个对话轮次中与网络搜索、代码解释器和其他工具交互并分析结果。

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-4.1-mini")

tool = {"type": "web_search"}
model_with_tools = model.bind_tools([tool])

response = model_with_tools.invoke("What was a positive news story from today?")
print(response.content_blocks)
```

#### 速率限制

许多聊天模型提供商对在给定时间段内可以进行的调用次数施加限制。为了帮助管理速率限制，聊天模型集成接受一个`rate_limiter`参数：

```python
from langchain_core.rate_limiters import InMemoryRateLimiter

rate_limiter = InMemoryRateLimiter(
    requests_per_second=0.1,  # 每10秒1个请求
    check_every_n_seconds=0.1,
    max_bucket_size=10,
)

model = init_chat_model(
    model="gpt-5",
    model_provider="openai",
    rate_limiter=rate_limiter
)
```

#### 基础URL或代理

对于许多聊天模型集成，您可以配置API请求的基础URL，这允许您使用具有OpenAI兼容API的模型提供商或使用代理服务器：

```python
model = init_chat_model(
    model="MODEL_NAME",
    model_provider="openai",
    base_url="BASE_URL",
    api_key="YOUR_API_KEY",
)
```

#### Token使用情况

许多模型提供商作为调用响应的一部分返回token使用信息。当可用时，此信息将包含在相应模型生成的`AIMessage`对象中。

```python
from langchain.chat_models import init_chat_model
from langchain_core.callbacks import get_usage_metadata_callback

model_1 = init_chat_model(model="gpt-4.1-mini")
model_2 = init_chat_model(model="claude-haiku-4-5-20251001")

with get_usage_metadata_callback() as cb:
    model_1.invoke("Hello")
    model_2.invoke("Hello")
    print(cb.usage_metadata)
```

#### 调用配置

调用模型时，可以通过`config`参数使用`RunnableConfig`字典传递额外的配置：

```python
response = model.invoke(
    "Tell me a joke",
    config={
        "run_name": "joke_generation",
        "tags": ["humor", "demo"],
        "metadata": {"user_id": "123"},
        "callbacks": [my_callback_handler],
    }
)
```

#### 可配置模型

您可以通过指定`configurable_fields`创建运行时可配置的模型：

```python
from langchain.chat_models import init_chat_model

configurable_model = init_chat_model(temperature=0)

configurable_model.invoke(
    "what's your name",
    config={"configurable": {"model": "gpt-5-nano"}},
)
configurable_model.invoke(
    "what's your name",
    config={"configurable": {"model": "claude-sonnet-4-5-20250929"}},
)
```

## 6. 消息 (Messages)

消息是LangChain中模型上下文的基本单位。它们代表模型的输入和输出，携带在与LLM交互时表示对话状态所需的内容和元数据。

消息对象包含：

- **角色（Role）** - 标识消息类型（如`system`、`user`）
- **内容（Content）** - 表示消息的实际内容（如文本、图像、音频、文档等）
- **元数据（Metadata）** - 可选字段，如响应信息、消息ID和token使用情况

LangChain提供适用于所有模型提供商的标准消息类型，确保无论调用哪个模型都能保持一致的行为。

### 基本用法

使用消息最简单的方法是创建消息对象并在调用时将其传递给模型。

```python
from langchain.chat_models import init_chat_model
from langchain.messages import HumanMessage, AIMessage, SystemMessage

model = init_chat_model("gpt-5-nano")

system_msg = SystemMessage("You are a helpful assistant.")
human_msg = HumanMessage("Hello, how are you?")

# Use with chat models
messages = [system_msg, human_msg]
response = model.invoke(messages)  # Returns AIMessage
```

#### 文本提示

文本提示是字符串 - 适用于不需要保留对话历史的简单生成任务。

```python
response = model.invoke("Write a haiku about spring")
```

**使用文本提示的场景：**
- 您有单个独立请求
- 不需要对话历史
- 希望代码复杂度最低

#### 消息提示

或者，您可以通过提供消息对象列表将消息列表传递给模型。

```python
from langchain.messages import SystemMessage, HumanMessage, AIMessage

messages = [
    SystemMessage("You are a poetry expert"),
    HumanMessage("Write a haiku about spring"),
    AIMessage("Cherry blossoms bloom...")
]
response = model.invoke(messages)
```

**使用消息提示的场景：**
- 管理多轮对话
- 处理多模态内容（图像、音频、文件）
- 包含系统指令

#### 字典格式

您也可以直接以OpenAI聊天完成格式指定消息。

```python
messages = [
    {"role": "system", "content": "You are a poetry expert"},
    {"role": "user", "content": "Write a haiku about spring"},
    {"role": "assistant", "content": "Cherry blossoms bloom..."}
]
response = model.invoke(messages)
```

### 消息类型

#### 系统消息 (System Message)

`SystemMessage`代表初始化模型行为的一组指令。您可以使用系统消息来设置语气、定义模型角色并建立响应指南。

```python
from langchain.messages import SystemMessage, HumanMessage

system_msg = SystemMessage("""
You are a senior Python developer with expertise in web frameworks.
Always provide code examples and explain your reasoning.
Be concise but thorough in your explanations.
""")

messages = [
    system_msg,
    HumanMessage("How do I create a REST API?")
]
response = model.invoke(messages)
```

#### 人类消息 (Human Message)

`HumanMessage`代表用户输入和交互。它们可以包含文本、图像、音频、文件和任何其他多模态内容。

**文本内容**

```python
# Message object
response = model.invoke([
    HumanMessage("What is machine learning?")
])

# String shortcut
response = model.invoke("What is machine learning?")
```

**消息元数据**

```python
human_msg = HumanMessage(
    content="Hello!",
    name="alice",  # Optional: identify different users
    id="msg_123",  # Optional: unique identifier for tracing
)
```

#### AI消息 (AI Message)

`AIMessage`代表模型调用的输出。它们可以包括多模态数据、工具调用和您稍后可以访问的提供商特定元数据。

```python
response = model.invoke("Explain AI")
print(type(response))  # <class 'langchain.messages.AIMessage'>
```

**属性**

| 属性 | 类型 | 说明 |
|------|------|------|
| `text` | string | 消息的文本内容 |
| `content` | string \| dict[] | 消息的原始内容 |
| `content_blocks` | ContentBlock[] | 消息的标准化内容块 |
| `tool_calls` | dict[] \| None | 模型进行的工具调用 |
| `id` | string | 消息的唯一标识符 |
| `usage_metadata` | dict \| None | 消息的使用元数据，可包含token计数 |
| `response_metadata` | ResponseMetadata \| None | 消息的响应元数据 |

**工具调用**

当模型进行工具调用时，它们包含在`AIMessage`中：

```python
from langchain.chat_models import init_chat_model

model = init_chat_model("gpt-5-nano")

def get_weather(location: str) -> str:
    """Get the weather at a location."""
    ...

model_with_tools = model.bind_tools([get_weather])
response = model_with_tools.invoke("What's the weather in Paris?")

for tool_call in response.tool_calls:
    print(f"Tool: {tool_call['name']}")
    print(f"Args: {tool_call['args']}")
    print(f"ID: {tool_call['id']}")
```

**Token使用情况**

`AIMessage`可以在其`usage_metadata`字段中保存token计数和其他使用元数据：

```python
response = model.invoke("Hello!")
response.usage_metadata
# {'input_tokens': 8, 'output_tokens': 304, 'total_tokens': 312, ...}
```

**流式传输和块**

在流式传输期间，您将收到可以组合成完整消息对象的`AIMessageChunk`对象：

```python
chunks = []
full_message = None
for chunk in model.stream("Hi"):
    chunks.append(chunk)
    print(chunk.text)
    full_message = chunk if full_message is None else full_message + chunk
```

#### 工具消息 (Tool Message)

对于支持工具调用的模型，AI消息可以包含工具调用。工具消息用于将单个工具执行的结果传回模型。

```python
from langchain.messages import AIMessage, ToolMessage

# After a model makes a tool call
ai_message = AIMessage(
    content=[],
    tool_calls=[{
        "name": "get_weather",
        "args": {"location": "San Francisco"},
        "id": "call_123"
    }]
)

# Execute tool and create result message
weather_result = "Sunny, 72°F"
tool_message = ToolMessage(
    content=weather_result,
    tool_call_id="call_123"  # Must match the call ID
)

# Continue conversation
messages = [
    HumanMessage("What's the weather in San Francisco?"),
    ai_message,  # Model's tool call
    tool_message,  # Tool execution result
]
response = model.invoke(messages)  # Model processes the result
```

**属性**

| 属性 | 类型 | 说明 |
|------|------|------|
| `content` | string | 工具调用的字符串化输出（必需） |
| `tool_call_id` | string | 此消息响应的工具调用ID（必需） |
| `name` | string | 被调用工具的名称（必需） |
| `artifact` | dict | 不发送给模型但可以编程方式访问的附加数据 |

### 消息内容

您可以将消息的内容视为发送给模型的数据负载。消息有一个`content`属性，它是松散类型的，支持字符串和未类型化对象列表（如字典）。这允许直接在LangChain聊天模型中支持提供商原生结构，如多模态内容和其他数据。

LangChain聊天模型接受`content`属性中的消息内容。这可能包含：

1. 字符串
2. 提供商原生格式的内容块列表
3. LangChain标准内容块列表

```python
from langchain.messages import HumanMessage

# String content
human_message = HumanMessage("Hello, how are you?")

# Provider-native format (e.g., OpenAI)
human_message = HumanMessage(content=[
    {"type": "text", "text": "Hello, how are you?"},
    {"type": "image_url", "image_url": {"url": "https://example.com/image.jpg"}}
])

# List of standard content blocks
human_message = HumanMessage(content_blocks=[
    {"type": "text", "text": "Hello, how are you?"},
    {"type": "image", "url": "https://example.com/image.jpg"},
])
```

#### 标准内容块

LangChain提供适用于各提供商的消息内容标准表示。消息对象实现一个`content_blocks`属性，该属性将`content`属性延迟解析为标准的、类型安全的表示。

```python
from langchain.messages import AIMessage

message = AIMessage(
    content=[
        {"type": "thinking", "thinking": "...", "signature": "WaUjzkyp..."},
        {"type": "text", "text": "..."},
    ],
    response_metadata={"model_provider": "anthropic"}
)
message.content_blocks
# [{'type': 'reasoning', 'reasoning': '...', 'extras': {'signature': 'WaUjzkyp...'}},
#  {'type': 'text', 'text': '...'}]
```

#### 多模态 (Multimodal)

**多模态**是指处理不同形式数据的能力，如文本、音频、图像和视频。LangChain包含可用于各提供商的这些数据的标准类型。

**图像输入**

```python
# From URL
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this image."},
        {"type": "image", "url": "https://example.com/path/to/image.jpg"},
    ]
}

# From base64 data
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this image."},
        {
            "type": "image",
            "base64": "AAAAIGZ0eXBtcDQyAAAAAGlzb21tcDQyAAACAGlzb2...",
            "mime_type": "image/jpeg",
        },
    ]
}
```

**PDF文档输入**

```python
# From URL
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this document."},
        {"type": "file", "url": "https://example.com/path/to/document.pdf"},
    ]
}

# From base64 data
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this document."},
        {
            "type": "file",
            "base64": "AAAAIGZ0eXBtcDQyAAAAAGlzb21tcDQyAAACAGlzb2...",
            "mime_type": "application/pdf",
        },
    ]
}
```

**音频输入**

```python
# From base64 data
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this audio."},
        {
            "type": "audio",
            "base64": "AAAAIGZ0eXBtcDQyAAAAAGlzb21tcDQyAAACAGlzb2...",
            "mime_type": "audio/wav",
        },
    ]
}
```

**视频输入**

```python
# From base64 data
message = {
    "role": "user",
    "content": [
        {"type": "text", "text": "Describe the content of this video."},
        {
            "type": "video",
            "base64": "AAAAIGZ0eXBtcDQyAAAAAGlzb21tcDQyAAACAGlzb2...",
            "mime_type": "video/mp4",
        },
    ]
}
```

> 并非所有模型都支持所有文件类型。请查看模型提供商的参考文档以了解支持的格式和大小限制。

### 内容块参考

内容块表示为类型化字典列表。列表中的每个项目必须符合以下块类型之一：

#### 核心类型

**TextContentBlock** - 标准文本输出

```python
{
    "type": "text",
    "text": "Hello world",
    "annotations": []
}
```

**ReasoningContentBlock** - 模型推理步骤

```python
{
    "type": "reasoning",
    "reasoning": "The user is asking about...",
    "extras": {"signature": "abc123"},
}
```

#### 多模态类型

**ImageContentBlock** - 图像数据

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 始终为`"image"` |
| `url` | string | 指向图像位置的URL |
| `base64` | string | Base64编码的图像数据 |
| `mime_type` | string | 图像MIME类型（如`image/jpeg`） |

**AudioContentBlock** - 音频数据

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 始终为`"audio"` |
| `url` | string | 指向音频位置的URL |
| `base64` | string | Base64编码的音频数据 |
| `mime_type` | string | 音频MIME类型（如`audio/wav`） |

**VideoContentBlock** - 视频数据

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 始终为`"video"` |
| `url` | string | 指向视频位置的URL |
| `base64` | string | Base64编码的视频数据 |
| `mime_type` | string | 视频MIME类型（如`video/mp4`） |

**FileContentBlock** - 通用文件（PDF等）

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 始终为`"file"` |
| `url` | string | 指向文件位置的URL |
| `base64` | string | Base64编码的文件数据 |
| `mime_type` | string | 文件MIME类型（如`application/pdf`） |

#### 工具调用类型

**ToolCall** - 函数调用

```python
{
    "type": "tool_call",
    "name": "search",
    "args": {"query": "weather"},
    "id": "call_123"
}
```

**ToolCallChunk** - 流式工具调用片段

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 始终为`"tool_call_chunk"` |
| `name` | string | 被调用工具的名称 |
| `args` | string | 部分工具参数（可能是不完整的JSON） |
| `id` | string | 工具调用标识符 |
| `index` | number \| string | 此块在流中的位置 |

**InvalidToolCall** - 格式错误的调用

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 始终为`"invalid_tool_call"` |
| `name` | string | 未能调用的工具名称 |
| `args` | object | 传递给工具的参数 |
| `error` | string | 出错描述 |

#### 服务端工具执行类型

**ServerToolCall** - 服务端执行的工具调用

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 始终为`"server_tool_call"` |
| `id` | string | 与工具调用关联的标识符 |
| `name` | string | 要调用的工具名称 |
| `args` | string | 工具参数 |

**ServerToolResult** - 搜索结果

| 字段 | 类型 | 说明 |
|------|------|------|
| `type` | string | 始终为`"server_tool_result"` |
| `tool_call_id` | string | 对应服务端工具调用的标识符 |
| `status` | string | 执行状态（`"success"`或`"error"`） |
| `output` | any | 已执行工具的输出 |

### 与聊天模型一起使用

聊天模型接受消息对象序列作为输入，并返回`AIMessage`作为输出。交互通常是无状态的，因此简单的对话循环涉及使用增长的消息列表调用模型。

相关指南：
- [持久化和管理对话历史](/oss/python/langchain/short-term-memory)
- [管理上下文窗口的策略](/oss/python/langchain/short-term-memory#common-patterns)

## 7. 工具 (Tools)

工具扩展了智能体的能力——让它们能够获取实时数据、执行代码、查询外部数据库并在世界中采取行动。

在底层，工具是具有明确定义输入和输出的可调用函数，传递给聊天模型。模型根据对话上下文决定何时调用工具以及提供什么输入参数。

### 创建工具

#### 基本工具定义

创建工具最简单的方法是使用`@tool`装饰器。默认情况下，函数的文档字符串成为工具的描述，帮助模型理解何时使用它：

```python
from langchain.tools import tool

@tool
def search_database(query: str, limit: int = 10) -> str:
    """Search the customer database for records matching the query.

    Args:
        query: Search terms to look for
        limit: Maximum number of results to return
    """
    return f"Found {limit} results for '{query}'"
```

类型提示是**必需的**，因为它们定义了工具的输入模式。文档字符串应该信息丰富且简洁，以帮助模型理解工具的目的。

> **工具名称首选snake_case**（例如，使用`web_search`而非`Web Search`）。部分模型提供商不接受包含空格或特殊字符的名称。仅使用字母数字字符、下划线和连字符可确保在所有提供商处的兼容性。

#### 自定义工具属性

**自定义工具名称**

默认情况下，工具名称来自函数名。当您需要更具描述性的名称时覆盖它：

```python
@tool("web_search")  # Custom name
def search(query: str) -> str:
    """Search the web for information."""
    return f"Results for: {query}"

print(search.name)  # web_search
```

**自定义工具描述**

覆盖自动生成的工具描述以获得更清晰的模型指导：

```python
@tool("calculator", description="Performs arithmetic calculations. Use this for any math problems.")
def calc(expression: str) -> str:
    """Evaluate mathematical expressions."""
    return str(eval(expression))
```

#### 高级模式定义

使用Pydantic模型或JSON模式定义复杂输入：

**使用Pydantic模型**

```python
from pydantic import BaseModel, Field
from typing import Literal

class WeatherInput(BaseModel):
    """Input for weather queries."""
    location: str = Field(description="City name or coordinates")
    units: Literal["celsius", "fahrenheit"] = Field(
        default="celsius",
        description="Temperature unit preference"
    )
    include_forecast: bool = Field(
        default=False,
        description="Include 5-day forecast"
    )

@tool(args_schema=WeatherInput)
def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
    """Get current weather and optional forecast."""
    temp = 22 if units == "celsius" else 72
    result = f"Current weather in {location}: {temp} degrees {units[0].upper()}"
    if include_forecast:
        result += "\nNext 5 days: Sunny"
    return result
```

**使用JSON Schema**

```python
weather_schema = {
    "type": "object",
    "properties": {
        "location": {"type": "string"},
        "units": {"type": "string"},
        "include_forecast": {"type": "boolean"}
    },
    "required": ["location", "units", "include_forecast"]
}

@tool(args_schema=weather_schema)
def get_weather(location: str, units: str = "celsius", include_forecast: bool = False) -> str:
    """Get current weather and optional forecast."""
    ...
```

#### 保留参数名称

以下参数名称是保留的，不能用作工具参数。使用这些名称将导致运行时错误。

| 参数名 | 用途 |
|--------|------|
| `config` | 保留用于内部向工具传递`RunnableConfig` |
| `runtime` | 保留用于`ToolRuntime`参数（访问状态、上下文、存储） |

要访问运行时信息，请使用`ToolRuntime`参数，而不是将您自己的参数命名为`config`或`runtime`。

### 访问上下文

当工具能够访问运行时信息（如对话历史、用户数据和持久记忆）时，它们最强大。本节介绍如何从工具内部访问和更新这些信息。

工具可以通过`ToolRuntime`参数访问运行时信息，该参数提供：

| 组件 | 描述 | 用例 |
|------|------|------|
| **State** | 短期记忆 - 当前对话中存在的可变数据（消息、计数器、自定义字段） | 访问对话历史、跟踪工具调用计数 |
| **Context** | 在调用时传递的不可变配置（用户ID、会话信息） | 根据用户身份个性化响应 |
| **Store** | 长期记忆 - 跨对话持久化的数据 | 保存用户偏好、维护知识库 |
| **Stream Writer** | 在工具执行期间发出实时更新 | 为长时间运行的操作显示进度 |
| **Config** | 执行的`RunnableConfig` | 访问回调、标签和元数据 |
| **Tool Call ID** | 当前工具调用的唯一标识符 | 关联工具调用以用于日志和模型调用 |

#### 短期记忆 (State)

State代表对话期间存在的短期记忆。它包括消息历史和您在图状态中定义的任何自定义字段。

**访问状态**

工具可以使用`runtime.state`访问当前对话状态：

```python
from langchain.tools import tool, ToolRuntime
from langchain.messages import HumanMessage

@tool
def get_last_user_message(runtime: ToolRuntime) -> str:
    """Get the most recent message from the user."""
    messages = runtime.state["messages"]

    # Find the last human message
    for message in reversed(messages):
        if isinstance(message, HumanMessage):
            return message.content

    return "No user messages found"

# Access custom state fields
@tool
def get_user_preference(
    pref_name: str,
    runtime: ToolRuntime
) -> str:
    """Get a user preference value."""
    preferences = runtime.state.get("user_preferences", {})
    return preferences.get(pref_name, "Not set")
```

> `runtime`参数对模型是隐藏的。对于上面的示例，模型在工具模式中只能看到`pref_name`。

**更新状态**

使用`Command`更新智能体的状态。这对于需要更新自定义状态字段的工具很有用：

```python
from langgraph.types import Command
from langchain.tools import tool

@tool
def set_user_name(new_name: str) -> Command:
    """Set the user's name in the conversation state."""
    return Command(update={"user_name": new_name})
```

#### 上下文 (Context)

Context提供在调用时传递的不可变配置数据。用于用户ID、会话详细信息或不应在对话期间更改的应用程序特定设置。

通过`runtime.context`访问上下文：

```python
from dataclasses import dataclass
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime


USER_DATABASE = {
    "user123": {
        "name": "Alice Johnson",
        "account_type": "Premium",
        "balance": 5000,
        "email": "alice@example.com"
    },
    "user456": {
        "name": "Bob Smith",
        "account_type": "Standard",
        "balance": 1200,
        "email": "bob@example.com"
    }
}

@dataclass
class UserContext:
    user_id: str

@tool
def get_account_info(runtime: ToolRuntime[UserContext]) -> str:
    """Get the current user's account information."""
    user_id = runtime.context.user_id

    if user_id in USER_DATABASE:
        user = USER_DATABASE[user_id]
        return f"Account holder: {user['name']}\nType: {user['account_type']}\nBalance: ${user['balance']}"
    return "User not found"

model = ChatOpenAI(model="gpt-4.1")
agent = create_agent(
    model,
    tools=[get_account_info],
    context_schema=UserContext,
    system_prompt="You are a financial assistant."
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What's my current balance?"}]},
    context=UserContext(user_id="user123")
)
```

#### 长期记忆 (Store)

`BaseStore`提供跨对话持久化的存储。与状态（短期记忆）不同，保存到存储的数据在未来会话中仍然可用。

通过`runtime.store`访问存储。存储使用命名空间/键模式来组织数据：

```python
from typing import Any
from langgraph.store.memory import InMemoryStore
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime


# Access memory
@tool
def get_user_info(user_id: str, runtime: ToolRuntime) -> str:
    """Look up user info."""
    store = runtime.store
    user_info = store.get(("users",), user_id)
    return str(user_info.value) if user_info else "Unknown user"

# Update memory
@tool
def save_user_info(user_id: str, user_info: dict[str, Any], runtime: ToolRuntime) -> str:
    """Save user info."""
    store = runtime.store
    store.put(("users",), user_id, user_info)
    return "Successfully saved user info."

store = InMemoryStore()
agent = create_agent(
    model,
    tools=[get_user_info, save_user_info],
    store=store
)

# First session: save user info
agent.invoke({
    "messages": [{"role": "user", "content": "Save the following user: userid: abc123, name: Foo, age: 25, email: foo@langchain.dev"}]
})

# Second session: get user info
agent.invoke({
    "messages": [{"role": "user", "content": "Get user info for user with id 'abc123'"}]
})
```

> 对于生产部署，请使用持久化存储实现（如`PostgresStore`）而不是`InMemoryStore`。

#### 流写入器 (Stream Writer)

在执行期间从工具流式传输实时更新。这对于在长时间运行的操作期间向用户提供进度反馈很有用。

使用`runtime.stream_writer`发出自定义更新：

```python
from langchain.tools import tool, ToolRuntime

@tool
def get_weather(city: str, runtime: ToolRuntime) -> str:
    """Get weather for a given city."""
    writer = runtime.stream_writer

    # Stream custom updates as the tool executes
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")

    return f"It's always sunny in {city}!"
```

### ToolNode

`ToolNode`是一个预构建节点，用于在LangGraph工作流中执行工具。它自动处理并行工具执行、错误处理和状态注入。

#### 基本用法

```python
from langchain.tools import tool
from langgraph.prebuilt import ToolNode
from langgraph.graph import StateGraph, MessagesState, START, END

@tool
def search(query: str) -> str:
    """Search for information."""
    return f"Results for: {query}"

@tool
def calculator(expression: str) -> str:
    """Evaluate a math expression."""
    return str(eval(expression))

# Create the ToolNode with your tools
tool_node = ToolNode([search, calculator])

# Use in a graph
builder = StateGraph(MessagesState)
builder.add_node("tools", tool_node)
# ... add other nodes and edges
```

#### 错误处理

配置如何处理工具错误：

```python
from langgraph.prebuilt import ToolNode

# Default: catch invocation errors, re-raise execution errors
tool_node = ToolNode(tools)

# Catch all errors and return error message to LLM
tool_node = ToolNode(tools, handle_tool_errors=True)

# Custom error message
tool_node = ToolNode(tools, handle_tool_errors="Something went wrong, please try again.")

# Custom error handler
def handle_error(e: ValueError) -> str:
    return f"Invalid input: {e}"

tool_node = ToolNode(tools, handle_tool_errors=handle_error)

# Only catch specific exception types
tool_node = ToolNode(tools, handle_tool_errors=(ValueError, TypeError))
```

#### 使用tools_condition路由

使用`tools_condition`根据LLM是否进行了工具调用进行条件路由：

```python
from langgraph.prebuilt import ToolNode, tools_condition
from langgraph.graph import StateGraph, MessagesState, START, END

builder = StateGraph(MessagesState)
builder.add_node("llm", call_llm)
builder.add_node("tools", ToolNode(tools))

builder.add_edge(START, "llm")
builder.add_conditional_edges("llm", tools_condition)  # Routes to "tools" or END
builder.add_edge("tools", "llm")

graph = builder.compile()
```

#### 状态注入

工具可以通过`ToolRuntime`访问当前图状态：

```python
from langchain.tools import tool, ToolRuntime
from langgraph.prebuilt import ToolNode

@tool
def get_message_count(runtime: ToolRuntime) -> str:
    """Get the number of messages in the conversation."""
    messages = runtime.state["messages"]
    return f"There are {len(messages)} messages."

tool_node = ToolNode([get_message_count])
```

### 预构建工具

LangChain为常见任务（如网络搜索、代码解释、数据库访问等）提供了大量预构建工具和工具包。这些即用型工具可以直接集成到您的智能体中，无需编写自定义代码。

### 服务端工具使用

某些聊天模型具有由模型提供商在服务端执行的内置工具。这些包括网络搜索和代码解释器等功能，不需要您定义或托管工具逻辑。

## 8. 短期记忆 (Short-term Memory)

### 概述

记忆是一个记住有关先前交互信息的系统。对于AI智能体来说，记忆至关重要，因为它让它们能够记住先前的交互、从反馈中学习并适应用户偏好。随着智能体处理更多具有大量用户交互的复杂任务，此能力对于效率和用户满意度都变得必不可少。

短期记忆让您的应用程序能够记住单个线程或对话内的先前交互。

> 线程组织会话中的多个交互，类似于电子邮件在单个对话中分组消息的方式。

对话历史是短期记忆最常见的形式。长对话对当今的LLM构成挑战；完整的历史可能不适合LLM的上下文窗口，导致上下文丢失或错误。

即使您的模型支持完整的上下文长度，大多数LLM在长上下文上的表现仍然不佳。它们会被过时或离题的内容"分散注意力"，同时遭受响应时间变慢和成本增加的问题。

### 用法

要向智能体添加短期记忆（线程级持久化），您需要在创建智能体时指定`checkpointer`。

```python
from langchain.agents import create_agent
from langgraph.checkpoint.memory import InMemorySaver


agent = create_agent(
    "gpt-5",
    tools=[get_user_info],
    checkpointer=InMemorySaver(),
)

agent.invoke(
    {"messages": [{"role": "user", "content": "Hi! My name is Bob."}]},
    {"configurable": {"thread_id": "1"}},
)
```

#### 生产环境

在生产环境中，使用由数据库支持的检查点：

```bash
pip install langgraph-checkpoint-postgres
```

```python
from langchain.agents import create_agent
from langgraph.checkpoint.postgres import PostgresSaver


DB_URI = "postgresql://postgres:postgres@localhost:5442/postgres?sslmode=disable"
with PostgresSaver.from_conn_string(DB_URI) as checkpointer:
    checkpointer.setup() # auto create tables in PostgresSql
    agent = create_agent(
        "gpt-5",
        tools=[get_user_info],
        checkpointer=checkpointer,
    )
```

### 自定义智能体记忆

默认情况下，智能体使用`AgentState`来管理短期记忆，特别是通过`messages`键管理对话历史。

您可以扩展`AgentState`来添加额外的字段。自定义状态模式通过`state_schema`参数传递给`create_agent`。

```python
from langchain.agents import create_agent, AgentState
from langgraph.checkpoint.memory import InMemorySaver


class CustomAgentState(AgentState):
    user_id: str
    preferences: dict

agent = create_agent(
    "gpt-5",
    tools=[get_user_info],
    state_schema=CustomAgentState,
    checkpointer=InMemorySaver(),
)

# Custom state can be passed in invoke
result = agent.invoke(
    {
        "messages": [{"role": "user", "content": "Hello"}],
        "user_id": "user_123",
        "preferences": {"theme": "dark"}
    },
    {"configurable": {"thread_id": "1"}})
```

### 常见模式

启用短期记忆后，长对话可能会超出LLM的上下文窗口。常见的解决方案是：

- **裁剪消息** - 在调用LLM之前删除前N条或后N条消息
- **删除消息** - 从LangGraph状态永久删除消息
- **摘要消息** - 摘要历史中的早期消息并用摘要替换它们
- **自定义策略** - 自定义策略（如消息过滤等）

#### 裁剪消息

大多数LLM都有最大支持的上下文窗口（以token为单位）。

决定何时截断消息的一种方法是计算消息历史中的token数，并在接近该限制时进行截断。如果您使用LangChain，可以使用裁剪消息工具并指定要从列表中保留的token数，以及用于处理边界的`strategy`（例如，保留最后的`max_tokens`）。

要在智能体中裁剪消息历史，请使用`@before_model`中间件装饰器：

```python
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langgraph.runtime import Runtime
from langchain_core.runnables import RunnableConfig
from typing import Any


@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    if len(messages) <= 3:
        return None  # No changes needed

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }

agent = create_agent(
    your_model_here,
    tools=your_tools_here,
    middleware=[trim_messages],
    checkpointer=InMemorySaver(),
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}

agent.invoke({"messages": "hi, my name is bob"}, config)
agent.invoke({"messages": "write a short poem about cats"}, config)
agent.invoke({"messages": "now do the same but for dogs"}, config)
final_response = agent.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
# Your name is Bob. You told me that earlier.
```

#### 删除消息

您可以从图状态中删除消息来管理消息历史。

当您想删除特定消息或清除整个消息历史时，这很有用。

要从图状态中删除消息，可以使用`RemoveMessage`。

要使`RemoveMessage`工作，您需要使用带有`add_messages`归约器的状态键。默认的`AgentState`提供了这个。

**删除特定消息：**

```python
from langchain.messages import RemoveMessage

def delete_messages(state):
    messages = state["messages"]
    if len(messages) > 2:
        # remove the earliest two messages
        return {"messages": [RemoveMessage(id=m.id) for m in messages[:2]]}
```

**删除所有消息：**

```python
from langgraph.graph.message import REMOVE_ALL_MESSAGES

def delete_messages(state):
    return {"messages": [RemoveMessage(id=REMOVE_ALL_MESSAGES)]}
```

> 删除消息时，**请确保**生成的消息历史是有效的。检查您使用的LLM提供商的限制。例如：
> - 某些提供商期望消息历史以`user`消息开始
> - 大多数提供商要求带有工具调用的`assistant`消息后面跟着相应的`tool`结果消息

#### 摘要消息

如上所示的裁剪或删除消息的问题在于，您可能会因消息队列的删减而丢失信息。因此，某些应用程序受益于使用聊天模型摘要消息历史的更复杂方法。

要在智能体中摘要消息历史，请使用内置的`SummarizationMiddleware`：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.runnables import RunnableConfig


checkpointer = InMemorySaver()

agent = create_agent(
    model="gpt-4.1",
    tools=[],
    middleware=[
        SummarizationMiddleware(
            model="gpt-4.1-mini",
            trigger=("tokens", 4000),
            keep=("messages", 20)
        )
    ],
    checkpointer=checkpointer,
)

config: RunnableConfig = {"configurable": {"thread_id": "1"}}
agent.invoke({"messages": "hi, my name is bob"}, config)
agent.invoke({"messages": "write a short poem about cats"}, config)
agent.invoke({"messages": "now do the same but for dogs"}, config)
final_response = agent.invoke({"messages": "what's my name?"}, config)

final_response["messages"][-1].pretty_print()
# Your name is Bob!
```

### 访问记忆

您可以通过多种方式访问和修改智能体的短期记忆（状态）：

#### 在工具中读取短期记忆

使用`runtime`参数（类型为`ToolRuntime`）在工具中访问短期记忆（状态）。

`runtime`参数对工具签名是隐藏的（因此模型看不到它），但工具可以通过它访问状态。

```python
from langchain.agents import create_agent, AgentState
from langchain.tools import tool, ToolRuntime


class CustomState(AgentState):
    user_id: str

@tool
def get_user_info(
    runtime: ToolRuntime
) -> str:
    """Look up user info."""
    user_id = runtime.state["user_id"]
    return "User is John Smith" if user_id == "user_123" else "Unknown user"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_user_info],
    state_schema=CustomState,
)

result = agent.invoke({
    "messages": "look up user information",
    "user_id": "user_123"
})
print(result["messages"][-1].content)
# > User is John Smith.
```

#### 从工具写入短期记忆

要在执行期间修改智能体的短期记忆（状态），您可以直接从工具返回状态更新。

这对于持久化中间结果或使信息可供后续工具或提示使用很有用。

```python
from langchain.tools import tool, ToolRuntime
from langchain_core.runnables import RunnableConfig
from langchain.messages import ToolMessage
from langchain.agents import create_agent, AgentState
from langgraph.types import Command
from pydantic import BaseModel


class CustomState(AgentState):
    user_name: str

class CustomContext(BaseModel):
    user_id: str

@tool
def update_user_info(
    runtime: ToolRuntime[CustomContext, CustomState],
) -> Command:
    """Look up and update user info."""
    user_id = runtime.context.user_id
    name = "John Smith" if user_id == "user_123" else "Unknown user"
    return Command(update={
        "user_name": name,
        # update the message history
        "messages": [
            ToolMessage(
                "Successfully looked up user information",
                tool_call_id=runtime.tool_call_id
            )
        ]
    })

@tool
def greet(
    runtime: ToolRuntime[CustomContext, CustomState]
) -> str | Command:
    """Use this to greet the user once you found their info."""
    user_name = runtime.state.get("user_name", None)
    if user_name is None:
       return Command(update={
            "messages": [
                ToolMessage(
                    "Please call the 'update_user_info' tool it will get and update the user's name.",
                    tool_call_id=runtime.tool_call_id
                )
            ]
        })
    return f"Hello {user_name}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[update_user_info, greet],
    state_schema=CustomState,
    context_schema=CustomContext,
)

agent.invoke(
    {"messages": [{"role": "user", "content": "greet the user"}]},
    context=CustomContext(user_id="user_123"),
)
```

#### 在提示中访问

在中间件中访问短期记忆（状态），以根据对话历史或自定义状态字段创建动态提示。

```python
from langchain.agents import create_agent
from typing import TypedDict
from langchain.agents.middleware import dynamic_prompt, ModelRequest


class CustomContext(TypedDict):
    user_name: str


def get_weather(city: str) -> str:
    """Get the weather in a city."""
    return f"The weather in {city} is always sunny!"


@dynamic_prompt
def dynamic_system_prompt(request: ModelRequest) -> str:
    user_name = request.runtime.context["user_name"]
    system_prompt = f"You are a helpful assistant. Address the user as {user_name}."
    return system_prompt


agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
    middleware=[dynamic_system_prompt],
    context_schema=CustomContext,
)

result = agent.invoke(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    context=CustomContext(user_name="John Smith"),
)
```

#### 在模型调用前访问

在`@before_model`中间件中访问短期记忆（状态），以在模型调用之前处理消息。

```python
from langchain.messages import RemoveMessage
from langgraph.graph.message import REMOVE_ALL_MESSAGES
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from typing import Any


@before_model
def trim_messages(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    """Keep only the last few messages to fit context window."""
    messages = state["messages"]

    if len(messages) <= 3:
        return None  # No changes needed

    first_msg = messages[0]
    recent_messages = messages[-3:] if len(messages) % 2 == 0 else messages[-4:]
    new_messages = [first_msg] + recent_messages

    return {
        "messages": [
            RemoveMessage(id=REMOVE_ALL_MESSAGES),
            *new_messages
        ]
    }


agent = create_agent(
    "gpt-5-nano",
    tools=[],
    middleware=[trim_messages],
    checkpointer=InMemorySaver()
)
```

#### 在模型调用后访问

在`@after_model`中间件中访问短期记忆（状态），以在模型调用之后处理消息。

```python
from langchain.messages import RemoveMessage
from langgraph.checkpoint.memory import InMemorySaver
from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import after_model
from langgraph.runtime import Runtime


@after_model
def validate_response(state: AgentState, runtime: Runtime) -> dict | None:
    """Remove messages containing sensitive words."""
    STOP_WORDS = ["password", "secret"]
    last_message = state["messages"][-1]
    if any(word in last_message.content for word in STOP_WORDS):
        return {"messages": [RemoveMessage(id=last_message.id)]}
    return None

agent = create_agent(
    model="gpt-5-nano",
    tools=[],
    middleware=[validate_response],
    checkpointer=InMemorySaver(),
)
```

## 9. 流式传输 (Streaming)

LangChain实现了一个流式传输系统来提供实时更新。

流式传输对于提高基于LLM的应用程序的响应性至关重要。通过逐步显示输出，即使在完整响应准备好之前，流式传输也能显著改善用户体验（UX），特别是在处理LLM的延迟时。

### 概述

LangChain的流式传输系统让您可以将智能体运行的实时反馈显示到您的应用程序中。

LangChain流式传输可以实现：

- **流式传输智能体进度** - 在每个智能体步骤后获取状态更新
- **流式传输LLM token** - 在语言模型token生成时进行流式传输
- **流式传输自定义更新** - 发出用户定义的信号（例如，"已获取10/100条记录"）
- **流式传输多种模式** - 从`updates`（智能体进度）、`messages`（LLM token + 元数据）或`custom`（任意用户数据）中选择

### 支持的流式传输模式

将以下一个或多个流式传输模式作为列表传递给`stream`或`astream`方法：

| 模式 | 描述 |
|------|------|
| `updates` | 在每个智能体步骤后流式传输状态更新。如果在同一步骤中进行多个更新（例如，运行多个节点），这些更新将分别流式传输 |
| `messages` | 从调用LLM的任何图节点流式传输`(token, metadata)`元组 |
| `custom` | 使用流写入器从图节点内部流式传输自定义数据 |

### 智能体进度

要流式传输智能体进度，请使用`stream`或`astream`方法并设置`stream_mode="updates"`。这会在每个智能体步骤后发出一个事件。

```python
from langchain.agents import create_agent


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="updates",
):
    for step, data in chunk.items():
        print(f"step: {step}")
        print(f"content: {data['messages'][-1].content_blocks}")
```

### LLM Token

要在LLM生成token时进行流式传输，请使用`stream_mode="messages"`。

```python
from langchain.agents import create_agent


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)

for token, metadata in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="messages",
):
    print(f"node: {metadata['langgraph_node']}")
    print(f"content: {token.content_blocks}")
```

### 自定义更新

要在工具执行时流式传输更新，可以使用`get_stream_writer`。

```python
from langchain.agents import create_agent
from langgraph.config import get_stream_writer


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    writer = get_stream_writer()
    # stream any arbitrary data
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_weather],
)

for chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode="custom"
):
    print(chunk)
```

> 如果在工具内部添加`get_stream_writer`，您将无法在LangGraph执行上下文之外调用该工具。

### 流式传输多种模式

您可以通过将流式传输模式作为列表传递来指定多种流式传输模式：`stream_mode=["updates", "custom"]`。

流式传输的输出将是`(mode, chunk)`元组，其中`mode`是流式传输模式的名称，`chunk`是该模式流式传输的数据。

```python
from langchain.agents import create_agent
from langgraph.config import get_stream_writer


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    writer = get_stream_writer()
    writer(f"Looking up data for city: {city}")
    writer(f"Acquired data for city: {city}")
    return f"It's always sunny in {city}!"

agent = create_agent(
    model="gpt-5-nano",
    tools=[get_weather],
)

for stream_mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "What is the weather in SF?"}]},
    stream_mode=["updates", "custom"]
):
    print(f"stream_mode: {stream_mode}")
    print(f"content: {chunk}")
```

### 常见模式

#### 流式传输工具调用

您可能希望同时流式传输：

1. 生成工具调用时的部分JSON
2. 已完成、已解析并执行的工具调用

指定`stream_mode="messages"`将流式传输智能体中所有LLM调用生成的增量消息块。要访问带有已解析工具调用的已完成消息：

1. 如果这些消息在状态中跟踪（如`create_agent`的模型节点），使用`stream_mode=["messages", "updates"]`通过状态更新访问已完成消息
2. 如果这些消息不在状态中跟踪，使用自定义更新或在流式传输循环期间聚合块

```python
from typing import Any

from langchain.agents import create_agent
from langchain.messages import AIMessage, AIMessageChunk, AnyMessage, ToolMessage


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


agent = create_agent("openai:gpt-5.2", tools=[get_weather])


def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)


def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")


input_message = {"role": "user", "content": "What is the weather in Boston?"}
for stream_mode, data in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates"],
):
    if stream_mode == "messages":
        token, metadata = data
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    if stream_mode == "updates":
        for source, update in data.items():
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
```

#### 流式传输与人机交互

要处理人机交互中断，我们基于上面的示例构建：

1. 我们使用人机交互中间件和检查点配置智能体
2. 我们收集在`"updates"`流式传输模式期间生成的中断
3. 我们使用命令响应这些中断

```python
from typing import Any

from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langchain.messages import AIMessage, AIMessageChunk, AnyMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command, Interrupt


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


checkpointer = InMemorySaver()

agent = create_agent(
    "openai:gpt-5.2",
    tools=[get_weather],
    middleware=[
        HumanInTheLoopMiddleware(interrupt_on={"get_weather": True}),
    ],
    checkpointer=checkpointer,
)


def _render_message_chunk(token: AIMessageChunk) -> None:
    if token.text:
        print(token.text, end="|")
    if token.tool_call_chunks:
        print(token.tool_call_chunks)


def _render_completed_message(message: AnyMessage) -> None:
    if isinstance(message, AIMessage) and message.tool_calls:
        print(f"Tool calls: {message.tool_calls}")
    if isinstance(message, ToolMessage):
        print(f"Tool response: {message.content_blocks}")


def _render_interrupt(interrupt: Interrupt) -> None:
    interrupts = interrupt.value
    for request in interrupts["action_requests"]:
        print(request["description"])


input_message = {
    "role": "user",
    "content": "Can you look up the weather in Boston and San Francisco?",
}
config = {"configurable": {"thread_id": "some_id"}}
interrupts = []
for stream_mode, data in agent.stream(
    {"messages": [input_message]},
    config=config,
    stream_mode=["messages", "updates"],
):
    if stream_mode == "messages":
        token, metadata = data
        if isinstance(token, AIMessageChunk):
            _render_message_chunk(token)
    if stream_mode == "updates":
        for source, update in data.items():
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
            if source == "__interrupt__":
                interrupts.extend(update)
                _render_interrupt(update[0])
```

#### 从子智能体流式传输

当智能体中任何点有多个LLM时，通常需要在生成消息时消除消息来源的歧义。

为此，在创建每个智能体时传递一个`name`。然后，在`"messages"`模式下流式传输时，该名称可通过`lc_agent_name`键在元数据中使用。

```python
from typing import Any

from langchain.agents import create_agent
from langchain.chat_models import init_chat_model
from langchain.messages import AIMessage, AnyMessage


def get_weather(city: str) -> str:
    """Get weather for a given city."""
    return f"It's always sunny in {city}!"


weather_model = init_chat_model("openai:gpt-5.2")
weather_agent = create_agent(
    model=weather_model,
    tools=[get_weather],
    name="weather_agent",
)


def call_weather_agent(query: str) -> str:
    """Query the weather agent."""
    result = weather_agent.invoke({
        "messages": [{"role": "user", "content": query}]
    })
    return result["messages"][-1].text


supervisor_model = init_chat_model("openai:gpt-5.2")
agent = create_agent(
    model=supervisor_model,
    tools=[call_weather_agent],
    name="supervisor",
)
```

然后，我们在流式传输循环中添加逻辑来报告哪个智能体正在发出token：

```python
input_message = {"role": "user", "content": "What is the weather in Boston?"}
current_agent = None
for _, stream_mode, data in agent.stream(
    {"messages": [input_message]},
    stream_mode=["messages", "updates"],
    subgraphs=True,
):
    if stream_mode == "messages":
        token, metadata = data
        if agent_name := metadata.get("lc_agent_name"):
            if agent_name != current_agent:
                print(f"🤖 {agent_name}: ")
                current_agent = agent_name
        if isinstance(token, AIMessage):
            _render_message_chunk(token)
    if stream_mode == "updates":
        for source, update in data.items():
            if source in ("model", "tools"):
                _render_completed_message(update["messages"][-1])
```

### 禁用流式传输

在某些应用程序中，您可能需要禁用特定模型的单个token流式传输。这在以下情况下很有用：

- 使用多智能体系统来控制哪些智能体流式传输其输出
- 混合支持流式传输的模型和不支持流式传输的模型
- 部署到LangSmith并希望防止某些模型输出流式传输到客户端

在初始化模型时设置`streaming=False`。

```python
from langchain_openai import ChatOpenAI

model = ChatOpenAI(
    model="gpt-4.1",
    streaming=False
)
```

> 在部署到LangSmith时，对任何您不希望流式传输到客户端的模型设置`streaming=False`。这是在部署之前在图代码中配置的。

## 10. 结构化输出 (Structured Output)

结构化输出允许智能体以特定、可预测的格式返回数据。您不需要解析自然语言响应，而是获得JSON对象、Pydantic模型或数据类形式的结构化数据，您的应用程序可以直接使用。

LangChain的`create_agent`自动处理结构化输出。用户设置所需的结构化输出模式，当模型生成结构化数据时，它会被捕获、验证并返回在智能体状态的`'structured_response'`键中。

### 响应格式

使用`response_format`控制智能体如何返回结构化数据：

- **`ToolStrategy[StructuredResponseT]`**：使用工具调用进行结构化输出
- **`ProviderStrategy[StructuredResponseT]`**：使用提供商原生结构化输出
- **`type[StructuredResponseT]`**：模式类型 - 根据模型能力自动选择最佳策略
- **`None`**：未显式请求结构化输出

当直接提供模式类型时，LangChain自动选择：

- 如果所选模型和提供商支持原生结构化输出（如OpenAI、Anthropic (Claude)或xAI (Grok)），则使用`ProviderStrategy`
- 对于所有其他模型，使用`ToolStrategy`

结构化响应在智能体最终状态的`structured_response`键中返回。

### 提供商策略 (Provider Strategy)

某些模型提供商通过其API原生支持结构化输出（如OpenAI、xAI (Grok)、Gemini、Anthropic (Claude)）。这是可用时最可靠的方法。

```python
class ProviderStrategy(Generic[SchemaT]):
    schema: type[SchemaT]
    strict: bool | None = None
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `schema` | type | 定义结构化输出格式的模式。支持Pydantic模型、数据类、TypedDict、JSON Schema |
| `strict` | bool | 可选布尔参数，用于启用严格模式遵守。某些提供商支持（如OpenAI和xAI）。默认为`None`（禁用） |

**使用Pydantic模型：**

```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent


class ContactInfo(BaseModel):
    """Contact information for a person."""
    name: str = Field(description="The name of the person")
    email: str = Field(description="The email address of the person")
    phone: str = Field(description="The phone number of the person")

agent = create_agent(
    model="gpt-5",
    response_format=ContactInfo  # Auto-selects ProviderStrategy
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Extract contact info from: John Doe, john@example.com, (555) 123-4567"}]
})

print(result["structured_response"])
# ContactInfo(name='John Doe', email='john@example.com', phone='(555) 123-4567')
```

**使用数据类：**

```python
from dataclasses import dataclass
from langchain.agents import create_agent


@dataclass
class ContactInfo:
    """Contact information for a person."""
    name: str
    email: str
    phone: str

agent = create_agent(
    model="gpt-5",
    tools=tools,
    response_format=ContactInfo
)

result["structured_response"]
# {'name': 'John Doe', 'email': 'john@example.com', 'phone': '(555) 123-4567'}
```

**使用TypedDict：**

```python
from typing_extensions import TypedDict
from langchain.agents import create_agent


class ContactInfo(TypedDict):
    """Contact information for a person."""
    name: str
    email: str
    phone: str

agent = create_agent(
    model="gpt-5",
    tools=tools,
    response_format=ContactInfo
)
```

**使用JSON Schema：**

```python
from langchain.agents import create_agent


contact_info_schema = {
    "type": "object",
    "description": "Contact information for a person.",
    "properties": {
        "name": {"type": "string", "description": "The name of the person"},
        "email": {"type": "string", "description": "The email address of the person"},
        "phone": {"type": "string", "description": "The phone number of the person"}
    },
    "required": ["name", "email", "phone"]
}

agent = create_agent(
    model="gpt-5",
    tools=tools,
    response_format=ProviderStrategy(contact_info_schema)
)
```

### 工具调用策略 (Tool Calling Strategy)

对于不支持原生结构化输出的模型，LangChain使用工具调用来实现相同的结果。这适用于所有支持工具调用的模型（大多数现代模型）。

```python
class ToolStrategy(Generic[SchemaT]):
    schema: type[SchemaT]
    tool_message_content: str | None
    handle_errors: Union[bool, str, type[Exception], tuple[type[Exception], ...], Callable[[Exception], str]]
```

**参数：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `schema` | type | 定义结构化输出格式的模式 |
| `tool_message_content` | str | 生成结构化输出时返回的工具消息的自定义内容 |
| `handle_errors` | bool/str/type/tuple/callable | 结构化输出验证失败的错误处理策略。默认为`True` |

**使用示例：**

```python
from pydantic import BaseModel, Field
from typing import Literal
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy


class ProductReview(BaseModel):
    """Analysis of a product review."""
    rating: int | None = Field(description="The rating of the product", ge=1, le=5)
    sentiment: Literal["positive", "negative"] = Field(description="The sentiment of the review")
    key_points: list[str] = Field(description="The key points of the review")

agent = create_agent(
    model="gpt-5",
    tools=tools,
    response_format=ToolStrategy(ProductReview)
)

result = agent.invoke({
    "messages": [{"role": "user", "content": "Analyze this review: 'Great product: 5 out of 5 stars. Fast shipping, but expensive'"}]
})
result["structured_response"]
# ProductReview(rating=5, sentiment='positive', key_points=['fast shipping', 'expensive'])
```

**使用Union类型：**

```python
from pydantic import BaseModel, Field
from typing import Literal, Union
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy


class ProductReview(BaseModel):
    """Analysis of a product review."""
    rating: int | None = Field(description="The rating of the product", ge=1, le=5)
    sentiment: Literal["positive", "negative"] = Field(description="The sentiment of the review")
    key_points: list[str] = Field(description="The key points of the review")

class CustomerComplaint(BaseModel):
    """A customer complaint about a product or service."""
    issue_type: Literal["product", "service", "shipping", "billing"] = Field(description="The type of issue")
    severity: Literal["low", "medium", "high"] = Field(description="The severity of the complaint")
    description: str = Field(description="Brief description of the complaint")

agent = create_agent(
    model="gpt-5",
    tools=tools,
    response_format=ToolStrategy(Union[ProductReview, CustomerComplaint])
)
```

### 自定义工具消息内容

`tool_message_content`参数允许您自定义生成结构化输出时出现在对话历史中的消息：

```python
from pydantic import BaseModel, Field
from typing import Literal
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy


class MeetingAction(BaseModel):
    """Action items extracted from a meeting transcript."""
    task: str = Field(description="The specific task to be completed")
    assignee: str = Field(description="Person responsible for the task")
    priority: Literal["low", "medium", "high"] = Field(description="Priority level")

agent = create_agent(
    model="gpt-5",
    tools=[],
    response_format=ToolStrategy(
        schema=MeetingAction,
        tool_message_content="Action item captured and added to meeting notes!"
    )
)

agent.invoke({
    "messages": [{"role": "user", "content": "From our meeting: Sarah needs to update the project timeline as soon as possible"}]
})
```

### 错误处理

模型在通过工具调用生成结构化输出时可能会犯错误。LangChain提供智能重试机制来自动处理这些错误。

#### 多个结构化输出错误

当模型错误地调用多个结构化输出工具时，智能体在`ToolMessage`中提供错误反馈并提示模型重试：

```python
from pydantic import BaseModel, Field
from typing import Union
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy


class ContactInfo(BaseModel):
    name: str = Field(description="Person's name")
    email: str = Field(description="Email address")

class EventDetails(BaseModel):
    event_name: str = Field(description="Name of the event")
    date: str = Field(description="Event date")

agent = create_agent(
    model="gpt-5",
    tools=[],
    response_format=ToolStrategy(Union[ContactInfo, EventDetails])  # Default: handle_errors=True
)

agent.invoke({
    "messages": [{"role": "user", "content": "Extract info: John Doe (john@email.com) is organizing Tech Conference on March 15th"}]
})
```

#### 模式验证错误

当结构化输出与预期模式不匹配时，智能体提供特定的错误反馈：

```python
from pydantic import BaseModel, Field
from langchain.agents import create_agent
from langchain.agents.structured_output import ToolStrategy


class ProductRating(BaseModel):
    rating: int | None = Field(description="Rating from 1-5", ge=1, le=5)
    comment: str = Field(description="Review comment")

agent = create_agent(
    model="gpt-5",
    tools=[],
    response_format=ToolStrategy(ProductRating),  # Default: handle_errors=True
    system_prompt="You are a helpful assistant that parses product reviews. Do not make any field or value up."
)

agent.invoke({
    "messages": [{"role": "user", "content": "Parse this: Amazing product, 10/10!"}]
})
```

#### 错误处理策略

您可以使用`handle_errors`参数自定义如何处理错误：

**自定义错误消息：**

```python
ToolStrategy(
    schema=ProductRating,
    handle_errors="Please provide a valid rating between 1-5 and include a comment."
)
```

**仅处理特定异常：**

```python
ToolStrategy(
    schema=ProductRating,
    handle_errors=ValueError  # Only retry on ValueError, raise others
)
```

**处理多个异常类型：**

```python
ToolStrategy(
    schema=ProductRating,
    handle_errors=(ValueError, TypeError)  # Retry on ValueError and TypeError
)
```

**自定义错误处理函数：**

```python
from langchain.agents.structured_output import StructuredOutputValidationError
from langchain.agents.structured_output import MultipleStructuredOutputsError

def custom_error_handler(error: Exception) -> str:
    if isinstance(error, StructuredOutputValidationError):
        return "There was an issue with the format. Try again."
    elif isinstance(error, MultipleStructuredOutputsError):
        return "Multiple structured outputs were returned. Pick the most relevant one."
    else:
        return f"Error: {str(error)}"


agent = create_agent(
    model="gpt-5",
    tools=[],
    response_format=ToolStrategy(
        schema=Union[ContactInfo, EventDetails],
        handle_errors=custom_error_handler
    )
)
```

**无错误处理：**

```python
response_format = ToolStrategy(
    schema=ProductRating,
    handle_errors=False  # All errors raised
)
```

## 11. 中间件 (Middleware)

中间件提供了一种更严格地控制智能体内部发生情况的方法。中间件在以下方面很有用：

- 通过日志记录、分析和调试来跟踪智能体行为
- 转换提示词、工具选择和输出格式
- 添加重试、备用方案和提前终止逻辑
- 应用速率限制、防护措施和个人身份信息检测

### 添加中间件

通过将中间件传递给`create_agent`来添加：

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware, HumanInTheLoopMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[...],
    middleware=[
        SummarizationMiddleware(...),
        HumanInTheLoopMiddleware(...)
    ],
)
```

### 预构建中间件

LangChain为常见用例提供预构建的中间件。每个中间件都是生产就绪的，可根据您的特定需求进行配置。

#### 提供商无关的中间件

| 中间件 | 描述 |
|--------|------|
| [摘要](#摘要-summarization) | 接近token限制时自动摘要对话历史 |
| [人机交互](#人机交互-human-in-the-loop) | 暂停执行以等待人工审批工具调用 |
| [模型调用限制](#模型调用限制-model-call-limit) | 限制模型调用次数以防止过度成本 |
| [工具调用限制](#工具调用限制-tool-call-limit) | 通过限制调用次数控制工具执行 |
| [模型备用](#模型备用-model-fallback) | 主模型失败时自动切换到备用模型 |
| [PII检测](#pii检测-pii-detection) | 检测和处理个人身份信息 |
| [待办事项列表](#待办事项列表-to-do-list) | 为智能体配备任务规划和跟踪能力 |
| [LLM工具选择器](#llm工具选择器-llm-tool-selector) | 在调用主模型前使用LLM选择相关工具 |
| [工具重试](#工具重试-tool-retry) | 使用指数退避自动重试失败的工具调用 |
| [模型重试](#模型重试-model-retry) | 使用指数退避自动重试失败的模型调用 |
| [LLM工具模拟器](#llm工具模拟器-llm-tool-emulator) | 使用LLM模拟工具执行以进行测试 |
| [上下文编辑](#上下文编辑-context-editing) | 通过修剪或清除工具使用来管理对话上下文 |
| [Shell工具](#shell工具-shell-tool) | 向智能体公开持久shell会话以执行命令 |
| [文件搜索](#文件搜索-file-search) | 在文件系统文件上提供Glob和Grep搜索工具 |

#### 摘要 (Summarization)

接近token限制时自动摘要对话历史，保留最近的消息同时压缩较旧的上下文。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import SummarizationMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[your_weather_tool, your_calculator_tool],
    middleware=[
        SummarizationMiddleware(
            model="gpt-4.1-mini",
            trigger=("tokens", 4000),
            keep=("messages", 20),
        ),
    ],
)
```

**配置选项：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `model` | string \| BaseChatModel | 用于生成摘要的模型 |
| `trigger` | ContextSize | 触发摘要的条件（fraction/tokens/messages） |
| `keep` | ContextSize | 摘要后保留多少上下文 |
| `token_counter` | function | 自定义token计数函数 |
| `summary_prompt` | string | 摘要的自定义提示模板 |

#### 人机交互 (Human-in-the-loop)

暂停智能体执行以等待人工批准、编辑或拒绝工具调用。

> 人机交互中间件需要检查点来跨中断维护状态。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-4.1",
    tools=[your_read_email_tool, your_send_email_tool],
    checkpointer=InMemorySaver(),
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "your_send_email_tool": {
                    "allowed_decisions": ["approve", "edit", "reject"],
                },
                "your_read_email_tool": False,
            }
        ),
    ],
)
```

#### 模型调用限制 (Model Call Limit)

限制模型调用次数以防止无限循环或过度成本。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelCallLimitMiddleware
from langgraph.checkpoint.memory import InMemorySaver

agent = create_agent(
    model="gpt-4.1",
    checkpointer=InMemorySaver(),
    tools=[],
    middleware=[
        ModelCallLimitMiddleware(
            thread_limit=10,
            run_limit=5,
            exit_behavior="end",
        ),
    ],
)
```

**配置选项：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `thread_limit` | number | 线程中所有运行的最大模型调用次数 |
| `run_limit` | number | 单次调用的最大模型调用次数 |
| `exit_behavior` | string | 达到限制时的行为：`'end'`或`'error'` |

#### 工具调用限制 (Tool Call Limit)

通过限制工具调用次数控制智能体执行。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolCallLimitMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[search_tool, database_tool],
    middleware=[
        ToolCallLimitMiddleware(thread_limit=20, run_limit=10),
        ToolCallLimitMiddleware(
            tool_name="search",
            thread_limit=5,
            run_limit=3,
        ),
    ],
)
```

**配置选项：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `tool_name` | string | 要限制的特定工具名称 |
| `thread_limit` | number | 线程中所有运行的最大工具调用次数 |
| `run_limit` | number | 单次调用的最大工具调用次数 |
| `exit_behavior` | string | 达到限制时的行为：`'continue'`/`'error'`/`'end'` |

#### 模型备用 (Model Fallback)

主模型失败时自动切换到备用模型。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelFallbackMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[],
    middleware=[
        ModelFallbackMiddleware(
            "gpt-4.1-mini",
            "claude-3-5-sonnet-20241022",
        ),
    ],
)
```

#### PII检测 (PII Detection)

使用可配置策略检测和处理对话中的个人身份信息。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import PIIMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[],
    middleware=[
        PIIMiddleware("email", strategy="redact", apply_to_input=True),
        PIIMiddleware("credit_card", strategy="mask", apply_to_input=True),
    ],
)
```

**配置选项：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `pii_type` | string | 要检测的PII类型（email/credit_card/ip等） |
| `strategy` | string | 处理策略：`block`/`redact`/`mask`/`hash` |
| `detector` | function \| regex | 自定义检测器函数或正则表达式模式 |
| `apply_to_input` | boolean | 在模型调用前检查用户消息 |
| `apply_to_output` | boolean | 在模型调用后检查AI消息 |

**自定义PII类型：**

```python
# 使用正则表达式模式
agent = create_agent(
    model="gpt-4.1",
    tools=[],
    middleware=[
        PIIMiddleware(
            "api_key",
            detector=r"sk-[a-zA-Z0-9]{32}",
            strategy="block",
        ),
    ],
)

# 使用自定义检测器函数
def detect_ssn(content: str) -> list[dict]:
    matches = []
    pattern = r"\d{3}-\d{2}-\d{4}"
    for match in re.finditer(pattern, content):
        matches.append({
            "text": match.group(0),
            "start": match.start(),
            "end": match.end(),
        })
    return matches

agent = create_agent(
    model="gpt-4.1",
    tools=[],
    middleware=[
        PIIMiddleware("ssn", detector=detect_ssn, strategy="hash"),
    ],
)
```

#### 待办事项列表 (To-do List)

为智能体配备复杂多步骤任务的任务规划和跟踪能力。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import TodoListMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[read_file, write_file, run_tests],
    middleware=[TodoListMiddleware()],
)
```

#### LLM工具选择器 (LLM Tool Selector)

在调用主模型前使用LLM智能选择相关工具。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolSelectorMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[tool1, tool2, tool3, tool4, tool5, ...],
    middleware=[
        LLMToolSelectorMiddleware(
            model="gpt-4.1-mini",
            max_tools=3,
            always_include=["search"],
        ),
    ],
)
```

#### 工具重试 (Tool Retry)

使用可配置的指数退避自动重试失败的工具调用。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ToolRetryMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[search_tool, database_tool],
    middleware=[
        ToolRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
        ),
    ],
)
```

**配置选项：**

| 参数 | 类型 | 说明 |
|------|------|------|
| `max_retries` | number | 初始调用后的最大重试次数（默认2） |
| `tools` | list | 要应用重试逻辑的工具列表 |
| `retry_on` | tuple \| callable | 要重试的异常类型或判断函数 |
| `on_failure` | string \| callable | 所有重试耗尽时的行为 |
| `backoff_factor` | number | 指数退避乘数（默认2.0） |
| `initial_delay` | number | 首次重试前的初始延迟秒数 |
| `max_delay` | number | 重试之间的最大延迟秒数 |
| `jitter` | boolean | 是否添加随机抖动以避免惊群效应 |

#### 模型重试 (Model Retry)

使用可配置的指数退避自动重试失败的模型调用。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ModelRetryMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[search_tool, database_tool],
    middleware=[
        ModelRetryMiddleware(
            max_retries=3,
            backoff_factor=2.0,
            initial_delay=1.0,
        ),
    ],
)
```

#### LLM工具模拟器 (LLM Tool Emulator)

使用LLM模拟工具执行以进行测试。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import LLMToolEmulator

agent = create_agent(
    model="gpt-4.1",
    tools=[get_weather, search_database, send_email],
    middleware=[
        LLMToolEmulator(),  # 模拟所有工具
    ],
)
```

#### 上下文编辑 (Context Editing)

通过清除较旧的工具调用输出来管理对话上下文。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import ContextEditingMiddleware, ClearToolUsesEdit

agent = create_agent(
    model="gpt-4.1",
    tools=[],
    middleware=[
        ContextEditingMiddleware(
            edits=[
                ClearToolUsesEdit(
                    trigger=100000,
                    keep=3,
                ),
            ],
        ),
    ],
)
```

#### Shell工具 (Shell Tool)

向智能体公开持久shell会话以执行命令。

> **安全考虑**：使用适当的执行策略（HostExecutionPolicy、DockerExecutionPolicy或CodexSandboxExecutionPolicy）来匹配您的部署安全要求。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import (
    ShellToolMiddleware,
    HostExecutionPolicy,
)

agent = create_agent(
    model="gpt-4.1",
    tools=[search_tool],
    middleware=[
        ShellToolMiddleware(
            workspace_root="/workspace",
            execution_policy=HostExecutionPolicy(),
        ),
    ],
)
```

#### 文件搜索 (File Search)

在文件系统上提供Glob和Grep搜索工具。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import FilesystemFileSearchMiddleware

agent = create_agent(
    model="gpt-4.1",
    tools=[],
    middleware=[
        FilesystemFileSearchMiddleware(
            root_path="/workspace",
            use_ripgrep=True,
        ),
    ],
)
```

### 提供商特定中间件

这些中间件针对特定LLM提供商进行了优化：

- **Anthropic** - 提示缓存、bash工具、文本编辑器、内存和文件搜索中间件
- **OpenAI** - OpenAI模型的内容审核中间件

### 自定义中间件

通过实现钩子构建自定义中间件，这些钩子在智能体执行流程的特定点运行。

#### 钩子类型

中间件提供两种风格的钩子来拦截智能体执行：

**节点风格钩子** - 在特定执行点顺序运行。用于日志记录、验证和状态更新。

可用钩子：
- `before_agent` - 智能体启动前（每次调用一次）
- `before_model` - 每次模型调用前
- `after_model` - 每次模型响应后
- `after_agent` - 智能体完成后（每次调用一次）

**包装风格钩子** - 在每个模型或工具调用周围运行。用于重试、缓存和转换。

可用钩子：
- `wrap_model_call` - 每次模型调用周围
- `wrap_tool_call` - 每次工具调用周围

#### 创建中间件

**装饰器方式** - 快速简单，适用于单钩子中间件。

```python
from langchain.agents.middleware import (
    before_model,
    wrap_model_call,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langchain.agents import create_agent
from langgraph.runtime import Runtime
from typing import Any, Callable


@before_model
def log_before_model(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    print(f"About to call model with {len(state['messages'])} messages")
    return None

@wrap_model_call
def retry_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    for attempt in range(3):
        try:
            return handler(request)
        except Exception as e:
            if attempt == 2:
                raise
            print(f"Retry {attempt + 1}/3 after error: {e}")

agent = create_agent(
    model="gpt-4.1",
    middleware=[log_before_model, retry_model],
    tools=[...],
)
```

**类方式** - 更强大，适用于复杂中间件或多个钩子。

```python
from langchain.agents.middleware import (
    AgentMiddleware,
    AgentState,
    ModelRequest,
    ModelResponse,
)
from langgraph.runtime import Runtime
from typing import Any, Callable

class LoggingMiddleware(AgentMiddleware):
    def before_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        print(f"About to call model with {len(state['messages'])} messages")
        return None

    def after_model(self, state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
        print(f"Model returned: {state['messages'][-1].content}")
        return None

agent = create_agent(
    model="gpt-4.1",
    middleware=[LoggingMiddleware()],
    tools=[...],
)
```

#### 自定义状态模式

中间件可以使用自定义属性扩展智能体的状态：

```python
from langchain.agents import create_agent
from langchain.messages import HumanMessage
from langchain.agents.middleware import AgentState, AgentMiddleware, before_model, after_model
from typing_extensions import NotRequired
from typing import Any


class CustomState(AgentState):
    model_call_count: NotRequired[int]
    user_id: NotRequired[str]


class CallCounterMiddleware(AgentMiddleware[CustomState]):
    state_schema = CustomState

    def before_model(self, state: CustomState, runtime) -> dict[str, Any] | None:
        count = state.get("model_call_count", 0)
        if count > 10:
            return {"jump_to": "end"}
        return None

    def after_model(self, state: CustomState, runtime) -> dict[str, Any] | None:
        return {"model_call_count": state.get("model_call_count", 0) + 1}


agent = create_agent(
    model="gpt-4.1",
    middleware=[CallCounterMiddleware()],
    tools=[],
)
```

#### 执行顺序

使用多个中间件时，执行顺序如下：

```python
agent = create_agent(
    model="gpt-4.1",
    middleware=[middleware1, middleware2, middleware3],
    tools=[...],
)
```

- `before_*` 钩子：从第一个到最后一个
- `after_*` 钩子：从最后一个到第一个（反向）
- `wrap_*` 钩子：嵌套（第一个中间件包装所有其他）

#### 智能体跳转

要从中间件提前退出，返回带有`jump_to`的字典：

可用跳转目标：
- `'end'`：跳到智能体执行结束
- `'tools'`：跳到工具节点
- `'model'`：跳到模型节点

```python
from langchain.agents.middleware import after_model, hook_config, AgentState
from langchain.messages import AIMessage
from langgraph.runtime import Runtime
from typing import Any


@after_model
@hook_config(can_jump_to=["end"])
def check_for_blocked(state: AgentState, runtime: Runtime) -> dict[str, Any] | None:
    last_message = state["messages"][-1]
    if "BLOCKED" in last_message.content:
        return {
            "messages": [AIMessage("I cannot respond to that request.")],
            "jump_to": "end"
        }
    return None
```

#### 最佳实践

1. 保持中间件专注 - 每个中间件应该只做一件事
2. 优雅地处理错误 - 不要让中间件错误导致智能体崩溃
3. 使用适当的钩子类型：
   - 节点风格用于顺序逻辑（日志记录、验证）
   - 包装风格用于控制流（重试、备用、缓存）
4. 清楚地记录任何自定义状态属性
5. 在集成之前独立地对中间件进行单元测试
6. 考虑执行顺序 - 将关键中间件放在列表前面
7. 尽可能使用内置中间件

#### 示例

**动态模型选择**

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.chat_models import init_chat_model
from typing import Callable


complex_model = init_chat_model("gpt-4.1")
simple_model = init_chat_model("gpt-4.1-mini")

@wrap_model_call
def dynamic_model(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    # Use different model based on conversation length
    if len(request.messages) > 10:
        model = complex_model
    else:
        model = simple_model
    return handler(request.override(model=model))
```

**工具调用监控**

```python
from langchain.agents.middleware import wrap_tool_call
from langchain.tools.tool_node import ToolCallRequest
from langchain.messages import ToolMessage
from langgraph.types import Command
from typing import Callable


@wrap_tool_call
def monitor_tool(
    request: ToolCallRequest,
    handler: Callable[[ToolCallRequest], ToolMessage | Command],
) -> ToolMessage | Command:
    print(f"Executing tool: {request.tool_call['name']}")
    print(f"Arguments: {request.tool_call['args']}")
    try:
        result = handler(request)
        print(f"Tool completed successfully")
        return result
    except Exception as e:
        print(f"Tool failed: {e}")
        raise
```

**动态选择工具**

```python
from langchain.agents import create_agent
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable


@wrap_model_call
def select_tools(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Middleware to select relevant tools based on state/context."""
    # Select a small, relevant subset of tools based on state/context
    relevant_tools = select_relevant_tools(request.state, request.runtime)
    return handler(request.override(tools=relevant_tools))

agent = create_agent(
    model="gpt-4.1",
    tools=all_tools,
    middleware=[select_tools],
)
```

**使用系统消息**

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from typing import Callable


@wrap_model_call
def add_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    # Always work with content blocks
    new_content = list(request.system_message.content_blocks) + [
        {"type": "text", "text": "Additional context."}
    ]
    new_system_message = SystemMessage(content=new_content)
    return handler(request.override(system_message=new_system_message))
```

## 12. 运行时 (Runtime)

运行时 API 允许你在工具和中间件中访问上下文、存储和流写入器。这使你能够：

- 在工具中访问智能体状态和配置
- 使用存储进行跨会话持久化
- 从工具和中间件中流式传输自定义数据

### 在工具中访问运行时

在工具中使用 `Runtime.ensure()` 来访问运行时上下文：

```python
from langchain.tools import tool
from langchain.agents.runtime import Runtime


@tool
def my_tool(query: str) -> str:
    """A tool that uses runtime context."""
    runtime = Runtime.ensure()

    # 访问智能体状态
    state = runtime.state
    messages = state["messages"]

    # 访问配置
    config = runtime.config
    user_id = config["configurable"]["user_id"]

    # 访问存储
    store = runtime.store
    namespace = ("users", user_id)
    user_data = store.get(namespace, "preferences")

    return f"Found {len(messages)} messages for user {user_id}"
```

### 运行时属性

运行时对象提供对以下内容的访问：

| 属性 | 描述 |
|------|------|
| `state` | 当前智能体状态（消息、上下文等） |
| `config` | 运行时配置（可配置参数、线程 ID 等） |
| `store` | 用于持久化的键值存储 |
| `stream_writer` | 用于流式传输自定义数据 |
| `callbacks` | 回调处理器 |

### 流式传输自定义数据

使用 `stream_writer` 从工具中流式传输自定义数据：

```python
from langchain.tools import tool
from langchain.agents.runtime import Runtime


@tool
def search_tool(query: str) -> str:
    """Search with streaming progress updates."""
    runtime = Runtime.ensure()
    writer = runtime.stream_writer

    # 流式传输进度更新
    writer("Searching database...")
    results = search_database(query)

    writer("Ranking results...")
    ranked = rank_results(results)

    writer("Formatting output...")
    return format_results(ranked)
```

在调用智能体时使用 `"custom"` 流模式来接收这些更新：

```python
async for chunk in agent.astream(
    {"messages": [{"role": "user", "content": "search for X"}]},
    stream_mode="custom",
):
    print(chunk)  # 来自 writer() 的自定义数据
```

### 在中间件中访问运行时

中间件可以通过请求对象访问运行时：

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable


@wrap_model_call
def log_to_store(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    runtime = request.runtime

    # 记录到存储
    store = runtime.store
    namespace = ("logs", "model_calls")
    store.put(
        namespace,
        key=f"call_{time.time()}",
        value={
            "messages": len(request.messages),
            "tools": [t.name for t in request.tools],
        },
    )

    return handler(request)
```

### 使用存储

存储提供了用于跨会话持久化数据的键值接口：

```python
from langchain.tools import tool
from langchain.agents.runtime import Runtime


@tool
def remember_fact(fact: str) -> str:
    """Remember a fact for later."""
    runtime = Runtime.ensure()
    store = runtime.store

    # 获取用户 ID
    user_id = runtime.config["configurable"]["user_id"]

    # 存储数据
    namespace = ("user_facts", user_id)
    existing = store.get(namespace, "facts") or {"facts": []}
    existing["facts"].append(fact)
    store.put(namespace, key="facts", value=existing)

    return f"Remembered: {fact}"


@tool
def recall_facts() -> str:
    """Recall previously remembered facts."""
    runtime = Runtime.ensure()
    store = runtime.store

    user_id = runtime.config["configurable"]["user_id"]
    namespace = ("user_facts", user_id)
    data = store.get(namespace, "facts")

    if not data:
        return "No facts remembered yet."

    return "Remembered facts:\n" + "\n".join(f"- {f}" for f in data["facts"])
```

### 配置运行时

在创建智能体时配置存储和其他运行时选项：

```python
from langchain.agents import create_agent
from langgraph.store.memory import InMemoryStore


agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[remember_fact, recall_facts],
    store=InMemoryStore(),  # 为生产环境使用持久化存储
)

# 使用配置调用
result = agent.invoke(
    {"messages": [{"role": "user", "content": "remember that I like pizza"}]},
    config={"configurable": {"user_id": "user123"}},
)
```

### 最佳实践

1. **运行时可用性**：在工具中始终使用 `Runtime.ensure()`，如果不在智能体上下文中运行，它会优雅地失败
2. **命名空间**：为存储键使用一致的命名空间，以避免冲突
3. **流式传输**：使用流写入器提供有意义的进度更新，而不是详细日志
4. **配置**：将用户/会话特定的数据放在 `config["configurable"]` 中

## 13. 上下文工程 (Context Engineering)

上下文工程是关于有效管理模型、工具和中间件中的上下文（对话历史、系统指令等）。本节介绍管理上下文的最佳实践。

### 模型上下文

模型上下文包括发送给 LLM 的消息和系统指令。

#### 访问消息

在工具和中间件中，你可以通过运行时访问当前消息：

```python
from langchain.tools import tool
from langchain.agents.runtime import Runtime


@tool
def summarize_conversation() -> str:
    """Summarize the conversation so far."""
    runtime = Runtime.ensure()
    messages = runtime.state["messages"]

    # 计算对话长度
    total_chars = sum(len(str(m.content)) for m in messages)

    return f"Conversation has {len(messages)} messages, {total_chars} characters"
```

#### 修改系统消息

中间件可以修改发送给模型的系统消息：

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from langchain.messages import SystemMessage
from typing import Callable


@wrap_model_call
def add_time_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Add current time to system context."""
    from datetime import datetime

    # 使用内容块以实现最大兼容性
    new_content = list(request.system_message.content_blocks) + [
        {
            "type": "text",
            "text": f"\nCurrent time: {datetime.now().isoformat()}",
        }
    ]

    new_system_message = SystemMessage(content=new_content)
    return handler(request.override(system_message=new_system_message))
```

#### 上下文窗口管理

使用中间件在接近上下文限制时自动总结或截断：

```python
from langchain.agents.middleware import wrap_model_call, ModelRequest, ModelResponse
from typing import Callable


@wrap_model_call
def manage_context(
    request: ModelRequest,
    handler: Callable[[ModelRequest], ModelResponse],
) -> ModelResponse:
    """Summarize if context is too long."""
    # 估算 token 数量（粗略）
    total_chars = sum(len(str(m.content)) for m in request.messages)
    estimated_tokens = total_chars // 4

    if estimated_tokens > 100000:
        # 触发总结（使用总结中间件或自定义逻辑）
        # 这里有简化的示例
        pass

    return handler(request)
```

### 工具上下文

工具可以访问智能体状态和配置以提供上下文感知的行为。

#### 访问用户配置

```python
from langchain.tools import tool
from langchain.agents.runtime import Runtime


@tool
def get_user_preferences() -> str:
    """Get preferences for the current user."""
    runtime = Runtime.ensure()
    user_id = runtime.config["configurable"].get("user_id")

    if not user_id:
        return "No user context available"

    # 从存储中获取用户偏好
    store = runtime.store
    prefs = store.get(("preferences", user_id), "settings")

    return f"Preferences for {user_id}: {prefs}"
```

#### 上下文感知工具

根据状态或配置动态调整行为的工具：

```python
from langchain.tools import tool
from langchain.agents.runtime import Runtime


@tool
def search(query: str) -> str:
    """Search with user context."""
    runtime = Runtime.ensure()

    # 获取用户的语言偏好
    lang = runtime.config["configurable"].get("language", "en")

    # 获取先前的搜索以获得上下文
    previous = runtime.store.get(("search_history",), "recent") or []

    # 使用上下文执行搜索
    results = perform_search(query, language=lang, context=previous)

    # 更新历史
    runtime.store.put(
        ("search_history",),
        key="recent",
        value=previous[-10:] + [query],
    )

    return results
```

### 生命周期上下文

上下文在智能体的生命周期中演变：

```
┌─────────────────────────────────────────────────────────────┐
│                     Agent Lifecycle                          │
├─────────────────────────────────────────────────────────────┤
│                                                              │
│  1. Initial Context                                          │
│     ├── System prompt (来自 create_agent)                    │
│     ├── User message (来自 invoke)                           │
│     └── Configuration (来自 config)                          │
│                                                              │
│  2. Tool Execution                                           │
│     ├── Tool receives runtime                                │
│     ├── Can read/write to state                              │
│     └── Can access store                                     │
│                                                              │
│  3. Middleware Processing                                    │
│     ├── Can modify messages                                  │
│     ├── Can modify system prompt                             │
│     └── Can access full context                              │
│                                                              │
│  4. Response                                                 │
│     ├── Final messages                                       │
│     └── Any streamed data                                    │
│                                                              │
└─────────────────────────────────────────────────────────────┘
```

#### 跨运行持久化上下文

使用存储来保持跨多个运行的上下文：

```python
from langchain.agents import create_agent
from langchain.tools import tool
from langchain.agents.runtime import Runtime
from langgraph.store.memory import InMemoryStore


@tool
def remember(key: str, value: str) -> str:
    """Store a value for later retrieval."""
    runtime = Runtime.ensure()
    namespace = ("memory", runtime.config["configurable"]["session_id"])
    runtime.store.put(namespace, key=key, value=value)
    return f"Remembered {key}={value}"


@tool
def recall(key: str) -> str:
    """Retrieve a previously stored value."""
    runtime = Runtime.ensure()
    namespace = ("memory", runtime.config["configurable"]["session_id"])
    value = runtime.store.get(namespace, key)
    return str(value) if value else f"No value for {key}"


agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[remember, recall],
    store=InMemoryStore(),
)

# 第一次运行
agent.invoke(
    {"messages": [{"role": "user", "content": "remember name as Alice"}]},
    config={"configurable": {"session_id": "session1"}},
)

# 第二次运行（同一会话）
agent.invoke(
    {"messages": [{"role": "user", "content": "what is the name?"}]},
    config={"configurable": {"session_id": "session1"}},
)
```

### 上下文工程最佳实践

1. **保持系统提示简洁**：将详细指令移至中间件，以保持主要提示可读
2. **使用命名空间**：在存储中使用一致的命名空间以避免键冲突
3. **限制上下文增长**：实施总结或截断策略以管理 token 使用
4. **流式传输进度**：使用 `stream_writer` 在长时间操作期间保持用户知情
5. **分离关注点**：使用中间件进行跨领域关注点（日志记录、监控），而不是使工具复杂化
6. **配置优于硬编码**：使用运行时配置来参数化行为

## 14. 人工介入 (Human-in-the-loop)

人工介入（HITL）[中间件](#内置中间件)让你可以在智能体工具调用中添加人工监督。当模型提议执行可能需要审核的操作时（例如写入文件或执行 SQL），中间件可以暂停执行并等待决策。

它通过根据可配置的策略检查每个工具调用来实现这一点。如果需要干预，中间件会发出一个 [interrupt](https://reference.langchain.com/python/langgraph/types/interrupt) 来暂停执行。图状态使用 LangGraph 的[持久化层](/oss/python/langgraph/persistence)保存，因此执行可以安全暂停并在稍后恢复。

人工决策随后决定下一步：操作可以原样批准（`approve`）、运行前修改（`edit`）、或带反馈拒绝（`reject`）。

### 中断决策类型

[中间件](#内置中间件)定义了三种人工响应中断的内置方式：

| 决策类型 | 描述 | 示例用例 |
|---------|------|---------|
| ✅ `approve` | 操作原样批准，不做修改直接执行 | 完全按照草稿发送电子邮件 |
| ✏️ `edit` | 工具调用在修改后执行 | 发送电子邮件前更改收件人 |
| ❌ `reject` | 工具调用被拒绝，并将解释添加到对话中 | 拒绝电子邮件草稿并解释如何重写 |

每个工具可用的决策类型取决于你在 `interrupt_on` 中配置的策略。当多个工具调用同时暂停时，每个操作都需要单独的决策。决策必须按照操作在中断请求中出现的顺序提供。

> **提示**：在**编辑**工具参数时，请保守地进行更改。对原始参数的显著修改可能会导致模型重新评估其方法，并可能多次执行工具或采取意外操作。

### 配置中断

要使用 HITL，在创建智能体时将[中间件](#内置中间件)添加到智能体的 `middleware` 列表中。

你需要配置一个工具操作到每个操作允许的决策类型的映射。当工具调用与映射中的操作匹配时，中间件将中断执行。

```python
from langchain.agents import create_agent
from langchain.agents.middleware import HumanInTheLoopMiddleware
from langgraph.checkpoint.memory import InMemorySaver


agent = create_agent(
    model="gpt-4.1",
    tools=[write_file_tool, execute_sql_tool, read_data_tool],
    middleware=[
        HumanInTheLoopMiddleware(
            interrupt_on={
                "write_file": True,  # 允许所有决策（approve、edit、reject）
                "execute_sql": {"allowed_decisions": ["approve", "reject"]},  # 不允许编辑
                # 安全操作，无需批准
                "read_data": False,
            },
            # 中断消息前缀 - 与工具名称和参数组合形成完整消息
            # 例如："Tool execution pending approval: execute_sql with query='DELETE FROM...'"
            # 单个工具可以通过在其中断配置中指定 "description" 来覆盖此设置
            description_prefix="Tool execution pending approval",
        ),
    ],
    # 人工介入需要检查点来处理中断。
    # 在生产环境中，使用持久化检查点如 AsyncPostgresSaver。
    checkpointer=InMemorySaver(),
)
```

> **重要**：你必须配置检查点来跨中断持久化图状态。在生产环境中，使用持久化检查点如 [`AsyncPostgresSaver`](https://reference.langchain.com/python/langgraph/checkpoints/#langgraph.checkpoint.postgres.aio.AsyncPostgresSaver)。对于测试或原型设计，使用 [`InMemorySaver`](https://reference.langchain.com/python/langgraph/checkpoints/#langgraph.checkpoint.memory.InMemorySaver)。
>
> 在调用智能体时，传递一个包含 **线程 ID** 的 `config`，以将执行与对话线程关联。有关详细信息，请参阅 [LangGraph 中断文档](/oss/python/langgraph/interrupts)。

#### 配置选项

| 参数 | 类型 | 必需 | 描述 |
|------|------|------|------|
| `interrupt_on` | dict | 是 | 工具名称到批准配置的映射。值可以是 `True`（使用默认配置中断）、`False`（自动批准）、或 `InterruptOnConfig` 对象。 |
| `description_prefix` | string | 否（默认："Tool execution requires approval"） | 操作请求描述的前缀 |

**`InterruptOnConfig` 选项：**

| 参数 | 类型 | 描述 |
|------|------|------|
| `allowed_decisions` | list[string] | 允许的决策列表：`'approve'`、`'edit'` 或 `'reject'` |
| `description` | string \| callable | 静态字符串或可调用函数用于自定义描述 |

### 响应中断

当你调用智能体时，它会运行直到完成或引发中断。当工具调用与你在 `interrupt_on` 中配置的策略匹配时，会触发中断。在这种情况下，调用结果将包含一个 `__interrupt__` 字段，其中包含需要审核的操作。然后你可以将这些操作呈现给审核者，并在提供决策后恢复执行。

```python
from langgraph.types import Command

# 人工介入利用 LangGraph 的持久化层。
# 你必须提供线程 ID 来将执行与对话线程关联，
# 这样对话才能暂停和恢复（人工审核所需）。
config = {"configurable": {"thread_id": "some_id"}}
# 运行图直到遇到中断
result = agent.invoke(
    {
        "messages": [
            {
                "role": "user",
                "content": "Delete old records from the database",
            }
        ]
    },
    config=config
)

# 中断包含完整的 HITL 请求，包括 action_requests 和 review_configs
print(result['__interrupt__'])
# > [
# >    Interrupt(
# >       value={
# >          'action_requests': [
# >             {
# >                'name': 'execute_sql',
# >                'arguments': {'query': 'DELETE FROM records WHERE created_at < NOW() - INTERVAL \'30 days\';'},
# >                'description': 'Tool execution pending approval\n\nTool: execute_sql\nArgs: {...}'
# >             }
# >          ],
# >          'review_configs': [
# >             {
# >                'action_name': 'execute_sql',
# >                'allowed_decisions': ['approve', 'reject']
# >             }
# >          ]
# >       }
# >    )
# > ]


# 使用批准决策恢复
agent.invoke(
    Command(
        resume={"decisions": [{"type": "approve"}]}  # 或 "reject"
    ),
    config=config  # 相同的线程 ID 来恢复暂停的对话
)
```

#### 决策类型

**✅ approve**

使用 `approve` 原样批准工具调用，不做修改直接执行。

```python
agent.invoke(
    Command(
        # 决策以列表形式提供，每个待审核操作一个。
        # 决策的顺序必须与 `__interrupt__` 请求中
        # 列出的操作顺序匹配。
        resume={
            "decisions": [
                {
                    "type": "approve",
                }
            ]
        }
    ),
    config=config  # 相同的线程 ID 来恢复暂停的对话
)
```

**✏️ edit**

使用 `edit` 在执行前修改工具调用。提供带有新工具名称和参数的编辑后操作。

```python
agent.invoke(
    Command(
        # 决策以列表形式提供，每个待审核操作一个。
        # 决策的顺序必须与 `__interrupt__` 请求中
        # 列出的操作顺序匹配。
        resume={
            "decisions": [
                {
                    "type": "edit",
                    # 带有工具名称和参数的编辑后操作
                    "edited_action": {
                        # 要调用的工具名称。
                        # 通常与原始操作相同。
                        "name": "new_tool_name",
                        # 传递给工具的参数。
                        "args": {"key1": "new_value", "key2": "original_value"},
                    }
                }
            ]
        }
    ),
    config=config  # 相同的线程 ID 来恢复暂停的对话
)
```

> **提示**：在**编辑**工具参数时，请保守地进行更改。对原始参数的显著修改可能会导致模型重新评估其方法，并可能多次执行工具或采取意外操作。

**❌ reject**

使用 `reject` 拒绝工具调用并提供反馈，而不是执行。

```python
agent.invoke(
    Command(
        # 决策以列表形式提供，每个待审核操作一个。
        # 决策的顺序必须与 `__interrupt__` 请求中
        # 列出的操作顺序匹配。
        resume={
            "decisions": [
                {
                    "type": "reject",
                    # 关于操作为何被拒绝的解释
                    "message": "No, this is wrong because ..., instead do this ...",
                }
            ]
        }
    ),
    config=config  # 相同的线程 ID 来恢复暂停的对话
)
```

`message` 作为反馈添加到对话中，帮助智能体理解操作为何被拒绝以及应该做什么。

**多个决策**

当多个操作待审核时，按照它们在中断中出现的顺序为每个操作提供决策：

```python
{
    "decisions": [
        {"type": "approve"},
        {
            "type": "edit",
            "edited_action": {
                "name": "tool_name",
                "args": {"param": "new_value"}
            }
        },
        {
            "type": "reject",
            "message": "This action is not allowed"
        }
    ]
}
```

### 使用人工介入进行流式传输

你可以使用 `stream()` 而不是 `invoke()` 来在智能体运行和处理中断时获取实时更新。使用 `stream_mode=['updates', 'messages']` 来同时流式传输智能体进度和 LLM token。

```python
from langgraph.types import Command

config = {"configurable": {"thread_id": "some_id"}}

# 流式传输智能体进度和 LLM token 直到中断
for mode, chunk in agent.stream(
    {"messages": [{"role": "user", "content": "Delete old records from the database"}]},
    config=config,
    stream_mode=["updates", "messages"],
):
    if mode == "messages":
        # LLM token
        token, metadata = chunk
        if token.content:
            print(token.content, end="", flush=True)
    elif mode == "updates":
        # 检查中断
        if "__interrupt__" in chunk:
            print(f"\n\nInterrupt: {chunk['__interrupt__']}")

# 人工决策后使用流式传输恢复
for mode, chunk in agent.stream(
    Command(resume={"decisions": [{"type": "approve"}]}),
    config=config,
    stream_mode=["updates", "messages"],
):
    if mode == "messages":
        token, metadata = chunk
        if token.content:
            print(token.content, end="", flush=True)
```

有关流模式的更多详细信息，请参阅[流式传输](#流式传输-streaming)指南。

### 执行生命周期

中间件定义了一个 `after_model` 钩子，在模型生成响应后但执行任何工具调用之前运行：

1. 智能体调用模型生成响应。
2. 中间件检查响应中的工具调用。
3. 如果任何调用需要人工输入，中间件会构建一个包含 `action_requests` 和 `review_configs` 的 `HITLRequest`，并调用 [interrupt](https://reference.langchain.com/python/langgraph/types/interrupt)。
4. 智能体等待人工决策。
5. 根据 `HITLResponse` 决策，中间件执行批准或编辑的调用，为拒绝的调用合成 [ToolMessage](https://reference.langchain.com/python/langchain-core/messages/tool/ToolMessage)，并恢复执行。

### 自定义 HITL 逻辑

对于更专业的工作流，你可以使用 [interrupt](https://reference.langchain.com/python/langgraph/types/interrupt) 原语和[中间件](#自定义中间件)抽象直接构建自定义 HITL 逻辑。

查看上面的[执行生命周期](#执行生命周期)以了解如何将中断集成到智能体的操作中。

## 15. 长期记忆 (Long-term Memory)

### 概述

LangChain 智能体使用 [LangGraph 持久化](/oss/python/langgraph/persistence#memory-store)来启用长期记忆。这是一个更高级的主题，需要了解 LangGraph 才能使用。

### 记忆存储

LangGraph 将长期记忆作为 JSON 文档存储在 [store](/oss/python/langgraph/persistence#memory-store) 中。

每个记忆都在自定义 `namespace`（类似于文件夹）和不同的 `key`（如文件名）下组织。命名空间通常包含用户或组织 ID 或其他便于组织信息的标签。

这种结构支持记忆的分层组织。然后通过内容过滤器支持跨命名空间搜索。

```python
from langgraph.store.memory import InMemoryStore


def embed(texts: list[str]) -> list[list[float]]:
    # 替换为实际的嵌入函数或 LangChain 嵌入对象
    return [[1.0, 2.0] * len(texts)]


# InMemoryStore 将数据保存到内存字典中。在生产使用中使用数据库支持的存储。
store = InMemoryStore(index={"embed": embed, "dims": 2})
user_id = "my-user"
application_context = "chitchat"
namespace = (user_id, application_context)
store.put(
    namespace,
    "a-memory",
    {
        "rules": [
            "User likes short, direct language",
            "User only speaks English & python",
        ],
        "my-key": "my-value",
    },
)
# 通过 ID 获取 "memory"
item = store.get(namespace, "a-memory")
# 在此命名空间内搜索 "memories"，按内容等效性过滤，按向量相似度排序
items = store.search(
    namespace, filter={"my-key": "my-value"}, query="language preferences"
)
```

有关记忆存储的更多信息，请参阅[持久化](/oss/python/langgraph/persistence#memory-store)指南。

### 在工具中读取长期记忆

```python
from dataclasses import dataclass

from langchain_core.runnables import RunnableConfig
from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langgraph.store.memory import InMemoryStore


@dataclass
class Context:
    user_id: str

# InMemoryStore 将数据保存到内存字典中。在生产环境中使用数据库支持的存储。
store = InMemoryStore()

# 使用 put 方法将示例数据写入存储
store.put(
    ("users",),  # 用于将相关数据分组的命名空间（用户数据的 users 命名空间）
    "user_123",  # 命名空间内的键（用户 ID 作为键）
    {
        "name": "John Smith",
        "language": "English",
    }  # 要为给定用户存储的数据
)

@tool
def get_user_info(runtime: ToolRuntime[Context]) -> str:
    """Look up user info."""
    # 访问存储 - 与提供给 `create_agent` 的相同
    store = runtime.store
    user_id = runtime.context.user_id
    # 从存储中检索数据 - 返回带有 value 和 metadata 的 StoreValue 对象
    user_info = store.get(("users",), user_id)
    return str(user_info.value) if user_info else "Unknown user"

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[get_user_info],
    # 将存储传递给智能体 - 使智能体在运行工具时能够访问存储
    store=store,
    context_schema=Context
)

# 运行智能体
agent.invoke(
    {"messages": [{"role": "user", "content": "look up user information"}]},
    context=Context(user_id="user_123")
)
```

### 从工具写入长期记忆

```python
from dataclasses import dataclass
from typing_extensions import TypedDict

from langchain.agents import create_agent
from langchain.tools import tool, ToolRuntime
from langgraph.store.memory import InMemoryStore


# InMemoryStore 将数据保存到内存字典中。在生产环境中使用数据库支持的存储。
store = InMemoryStore()

@dataclass
class Context:
    user_id: str

# TypedDict 定义 LLM 的用户信息结构
class UserInfo(TypedDict):
    name: str

# 允许智能体更新用户信息的工具（对聊天应用程序有用）
@tool
def save_user_info(user_info: UserInfo, runtime: ToolRuntime[Context]) -> str:
    """Save user info."""
    # 访问存储 - 与提供给 `create_agent` 的相同
    store = runtime.store
    user_id = runtime.context.user_id
    # 在存储中存储数据（命名空间、键、数据）
    store.put(("users",), user_id, user_info)
    return "Successfully saved user info."

agent = create_agent(
    model="claude-sonnet-4-5-20250929",
    tools=[save_user_info],
    store=store,
    context_schema=Context
)

# 运行智能体
agent.invoke(
    {"messages": [{"role": "user", "content": "My name is John Smith"}]},
    # user_id 在上下文中传递以标识正在更新的信息属于谁
    context=Context(user_id="user_123")
)

# 你可以直接访问存储来获取值
store.get(("users",), "user_123").value
```
