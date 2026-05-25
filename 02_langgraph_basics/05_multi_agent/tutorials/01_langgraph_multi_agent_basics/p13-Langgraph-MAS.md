# LangGraph 多智能体系统（MAS）

> 来源：`p13-Langgraph-MAS.ipynb`
>
> 可运行实现见同目录 `p13-Langgraph-MAS.py`。

![multi-agent architectures](https://langgraph.com.cn/concepts/img/multi_agent/architectures.png)

上图展示了多代理系统的几种常见组织方式：

- 网络：每个代理都可以与其他代理直接通信。
- 主管：由一个主管代理统一决定下一步调用谁。
- 主管（工具调用）：把其他代理包装成工具，由主管代理调用。
- 分层：主管之上还有更高层主管，形成多层控制。
- 自定义工作流：只允许部分代理之间通信，流程部分确定、部分智能。

这篇文档对应的是一种“自定义工作流 + handoff”式的实现：两个代理分别负责不同任务，并在需要时将控制权转交给下一个代理。

## 这篇文档学什么

看完这个示例，应该重点理解 3 件事：

1. 为什么多代理示例里不只需要“多个工具”，还需要“多个代理节点”。
2. 为什么代理之间的转接采用 `Command` 表达。
3. 为什么 handoff 场景下必须额外处理消息历史，否则 LangGraph 会报错或让下一个代理拿到错误上下文。

## 场景

这个示例模拟一个旅行预订助手，用户一次提出两个子任务：

- 预订从波士顿（BOS）到纽约（JFK）的航班
- 预订麦克基特里克酒店（McKittrick Hotel）的住宿

为了让示例更清楚，系统把两个任务拆给两个专业代理：

- `flight_assistant`：负责航班相关问题
- `hotel_assistant`：负责酒店相关问题

这样设计的主要目的是展示在 LangGraph 中如何将不同职责拆分为独立节点，并通过 handoff 机制实现控制权流转。

## 架构

这个示例可以先理解成下面这条主流程：

```text
用户请求
  -> flight_assistant
  -> book_flight
  -> transfer_to_hotel_assistant
  -> hotel_assistant
  -> book_hotel
  -> 最终答复
```

其中有 4 类核心部件：

### 1. 两个代理节点

- `flight_assistant`
- `hotel_assistant`

它们都是通过 `create_react_agent(...)` 创建出来的 LangGraph 代理节点。每个节点都绑定了自己的工具集和提示词。

### 2. 两个普通工具

- `book_flight(...)`
- `book_hotel(...)`

这两个函数只负责执行业务动作，返回普通结果字符串。

### 3. 两个 handoff 工具

- `transfer_to_hotel_assistant`
- `transfer_to_flight_assistant`

这两个工具的主要职责是将控制权转交给另一个代理。

### 4. 一个状态图

整个系统最后由 `StateGraph(MessagesState)` 组织起来，入口在 `START -> flight_assistant`。也就是说，这个例子总是先让航班代理接手，再根据情况决定是否转交给酒店代理。

## 关键机制

### 1. 普通工具和 handoff 工具的区别

普通工具只做一件事：执行动作并返回结果。

```python
def book_flight(from_airport: str, to_airport: str) -> str:
    return f"已成功预订从 {from_airport} 到 {to_airport} 的航班。"
```

handoff 工具的职责与普通业务工具不同，它返回的是 `Command`：

```python
return Command(
    goto=agent_name,
    update={"messages": ...},
    graph=Command.PARENT,
)
```

这里最重要的是：

- `goto=agent_name`
  表示下一步跳到哪个代理节点
- `update={...}`
  表示切换代理时，要把什么状态一起带过去
- `graph=Command.PARENT`
  表示这次跳转发生在父图层级

因此，handoff 的核心作用是修改图的执行路径，并将控制权切换到目标代理节点。

### 2. 为什么 handoff 不能只传一句“已转接”

在 LangGraph 中，只要某条 `AIMessage` 包含工具调用，就需要配套的 `ToolMessage` 完成消息配对。缺少配对信息时，后续节点会因为消息历史不完整而报错。

这也是这个示例里最关键、也最容易踩坑的地方。

当前脚本在 handoff 时只传递一对关键消息：

```python
def build_handoff_messages(messages, tool_call_id: str, agent_name: str) -> list:
    last_ai_message = next(
        message for message in reversed(messages) if isinstance(message, AIMessage)
    )
    transfer_message = ToolMessage(
        content="...",
        tool_call_id=tool_call_id,
    )
    return [last_ai_message, transfer_message]
```

这样做有两个目的：

1. 保证消息历史合法：handoff 这一轮的工具调用一定能找到对应的 `ToolMessage`
2. 控制传递给下一个代理的上下文范围，降低无关信息干扰和额外 token 开销

### 3. 为什么 `ToolMessage` 里要带“已完成事项摘要”

如果 handoff 时仅保留“成功转移到 hotel_assistant”这一类简短确认信息，下一个代理通常无法准确获知前一个代理已经完成的事项。

在这个例子里，这会带来一个典型问题：

- 航班已经预订完成
- 酒店代理却看不到这个事实
- 最后它可能会再次说“还需要转回航班代理处理机票”

所以脚本里专门做了一个摘要：

```python
completed_items = summarize_completed_tool_messages(messages)
summary_lines = [f"成功转移到 {agent_name}。"]
if completed_items:
    summary_lines.append("已完成事项：")
    summary_lines.extend(f"- {item}" for item in completed_items)
summary_lines.append(f"当前请继续处理 {agent_name} 负责的剩余事项。")
summary_lines.append("不要重复处理已完成事项。")
```

这个设计的作用是：

- 保留 handoff 所需的合法消息结构
- 同时把“航班已订好”这样的关键信息显式告诉下一个代理

这套做法并不等同于完整状态管理，但对于教学示例已经足够，同时也更便于理解 handoff 的上下文传递机制。

### 4. 为什么要关闭并行 tool calls

脚本里还有一个不太显眼但很重要的点：

```python
def bind_model_with_tools(model, tools):
    return model.bind_tools(tools, parallel_tool_calls=False)
```

这是为了避免模型在同一条 `AIMessage` 里一次性同时发出多个工具调用。

如果不关闭并行 tool calls，模型可能会在同一轮里同时决定：

- `book_flight(...)`
- `transfer_to_hotel_assistant(...)`

这种执行方式会增加 handoff 场景下的消息历史维护难度，也更容易出现前一个工具结果尚未完成处理、控制权就已经切换到下一个代理的情况。

本示例以教学说明为主，因此这里选择了更稳定、也更容易解释的串行工具调用方式。

### 5. Command 与 Send

Handoffs 的底层实现通常会涉及两个 LangGraph 控制流原语：

- `Command`
  用于在当前步骤中同时表达“状态更新”和“下一步跳转目标”。本示例中的代理切换正是通过 `Command(goto=..., update=...)` 完成的。
- `Send`
  用于把一个输入动态分发给多个目标节点，常见于 fan-out / fan-in 一类工作流，例如把一个复杂请求拆成多个并行子任务，再在后续节点汇总结果。

从控制流语义上看，`Command` 更适合单路径切换，`Send` 更适合多目标分发。

## 执行流程

把整体运行过程串起来看，大致是下面 6 步：

1. 用户输入“订机票 + 订酒店”的复合请求。
2. 图从 `flight_assistant` 开始执行。
3. 航班代理调用 `book_flight(...)`，完成机票预订。
4. 航班代理判断酒店任务还没处理，于是调用 `transfer_to_hotel_assistant`。
5. handoff 工具返回 `Command`，LangGraph 把控制权切给 `hotel_assistant`，并附带摘要化后的合法消息对。
6. 酒店代理调用 `book_hotel(...)`，完成酒店预订，并给出最终答复。

从教学角度看，这个例子能够更清晰地展示“业务动作执行”和“控制流切换”这两类机制。

当前示例属于单路径代理切换，因此这里选择 `Command` 作为 handoff 的底层表达方式。如果后续要把一个请求拆成多个并行子任务，再在下游节点汇总结果，通常会进一步引入 `Send`。

## 运行与排错

### 1. 运行方式

直接在当前目录执行：

```bash
python p13-Langgraph-MAS.py
```

### 2. API Key 从哪里来

当前脚本会按顺序尝试读取这些位置：

- 当前目录下的 `.env`
- `08_multi_agent_frameworks/01_autogen_two_agent_chat/.env`
- `01_langchain_basics/.env`

对应逻辑在：

```python
DEFAULT_ENV_FILES = [
    SCRIPT_DIR / ".env",
    PROJECT_ROOT / "08_multi_agent_frameworks/01_autogen_two_agent_chat/.env",
    PROJECT_ROOT / "01_langchain_basics/.env",
]
```

如果这些位置都没有真实可用的 `DASHSCOPE_API_KEY`，脚本会在启动阶段直接给出明确错误。

### 3. 为什么现在用的是 `ChatTongyi`

原 Notebook 更接近 OpenAI 兼容接口的写法，但这版脚本改成了：

```python
from langchain_community.chat_models import ChatTongyi
```

选择该接入方式的原因在于：它在当前仓库环境中更稳定，也与仓库内其他 Qwen 示例的写法保持一致。

对于学习过程而言，更重要的是以下几点：

- 你把模型对象当作“支持工具调用的聊天模型”来理解
- 它能被 `create_react_agent(...)` 正常绑定工具
- 你能把注意力放在 multi-agent 和 handoff 机制本身

## 初学者最容易踩的坑

### 1. 把 handoff 当成普通工具返回字符串

如果 handoff 工具只是返回 `"已转接"` 这种字符串，它不会改变图的执行路径，系统也不会真的切换到另一个代理节点。

### 2. handoff 时不补 `ToolMessage`

只要存在 tool call，就需要对应的 `ToolMessage`。这是 LangGraph / LLM 工具调用历史的基本规则。

### 3. 直接把全部历史丢给下一个代理

这种做法并非绝对错误，但在教学示例中通常会引入更多无关上下文，也不利于说明 handoff 所需的最小必要信息。

### 4. 不控制并行 tool calls

并行调用并不总是更好。在 handoff 场景下，它反而更容易制造执行顺序和消息历史的问题。

### 5. 只看代码，不看执行流

这个示例真正的学习重点不在某一行 Python，而在“谁在什么时候拥有控制权”。理解这一点，比死记 API 更重要。

## 小结

这个示例最值得学习的是下面这套设计思路：

- 用不同代理拆分职责
- 用普通工具完成动作
- 用 handoff 工具切换控制权
- 用 `Command` 驱动图跳转
- 用合法且精简的消息历史把上下文传给下一个代理

如果你先把这套机制看懂，再去读同目录的 [p13-Langgraph-MAS.py](/Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/05_multi_agent/tutorials/01_langgraph_multi_agent_basics/p13-Langgraph-MAS.py)，代码会容易理解很多。
