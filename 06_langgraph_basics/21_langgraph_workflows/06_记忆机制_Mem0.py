# %% [markdown]
# ## 内存记忆

# %%

import importlib.util
import os
import sys
from pathlib import Path

from dotenv import load_dotenv

# 本 notebook 依赖 21_langgraph_workflows 的依赖版本（LangChain 0.3.x）。
# 如果你看到 `No module named 'langchain.memory'`，通常是 Jupyter kernel 指到了仓库根目录的 `.venv`（langchain 1.x）。
if importlib.util.find_spec("langchain.memory") is None:
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
        "请切换到 21_langgraph_workflows 的虚拟环境/内核后再运行：\n"
        "  cd 21_langgraph_workflows && uv sync --locked\n"
        "  cd 21_langgraph_workflows && uv run python -m ipykernel install --user --name 21_langgraph_workflows --display-name \"21_langgraph_workflows\"\n"
    )

from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.chat_models import ChatTongyi

# 读取环境变量：优先当前目录的 .env；如果你从仓库根目录运行，再尝试 21_langgraph_workflows/.env
if not load_dotenv():
    load_dotenv(Path("21_langgraph_workflows/.env"))

if not os.getenv("DASHSCOPE_API_KEY"):
    raise RuntimeError("Missing DASHSCOPE_API_KEY. Set env var or fill 21_langgraph_workflows/.env")

# 使用通义千问（需要设置 DASHSCOPE_API_KEY；见 21_langgraph_workflows/.env）
llm = ChatTongyi(model_name="qwen-turbo", temperature=0.7, streaming=False)

template = """You are a chatbot having a conversation with a human.
{chat_history}
Human: {human_input}
Chatbot:"""

prompt = PromptTemplate(
    input_variables=["chat_history", "human_input"], template=template
)

memory = ConversationBufferMemory(memory_key="chat_history")

llm_chain = LLMChain(
    llm=llm,
    prompt=prompt,
    verbose=True,
    memory=memory,
)

human_input="Hi there my friend"
print(llm_chain.predict(human_input=human_input))

human_input="Not too bad - how are you?"
print(llm_chain.predict(human_input=human_input))

# %% [markdown]
# ## ConversationBufferWindowMemory 类
#
# ConversationBufferWindowMemory 类是 ConversationMemory 的一个子类，它维护一个窗口内存，只存储最近指定数量的交互，并丢弃其余部分。
#
# 可以帮助限制内存的大小，以便适应特定的应用场景。
#
# 使用 ConversationBufferWindowMemory，您可以在对话中只保留最近的一些交互，以控制内存的大小。
#
# 这对于资源受限的环境或需要快速丢弃旧交互的场景非常有用。
#
#
# 例如：
#
# ```python
# import os
# from langchain.memory import ConversationBufferWindowMemory
# from langchain.chains import ConversationChain
# from langchain_openai import OpenAI
#
# # 初始化LLM - 使用通义千问
# llm = OpenAI(
# temperature=0.3,
# openai_api_key=os.getenv("DASHSCOPE_API_KEY"),
# openai_api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
# model_name="qwen-turbo"
# )
#
# # 创建窗口记忆 - 只保留最近2轮对话
# memory = ConversationBufferWindowMemory(k=2)
#
# # 创建对话链
# conversation_with_memory = ConversationChain(
# llm=llm,
# memory=memory,
# verbose=True
# )
#
# # 第1轮：客户自我介绍
# print("第1轮对话：")
# response1 = conversation_with_memory.predict(
# input="你好，我是张先生，我经常需要寄送电子产品到全国各地"
# )
# print(f"客服回复: {response1}\n")
#
# # 第2轮：说明业务需求
# print("第2轮对话：")
# response2 = conversation_with_memory.predict(
# input="我主要做电商生意，每天大概有50-100个包裹需要发货，主要是手机配件和数码产品"
# )
# print(f"客服回复: {response2}\n")
#
# # 第3轮：询问物流方案
# print("第3轮对话：")
# response3 = conversation_with_memory.predict(
# input="你能为我推荐一个适合的物流方案吗？我希望价格合理，时效稳定"
# )
# print(f"客服回复: {response3}\n")
#
# # 第4轮：询问更多选项
# print("第4轮对话：")
# response4 = conversation_with_memory.predict(
# input="除了刚才的方案，你还能给出更多选项吗？我想对比一下"
# )
# print(f"客服回复: {response4}\n")
#
# # 第5轮：测试记忆窗口（应该忘记第1轮的内容）
# print("第5轮对话（测试记忆窗口）：")
# response5 = conversation_with_memory.predict(
# input="你还记得我的名字吗？我是做什么生意的？"
# )
# print(f"客服回复: {response5}\n")
#
# # 查看当前记忆内容
# print("=== 当前记忆内容 ===")
# print(memory.buffer)

# %% [markdown]
# ## Redis
#
# [langchain Redis 持久记忆](https://python.langchain.com/docs/integrations/memory/redis_chat_message_history/)

# %% [markdown]
# ## Mem0 技术简介
# ### Mem0是什么？
#
# Mem0是一个专门为AI应用设计的记忆层框架，它能够为大语言模型（LLM）提供持久化的记忆能力。简单来说，它让AI能够"记住"之前的对话和用户偏好，实现真正的个性化交互。
#
# ### 核心工作原理：
#
# 记忆存储：将用户交互、偏好、上下文信息存储在向量数据库中
# 智能检索：通过语义搜索快速找到相关的历史信息
# 上下文注入：将检索到的记忆信息注入到当前对话中
# 动态更新：根据新的交互持续更新和优化记忆内容
#
# ### Mem0 的核心优势
#
# 1. 持久化记忆能力
# 突破了传统LLM的上下文窗口限制
# 能够跨会话保持用户信息和偏好
# 支持长期记忆积累和演化
#
# 2. 个性化体验
# 根据用户历史行为提供定制化服务
# 学习用户偏好和习惯
# 提供连贯的多轮对话体验
#
# 3. 灵活的架构设计
# 支持多种向量数据库（Qdrant、Chroma、Pinecone等）
# 兼容主流LLM提供商（OpenAI、Anthropic、通义千问等）
# 模块化设计，易于集成和扩展
#
# 4. 智能记忆管理
# 自动提取和总结关键信息
# 智能去重和记忆优化
# 支持记忆的增删改查操作

# %%
# 依赖已在 21_langgraph_workflows/pyproject.toml（uv.lock）里锁定；推荐在终端安装，而不是在 notebook 里 `pip install` 覆盖环境：
# cd 21_langgraph_workflows && uv sync --locked

# %%
# 快递行业智能客服助手 - 使用通义千问和Mem0
import os
import logging
from typing import List, Dict, Optional
from openai import OpenAI
from mem0 import Memory
from mem0.configs.base import MemoryConfig
from mem0.embeddings.configs import EmbedderConfig
from mem0.llms.configs import LlmConfig
from langchain_openai import ChatOpenAI
from langchain_core.messages import SystemMessage, HumanMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ExpressCustomerService:
    def __init__(self):
        """初始化快递客服助手"""
        self.api_key = self._get_api_key()
        self.base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
        
        # 初始化组件
        self.openai_client = None
        self.llm = None
        self.mem0 = None
        self.prompt = None
        
        # 初始化所有组件
        self._initialize_components()
    
    def _get_api_key(self) -> str:
        """获取API密钥并验证"""
        api_key = os.getenv("DASHSCOPE_API_KEY")
        if not api_key:
            raise ValueError(
                "未找到DASHSCOPE_API_KEY环境变量。\n"
                "请设置环境变量：export DASHSCOPE_API_KEY='your_api_key_here'"
            )
        logger.info("API密钥已加载")
        return api_key
    
    def _test_api_connection(self) -> bool:
        """测试API连接"""
        try:
            response = self.openai_client.chat.completions.create(
                model="qwen-turbo",
                messages=[{"role": "user", "content": "测试连接"}],
                max_tokens=10
            )
            logger.info("API连接测试成功")
            return True
        except Exception as e:
            logger.error(f"API连接测试失败: {str(e)}")
            return False
    
    def _initialize_components(self):
        """初始化所有组件"""
        try:
            # 1. 初始化OpenAI客户端
            self.openai_client = OpenAI(
                api_key=self.api_key,
                base_url=self.base_url,
            )
            logger.info("OpenAI客户端初始化成功")
            
            # 2. 测试API连接
            if not self._test_api_connection():
                raise Exception("API连接失败，请检查API密钥和网络连接")
            
            # 3. 初始化LangChain LLM
            self.llm = ChatOpenAI(
                temperature=0.3,
                openai_api_key=self.api_key,
                openai_api_base=self.base_url,
                model="qwen-turbo"
            )
            logger.info("LangChain LLM初始化成功")
            
            # 4. 初始化Mem0配置（使用更兼容的配置）
            config = MemoryConfig(
                llm=LlmConfig(
                    provider="openai",
                    config={
                        "model": "qwen-turbo",
                        "api_key": self.api_key,
                        "openai_base_url": self.base_url
                    }
                ),
                embedder=EmbedderConfig(
                    provider="openai",
                    config={
                        "model": "text-embedding-v1",  # 修正为正确的embedding模型
                        "api_key": self.api_key,
                        "openai_base_url": self.base_url
                    }
                )
            )
            
            # 5. 初始化Mem0
            self.mem0 = Memory(config=config)
            logger.info("Mem0记忆系统初始化成功")
            
            # 6. 初始化提示词模板
            self._initialize_prompt()
            
        except Exception as e:
            logger.error(f"组件初始化失败: {str(e)}")
            raise
    
    def _initialize_prompt(self):
        """初始化提示词模板"""
        self.prompt = ChatPromptTemplate.from_messages([
            SystemMessage(content="""您是一位专业的快递行业智能客服助手。请使用提供的上下文信息来个性化您的回复，记住用户的偏好和历史交互记录。

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

                请用中文回复，语气亲切专业。"""),
            MessagesPlaceholder(variable_name="context"),
            HumanMessage(content="{input}")
        ])
    
    def retrieve_context(self, query: str, user_id: str) -> List[Dict]:
        """从Mem0检索相关上下文信息"""
        try:
            memories = self.mem0.search(query, user_id=user_id)
            
            # 安全地处理搜索结果
            if memories and "results" in memories and memories["results"]:
                serialized_memories = ' '.join([
                    mem.get("memory", "") for mem in memories["results"]
                ])
            else:
                serialized_memories = "暂无相关历史记录"
            
            context = [
                {
                    "role": "system", 
                    "content": f"相关历史信息: {serialized_memories}"
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
            return context
            
        except Exception as e:
            logger.warning(f"检索上下文时出错: {str(e)}")
            # 返回基础上下文
            return [
                {
                    "role": "system", 
                    "content": "相关历史信息: 暂无相关历史记录"
                },
                {
                    "role": "user",
                    "content": query
                }
            ]
    
    def generate_response(self, user_input: str, context: List[Dict]) -> str:
        """使用语言模型生成回复"""
        try:
            chain = self.prompt | self.llm
            response = chain.invoke({
                "context": context,
                "input": user_input
            })
            return response.content
            
        except Exception as e:
            logger.error(f"生成回复时出错: {str(e)}")
            return "抱歉，我现在遇到了一些技术问题，请稍后再试。如有紧急情况，请联系人工客服。"
    
    def save_interaction(self, user_id: str, user_input: str, assistant_response: str):
        """将交互记录保存到Mem0"""
        try:
            interaction = [
                {
                    "role": "user",
                    "content": user_input
                },
                {
                    "role": "assistant",
                    "content": assistant_response
                }
            ]
            self.mem0.add(interaction, user_id=user_id)
            logger.debug(f"交互记录已保存 - 用户ID: {user_id}")
            
        except Exception as e:
            logger.warning(f"保存交互记录时出错: {str(e)}")
            # 不影响主要功能，只记录警告
    
    def chat_turn(self, user_input: str, user_id: str) -> str:
        """处理一轮对话"""
        try:
            # 检索上下文
            context = self.retrieve_context(user_input, user_id)
            
            # 生成回复
            response = self.generate_response(user_input, context)
            
            # 保存交互记录
            self.save_interaction(user_id, user_input, response)
            
            return response
            
        except Exception as e:
            logger.error(f"处理对话时出错: {str(e)}")
            return "抱歉，处理您的请求时出现了问题。请重新尝试或联系技术支持。"
    
    def run_interactive_chat(self):
        """运行交互式聊天"""
        print("=" * 60)
        print("欢迎使用智能快递客服助手！")
        print("=" * 60)
        print("我可以帮您处理各种快递相关问题：")
        print("快递查询、寄件服务、问题处理、服务介绍等")
        print("输入 'quit'、'exit' 或 '再见' 结束对话")
        print("=" * 60)
        
        # 可以根据实际情况设置用户ID
        ###### 区分用户 ， 与 session_id 结合可以区分会话
        user_id = input("请输入您的客户ID（或直接回车使用默认ID）: ").strip()
        if not user_id:
            user_id = "customer_001"
        
        # session_id = f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{user_id}"
        # 混合模式：用户+会话
        # composite_id = f"{user_id}_session_{session_count}"

        print(f"您好！您的客户ID是: {user_id}")
        print("-" * 60)
        
        while True:
            try:
                user_input = input("您: ").strip()
                
                if user_input.lower() in ['quit', 'exit', '再见', '退出', 'bye']:
                    print("快递客服: 感谢您使用我们的服务！祝您生活愉快，期待下次为您服务！")
                    break
                
                if not user_input:
                    print("快递客服: 请输入您的问题，我很乐意为您提供帮助。")
                    continue
                
                # 处理用户输入
                response = self.chat_turn(user_input, user_id)
                print(f"快递客服: {response}\n")
                
            except KeyboardInterrupt:
                print("\n快递客服: 感谢您使用我们的服务！再见！")
                break
            except Exception as e:
                logger.error(f"交互过程中出错: {str(e)}")
                print("快递客服: 系统出现异常，请稍后重试。")

def main():
    """主程序入口"""
    try:
        # 创建客服助手实例
        service = ExpressCustomerService()
        
        # 运行交互式聊天
        service.run_interactive_chat()
        
    except Exception as e:
        print(f"程序启动失败: {str(e)}")
        print("\n请检查以下事项：")
        print("1. 确保已设置DASHSCOPE_API_KEY环境变量")
        print("2. 确保网络连接正常")
        print("3. 确保API密钥有效且有足够权限")
        print("4. 确保已安装所有必需的依赖包")

if __name__ == "__main__":
    main()

# %%
