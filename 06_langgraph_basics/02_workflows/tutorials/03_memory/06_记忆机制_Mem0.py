"""记忆机制与 Mem0 示例。

这个脚本保留了两类内容：
1. LangChain 旧式 ConversationBufferMemory 示例
2. 基于 Mem0 的快递客服长期记忆示例
"""

from __future__ import annotations

import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import Any

from dotenv import load_dotenv
from langchain_community.chat_models import ChatTongyi


def ensure_legacy_memory_support() -> None:
    """确保当前环境仍然包含旧式 langchain.memory 模块。"""
    if importlib.util.find_spec("langchain.memory") is not None:
        return

    try:
        import langchain

        langchain_ver = getattr(langchain, "__version__", "unknown")
        langchain_file = getattr(langchain, "__file__", "unknown")
    except Exception:
        langchain_ver = "not installed"
        langchain_file = "unknown"

    raise ModuleNotFoundError(
        "当前解释器的 LangChain 不包含 `langchain.memory`，因此无法导入 ConversationBufferMemory。\n"
        f"Python: {sys.executable}\n"
        f"langchain: {langchain_ver} ({langchain_file})\n\n"
        "请切换到 02_workflows 的虚拟环境/内核后再运行：\n"
        "  cd 02_workflows && uv sync --locked\n"
        "  cd 02_workflows && uv run python -m ipykernel install --user --name 02_workflows --display-name \"02_workflows\"\n"
    )


def load_environment() -> None:
    """读取环境变量。"""
    if not load_dotenv():
        load_dotenv(Path("02_workflows/.env"))


def require_dashscope_key() -> str:
    """获取并校验 DASHSCOPE_API_KEY。"""
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise RuntimeError("Missing DASHSCOPE_API_KEY. Set env var or fill 02_workflows/.env")
    return api_key


def build_tongyi_llm(streaming: bool = False) -> ChatTongyi:
    """构建通义千问模型实例。"""
    return ChatTongyi(model_name="qwen-turbo", temperature=0.7, streaming=streaming)


def run_conversation_buffer_demo() -> None:
    """运行最基础的 ConversationBufferMemory 示例。"""
    from langchain.chains import LLMChain
    from langchain.memory import ConversationBufferMemory
    from langchain.prompts import PromptTemplate

    llm = build_tongyi_llm(streaming=False)

    template = """You are a chatbot having a conversation with a human.
{chat_history}
Human: {human_input}
Chatbot:"""

    prompt = PromptTemplate(
        input_variables=["chat_history", "human_input"],
        template=template,
    )

    memory = ConversationBufferMemory(memory_key="chat_history")
    llm_chain = LLMChain(
        llm=llm,
        prompt=prompt,
        verbose=True,
        memory=memory,
    )

    print(llm_chain.predict(human_input="Hi there my friend"))
    print(llm_chain.predict(human_input="Not too bad - how are you?"))


# 依赖已在 02_workflows 环境里锁定；此处在运行 Mem0 示例时再按需导入。
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import ChatOpenAI
from openai import OpenAI

from mem0 import Memory
from mem0.configs.base import MemoryConfig
from mem0.embeddings.configs import EmbedderConfig
from mem0.llms.configs import LlmConfig


logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


class ExpressCustomerService:
    """使用 Mem0 的快递行业智能客服示例。"""

    def __init__(self):
        self.api_key = require_dashscope_key()
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"

        self.openai_client: OpenAI | None = None
        self.llm: ChatOpenAI | None = None
        self.mem0: Memory | None = None
        self.prompt: ChatPromptTemplate | None = None

        self._initialize_components()

    def _test_api_connection(self) -> bool:
        """测试 DashScope 兼容接口连接是否正常。"""
        try:
            self.openai_client.chat.completions.create(
                model="qwen-turbo",
                messages=[{"role": "user", "content": "测试连接"}],
                max_tokens=10,
            )
            logger.info("API 连接测试成功")
            return True
        except Exception as exc:
            logger.error(f"API 连接测试失败: {exc}")
            return False

    def _initialize_components(self) -> None:
        """初始化模型、Mem0 和提示词模板。"""
        try:
            self.openai_client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info("OpenAI 客户端初始化成功")

            if not self._test_api_connection():
                raise RuntimeError("API 连接失败，请检查 API 密钥和网络连接")

            self.llm = ChatOpenAI(
                temperature=0.3,
                openai_api_key=self.api_key,
                openai_api_base=self.base_url,
                model="qwen-turbo",
            )
            logger.info("LangChain LLM 初始化成功")

            config = MemoryConfig(
                llm=LlmConfig(
                    provider="openai",
                    config={
                        "model": "qwen-turbo",
                        "api_key": self.api_key,
                        "openai_base_url": self.base_url,
                    },
                ),
                embedder=EmbedderConfig(
                    provider="openai",
                    config={
                        "model": "text-embedding-v1",
                        "api_key": self.api_key,
                        "openai_base_url": self.base_url,
                    },
                ),
            )

            self.mem0 = Memory(config=config)
            logger.info("Mem0 记忆系统初始化成功")
            self._initialize_prompt()
        except Exception as exc:
            logger.error(f"组件初始化失败: {exc}")
            raise

    def _initialize_prompt(self) -> None:
        """初始化客服提示词模板。"""
        self.prompt = ChatPromptTemplate.from_messages(
            [
                SystemMessage(
                    content="""您是一位专业的快递行业智能客服助手。请使用提供的上下文信息来个性化您的回复，记住用户的偏好和历史交互记录。

您的主要职责包括：
1. 快递查询服务：帮助用户查询包裹状态、物流轨迹、预计送达时间
2. 寄件服务：提供寄件指导、价格咨询、时效说明、包装建议
3. 问题解决：处理快递延误、丢失、损坏等问题，提供解决方案
4. 服务咨询：介绍各类快递服务、收费标准、服务范围
5. 投诉建议：接收用户反馈，记录投诉信息并提供处理方案

回复时请保持：
- 专业、礼貌、耐心的服务态度
- 准确、及时的信息提供
- 个性化的服务体验
- 如果没有具体信息，可以基于快递行业常识提供建议

请用中文回复，语气亲切专业。"""
                ),
                MessagesPlaceholder(variable_name="context"),
                HumanMessage(content="{input}"),
            ]
        )

    def retrieve_context(self, query: str, user_id: str) -> list[dict[str, Any]]:
        """从 Mem0 检索历史上下文。"""
        try:
            memories = self.mem0.search(query, user_id=user_id)
            if memories and "results" in memories and memories["results"]:
                serialized_memories = " ".join(
                    mem.get("memory", "") for mem in memories["results"]
                )
            else:
                serialized_memories = "暂无相关历史记录"

            return [
                {"role": "system", "content": f"相关历史信息: {serialized_memories}"},
                {"role": "user", "content": query},
            ]
        except Exception as exc:
            logger.warning(f"检索上下文时出错: {exc}")
            return [
                {"role": "system", "content": "相关历史信息: 暂无相关历史记录"},
                {"role": "user", "content": query},
            ]

    def generate_response(self, user_input: str, context: list[dict[str, Any]]) -> str:
        """使用模型生成客服回复。"""
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({"context": context, "input": user_input})
            return response.content
        except Exception as exc:
            logger.error(f"生成回复时出错: {exc}")
            return "抱歉，我现在遇到了一些技术问题，请稍后再试。如有紧急情况，请联系人工客服。"

    def save_interaction(self, user_id: str, user_input: str, assistant_response: str) -> None:
        """把本轮用户和助手消息写回 Mem0。"""
        try:
            interaction = [
                {"role": "user", "content": user_input},
                {"role": "assistant", "content": assistant_response},
            ]
            self.mem0.add(interaction, user_id=user_id)
            logger.debug(f"交互记录已保存 - 用户 ID: {user_id}")
        except Exception as exc:
            logger.warning(f"保存交互记录时出错: {exc}")

    def chat_turn(self, user_input: str, user_id: str) -> str:
        """处理一轮用户输入。"""
        try:
            context = self.retrieve_context(user_input, user_id)
            response = self.generate_response(user_input, context)
            self.save_interaction(user_id, user_input, response)
            return response
        except Exception as exc:
            logger.error(f"处理对话时出错: {exc}")
            return "抱歉，处理您的请求时出现了问题。请重新尝试或联系技术支持。"

    def run_interactive_chat(self) -> None:
        """运行交互式快递客服示例。"""
        print("=" * 60)
        print("欢迎使用智能快递客服助手！")
        print("=" * 60)
        print("我可以帮您处理各种快递相关问题：")
        print("快递查询、寄件服务、问题处理、服务介绍等")
        print("输入 'quit'、'exit' 或 '再见' 结束对话")
        print("=" * 60)

        user_id = input("请输入您的客户ID（或直接回车使用默认ID）: ").strip()
        if not user_id:
            user_id = "customer_001"

        print(f"您好！您的客户ID是: {user_id}")
        print("-" * 60)

        while True:
            try:
                user_input = input("您: ").strip()
                if user_input.lower() in ["quit", "exit", "再见", "退出", "bye"]:
                    print("快递客服: 感谢您使用我们的服务！祝您生活愉快，期待下次为您服务！")
                    break

                if not user_input:
                    print("快递客服: 请输入您的问题，我很乐意为您提供帮助。")
                    continue

                response = self.chat_turn(user_input, user_id)
                print(f"快递客服: {response}\n")
            except KeyboardInterrupt:
                print("\n快递客服: 感谢您使用我们的服务！再见！")
                break
            except Exception as exc:
                logger.error(f"交互过程中出错: {exc}")
                print("快递客服: 系统出现异常，请稍后重试。")


def main() -> None:
    """脚本入口。"""
    load_environment()
    ensure_legacy_memory_support()
    require_dashscope_key()

    print("=== ConversationBufferMemory Demo ===")
    run_conversation_buffer_demo()

    print("\n=== Mem0 Customer Service Demo ===")
    try:
        service = ExpressCustomerService()
        service.run_interactive_chat()
    except Exception as exc:
        print(f"程序启动失败: {exc}")
        print("\n请检查以下事项：")
        print("1. 确保已设置 DASHSCOPE_API_KEY 环境变量")
        print("2. 确保网络连接正常")
        print("3. 确保 API 密钥有效且有足够权限")
        print("4. 确保已安装所有必需的依赖包，包括 mem0")


if __name__ == "__main__":
    main()
