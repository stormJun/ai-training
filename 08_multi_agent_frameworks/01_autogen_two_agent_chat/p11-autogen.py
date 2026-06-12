# -*- coding: utf-8 -*-
# Converted from p11-autogen.ipynb

# %% [markdown]
# 一个简单的示例，其中两个 agent 从 10 倒数到 1。
#
# 我们首先定义 agent 类及其各自的处理消息的程序。
#
# 我们创建两个 agent 类：Modifier 和 Checker。
#
# Modifier agent 修改给定的数字，而 Check agent 根据条件检查该值。
#
# 我们还创建了一个 Message 数据类，它定义了在 agent 之间传递的消息。

# %%
from dataclasses import dataclass
from typing import Callable

from autogen_core import DefaultTopicId, MessageContext, RoutedAgent, default_subscription, message_handler


@dataclass
class Message:
    content: int


@default_subscription
class Modifier(RoutedAgent):
    def __init__(self, modify_val: Callable[[int], int]) -> None:
        super().__init__("A modifier agent.")
        self._modify_val = modify_val

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> None:
        val = self._modify_val(message.content)
        print(f"{'-'*80}\nModifier:\nModified {message.content} to {val}")
        await self.publish_message(Message(content=val), DefaultTopicId())  # type: ignore


@default_subscription
class Checker(RoutedAgent):
    def __init__(self, run_until: Callable[[int], bool]) -> None:
        super().__init__("A checker agent.")
        self._run_until = run_until

    @message_handler
    async def handle_message(self, message: Message, ctx: MessageContext) -> None:
        if not self._run_until(message.content):
            print(f"{'-'*80}\nChecker:\n{message.content} passed the check, continue.")
            await self.publish_message(Message(content=message.content), DefaultTopicId())
        else:
            print(f"{'-'*80}\nChecker:\n{message.content} failed the check, stopping.")

# %% [markdown]
# 您可能已经注意到，agent 的逻辑（无论是使用模型还是代码执行器）与消息的传递方式完全分离。
#
# 这是核心思想：框架提供通信基础设施，agent 负责自己的逻辑。 我们将通信基础设施称为 **Agent 运行时**。
#
# Agent 运行时是此框架的关键概念。 除了传递消息之外，它还管理 agent 的生命周期。 因此，agent 的创建由运行时处理。

# %%
from autogen_core import AgentId, SingleThreadedAgentRuntime

# Create a local embedded runtime.
runtime = SingleThreadedAgentRuntime()

# Register the modifier and checker agents by providing
# their agent types, the factory functions for creating instance and subscriptions.
await Modifier.register(
    runtime,
    "modifier",
    # Modify the value by subtracting 1
    lambda: Modifier(modify_val=lambda x: x - 1),
)

await Checker.register(
    runtime,
    "checker",
    # Run until the value is less than or equal to 1
    lambda: Checker(run_until=lambda x: x <= 1),
)

# Start the runtime and send a direct message to the checker.
runtime.start()
await runtime.send_message(Message(10), AgentId("checker", "default"))
await runtime.stop_when_idle()

# %% [markdown]
# 从 agent 的输出中，我们可以看到该值已成功从 10 递减到 1，正如 modifier 和 checker 条件所规定。
#
# AutoGen 还支持分布式 agent 运行时，它可以托管在不同进程或机器上运行的具有不同身份、语言和依赖项的 agent。

# %% [markdown]
# https://msdocs.cn/autogen/stable/user-guide/core-user-guide/design-patterns/intro.html
#
# autogen 多代理模式的几个典型应用场景： 工作流、群聊、辩论、反思

# %%
# NOTEBOOK_MAGIC: %pip install autogen_ext

# %% [markdown]
# ## 顺序工作流
#
# 顺序工作流是一种多 Agent 设计模式，其中 Agent 以确定性的顺序响应。 工作流中的每个 Agent 通过处理消息、生成响应，然后将其传递给下一个 Agent 来执行特定任务。 此模式对于创建确定性工作流非常有用，其中每个 Agent 都有助于预先指定的子任务。
#
# 在此示例中，我们将演示一个顺序工作流，其中多个 Agent 协同工作，将基本产品描述转换为精美的营销文案。
#
# 该管道由四个专业的 Agent 组成
#
# - 概念提取 Agent：分析初始产品描述以提取关键功能、目标受众和独特的卖点 (USP)。 输出是单个文本块中的结构化分析。
#
# - 编写 Agent：根据提取的概念制作引人注目的营销文案。 此 Agent 将分析见解转化为引人入胜的促销内容，并在单个文本块中提供连贯的叙述。
#
# - 格式和校对 Agent：通过改进语法、增强清晰度和保持一致的语气来润色草稿副本。 此 Agent 确保专业质量并提供格式良好的最终版本。
#
# -用户 Agent：向用户展示最终的、精美的营销文案，完成工作流程。
#
# 下图说明了此示例中的顺序工作流程
#
# ![img](https://msdocs.cn/autogen/stable/_images/sequential-workflow.svg)

# %%


from dataclasses import dataclass

from autogen_core import (
    MessageContext,
    RoutedAgent,
    SingleThreadedAgentRuntime,
    TopicId,
    TypeSubscription,
    message_handler,
    type_subscription,
)
from autogen_core.models import ChatCompletionClient, SystemMessage, UserMessage
from autogen_ext.models.openai import OpenAIChatCompletionClient

# Agent 将使用该消息来传递他们的工作
@dataclass
class Message:
    content: str

# 工作流程中的每个 Agent 都将订阅特定的主题类型。
# 主题类型以序列中 Agent 的名称命名， 这允许每个 Agent 将其工作发布到序列中的下一个 Agent。

concept_extractor_topic_type = "ConceptExtractorAgent"
writer_topic_type = "WriterAgent"
format_proof_topic_type = "FormatProofAgent"
user_topic_type = "User"


# 每个 Agent 类都使用 type_subscription 装饰器来指定它订阅的主题类型。
# 除了装饰器，您还可以使用 add_subscription() 方法直接通过运行时订阅主题。

# "概念提取 Agent "提出了产品描述的初始要点。
@type_subscription(topic_type=concept_extractor_topic_type)
class ConceptExtractorAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A concept extractor agent.")
        self._system_message = SystemMessage(
            content=(
                "You are a marketing analyst. Given a product description, identify:\n"
                "- Key features\n"
                "- Target audience\n"
                "- Unique selling points\n\n"
            )
        )
        self._model_client = model_client

    @message_handler
    async def handle_user_description(self, message: Message, ctx: MessageContext) -> None:
        prompt = f"Product description: {message.content}"
        llm_result = await self._model_client.create(
            messages=[self._system_message, UserMessage(content=prompt, source=self.id.key)],
            cancellation_token=ctx.cancellation_token,
        )
        response = llm_result.content
        assert isinstance(response, str)
        print(f"{'-'*80}\n{self.id.type}:\n{response}")

        await self.publish_message(Message(response), topic_id=TopicId(writer_topic_type, source=self.id.key))

# "编写 Agent "执行编写
@type_subscription(topic_type=writer_topic_type)
class WriterAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A writer agent.")
        self._system_message = SystemMessage(
            content=(
                "You are a marketing copywriter. Given a block of text describing features, audience, and USPs, "
                "compose a compelling marketing copy (like a newsletter section) that highlights these points. "
                "Output should be short (around 150 words), output just the copy as a single text block."
            )
        )
        self._model_client = model_client

    @message_handler
    async def handle_intermediate_text(self, message: Message, ctx: MessageContext) -> None:
        prompt = f"Below is the info about the product:\n\n{message.content}"

        llm_result = await self._model_client.create(
            messages=[self._system_message, UserMessage(content=prompt, source=self.id.key)],
            cancellation_token=ctx.cancellation_token,
        )
        response = llm_result.content
        assert isinstance(response, str)
        print(f"{'-'*80}\n{self.id.type}:\n{response}")

        await self.publish_message(Message(response), topic_id=TopicId(format_proof_topic_type, source=self.id.key))

# "格式校对 Agent "执行格式化。
@type_subscription(topic_type=format_proof_topic_type)
class FormatProofAgent(RoutedAgent):
    def __init__(self, model_client: ChatCompletionClient) -> None:
        super().__init__("A format & proof agent.")
        self._system_message = SystemMessage(
            content=(
                "You are an editor. Given the draft copy, correct grammar, improve clarity, ensure consistent tone, "
                "give format and make it polished. Output the final improved copy as a single text block."
            )
        )
        self._model_client = model_client

    @message_handler
    async def handle_intermediate_text(self, message: Message, ctx: MessageContext) -> None:
        prompt = f"Draft copy:\n{message.content}."
        llm_result = await self._model_client.create(
            messages=[self._system_message, UserMessage(content=prompt, source=self.id.key)],
            cancellation_token=ctx.cancellation_token,
        )
        response = llm_result.content
        assert isinstance(response, str)
        print(f"{'-'*80}\n{self.id.type}:\n{response}")

        await self.publish_message(Message(response), topic_id=TopicId(user_topic_type, source=self.id.key))

# "用户 Agent "只是将最终的营销文案打印到控制台。
# 在实际应用中，这可以替换为将结果存储到数据库、发送电子邮件或任何其他所需的操作。
@type_subscription(topic_type=user_topic_type)
class UserAgent(RoutedAgent):
    def __init__(self) -> None:
        super().__init__("A user agent that outputs the final copy to the user.")

    @message_handler
    async def handle_final_copy(self, message: Message, ctx: MessageContext) -> None:
        print(f"\n{'-'*80}\n{self.id.type} received final copy:\n{message.content}")



# 将 Agent 注册到运行时。
# 因为我们使用了 type_subscription 装饰器，所以运行时会自动将 Agent 订阅到正确的主题。
model_client = OpenAIChatCompletionClient(
    model="gpt-4o-mini",
    # api_key="YOUR_API_KEY"
)

runtime = SingleThreadedAgentRuntime()

await ConceptExtractorAgent.register(
    runtime, type=concept_extractor_topic_type, factory=lambda: ConceptExtractorAgent(model_client=model_client)
)

await WriterAgent.register(runtime, type=writer_topic_type, factory=lambda: WriterAgent(model_client=model_client))

await FormatProofAgent.register(
    runtime, type=format_proof_topic_type, factory=lambda: FormatProofAgent(model_client=model_client)
)

await UserAgent.register(runtime, type=user_topic_type, factory=lambda: UserAgent())


# 最后，我们可以通过将消息发布到序列中的第一个 Agent 来运行工作流程
runtime.start()

await runtime.publish_message(
    Message(content="An eco-friendly stainless steel water bottle that keeps drinks cold for 24 hours"),
    topic_id=TopicId(concept_extractor_topic_type, source="default"),
)

await runtime.stop_when_idle()
await model_client.close()


# %% [markdown]
# ## 群聊模式的消息协议
#
# 首先，用户或外部 Agent 将 GroupChatMessage 消息发布到所有参与者的共同主题。
#
# 群聊管理器选择下一个发言人，并向该 Agent 发送 RequestToSpeak 消息。
#
# Agent 在收到 RequestToSpeak 消息后，将 GroupChatMessage 消息发布到公共主题。
#
# 此过程一直持续到群聊管理器达到终止条件，然后停止发出 RequestToSpeak 消息，并且群聊结束。
#
#
# ![img](https://msdocs.cn/autogen/stable/_images/groupchat.svg)

# %% [markdown]
# ## 多智能体辩论
#
# 多智能体辩论是一种多智能体设计模式，它模拟了多轮交互，在每一轮中，智能体之间交换响应，并根据其他智能体的响应改进其响应。
#
#
# 此模式中有两种类型的智能体：求解器智能体和聚合器智能体。
#
# 求解器智能体以稀疏的方式连接，遵循 使用稀疏通信拓扑改进多智能体辩论 中描述的技术。
#
# 求解器智能体负责解决数学问题并相互交换响应。
#
# 聚合器智能体负责将数学问题分发给求解器智能体，等待他们的最终响应，并聚合这些响应以获得最终答案。
#
#
# **该模式的工作方式如下**
#
# 1. 用户向聚合器智能体发送一个数学问题。
#
# 2. 聚合器智能体将问题分发给求解器智能体。
#
# 3. 每个求解器智能体处理该问题，并向其邻居发布响应。
#
# 4. 每个求解器智能体使用来自其邻居的响应来改进其响应，并发布新的响应。
#
# 5. 重复步骤 4 固定轮数。 在最后一轮中，每个求解器智能体发布最终响应。
#
# 6. 聚合器智能体使用多数投票来聚合来自所有求解器智能体的最终响应以获得最终答案，并发布该答案。

# %% [markdown]
# ## 反思
#
# 应用程序向编码器代理发送一个 CodeWritingTask 消息
#
# 编码器代理生成一个 CodeReviewTask 消息，该消息被发送到审查器代理
#
# 审查器代理生成一个 CodeReviewResult 消息，该消息被发送回编码器代理
#
# 取决于 CodeReviewResult 消息，如果代码被批准，编码器代理将一个 CodeWritingResult 消息发送回应用程序，否则，编码器代理将另一个 CodeReviewTask 消息发送到审查器代理，并且该过程继续。
#
# ![](https://msdocs.cn/autogen/stable/_images/coder-reviewer-data-flow.svg)
