import os
from collections.abc import AsyncIterable
from typing import Any, Dict, Literal
from langchain_core.tools import tool
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from pydantic import BaseModel
from tavily import TavilyClient

# 初始化内存存储
memory = MemorySaver()
DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"

load_dotenv()


def has_google_credentials() -> bool:
    """是否存在可用的 Google / Gemini API Key。"""
    return bool(os.getenv("GOOGLE_API_KEY") or os.getenv("GEMINI_API_KEY"))


def resolve_openai_compatible_api_key() -> str | None:
    """解析 OpenAI 兼容模型使用的 API Key。"""
    return (
        os.getenv("OPENAI_API_KEY")
        or os.getenv("DASHSCOPE_API_KEY")
        or os.getenv("API_KEY")
    )


def has_openai_compatible_credentials() -> bool:
    """是否存在可用的 OpenAI 兼容 API Key。"""
    return bool(resolve_openai_compatible_api_key())


def resolve_model_source() -> str:
    """
    解析当前应使用的模型来源。

    优先遵循显式配置；当 Google key 缺失但仓库里已有 DashScope /
    OpenAI 兼容配置时，自动回退到 openai 兼容路径。
    """
    preferred = (os.getenv("model_source") or "").strip().lower()
    if preferred in {"openai", "dashscope"}:
        return "openai"
    if preferred == "google":
        if has_google_credentials():
            return "google"
        if has_openai_compatible_credentials():
            return "openai"
        return "google"

    if has_google_credentials():
        return "google"
    return "openai"


def build_model():
    """根据当前环境变量构建可用模型实例。"""
    model_source = resolve_model_source()
    if model_source == "google":
        if not has_google_credentials():
            raise ValueError(
                "GOOGLE_API_KEY/GEMINI_API_KEY 未配置，无法使用 Google 模型。"
            )
        return ChatGoogleGenerativeAI(model="gemini-2.0-flash")

    api_key = resolve_openai_compatible_api_key()
    if not api_key:
        raise ValueError(
            "未找到可用模型密钥。请配置 DASHSCOPE_API_KEY、OPENAI_API_KEY，"
            "或使用 GOOGLE_API_KEY/GEMINI_API_KEY。"
        )

    return ChatOpenAI(
        model=os.getenv("TOOL_LLM_NAME", "qwen-plus"),
        openai_api_key=api_key,
        openai_api_base=os.getenv("TOOL_LLM_URL", DEFAULT_DASHSCOPE_BASE_URL),
        temperature=0,
    )

@tool
def search_tavily(query: str, search_depth: str = "basic") -> Dict[str, Any]:
    """使用Tavily进行网络搜索
    
    Args:
        query: 搜索查询字符串
        search_depth: 搜索深度，"basic" 或 "advanced"
        
    Returns:
        包含搜索结果或错误信息的字典
    """
    try:
        api_key = os.getenv("TAVILY_API_KEY")
        if not api_key:
            return {
                "success": False,
                "error": "TAVILY_API_KEY 未配置，当前 Web 搜索功能不可用。",
                "query": query,
            }

        tavily_client = TavilyClient(api_key=api_key)
        
        if search_depth == "advanced":
            result = tavily_client.search(query, depth="advanced", include_answer=True)
        else:
            result = tavily_client.search(query, include_answer=True)
            
        return {
            "success": True,
            "results": result.get("results", []),
            "answer": result.get("answer", ""),
            "query": query
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

class ResponseFormat(BaseModel):
    """以这种格式回应用户"""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str

class SearchAgent:
    """搜索Agent - 专门进行网络搜索的助手"""

    # 支持的输入输出类型
    SUPPORTED_CONTENT_TYPES = ["text/plain"]

    SYSTEM_INSTRUCTION = (
        "你是一个专门进行网络搜索的助手。"
        "你的主要目的是使用'search_tavily'工具来回答用户问题，提供最新、最相关的信息。"
        "如果需要用户提供更多信息来进行有效搜索，将响应状态设置为input_required。"
        "如果处理请求时发生错误，将响应状态设置为error。"
        "如果请求已完成并提供了答案，将响应状态设置为completed。"
    )

    def __init__(self):
        self.model = build_model()
        self.tools = [search_tavily]

        self.graph = create_react_agent(
            self.model,
            tools=self.tools,
            checkpointer=memory,
            prompt=self.SYSTEM_INSTRUCTION,
            response_format=ResponseFormat,
        )

    def invoke(self, query: str, sessionId: str) -> str:
        """同步调用搜索Agent"""
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': sessionId}}
        
        result = self.graph.invoke(inputs, config)
        return self._format_response(result, config)

    async def stream(self, query: str, sessionId: str) -> AsyncIterable[Dict[str, Any]]:
        """异步流式搜索"""
        inputs = {'messages': [('user', query)]}
        config = {'configurable': {'thread_id': sessionId}}

        async for item in self.graph.astream(inputs, config, stream_mode='values'):
            message = item['messages'][-1]
            if hasattr(message, 'tool_calls') and message.tool_calls:
                yield {
                    'status': 'processing',
                    'message': '正在搜索网络信息...'
                }
            elif hasattr(message, 'content'):
                yield {
                    'status': 'processing', 
                    'message': message.content
                }

        final_result = self._get_agent_response(config)
        yield final_result

    def _get_agent_response(self, config):
        """获取最终的Agent响应"""
        current_state = self.graph.get_state(config)
        structured_response = current_state.values.get('structured_response')
        
        if structured_response and isinstance(structured_response, ResponseFormat):
            return {
                'status': structured_response.status,
                'message': structured_response.message
            }
            
        return {
            'status': 'error',
            'message': '无法处理请求，请稍后重试'
        }

    def _format_response(self, result, config):
        """格式化响应"""
        response = self._get_agent_response(config)
        return f"Status: {response['status']}\nMessage: {response['message']}"

# 使用示例
if __name__ == "__main__":
    # 设置环境变量
    # os.environ["TAVILY_API_KEY"] = "your_tavily_api_key_here"
    
    agent = SearchAgent()
    result = agent.invoke("最新的AI技术发展", "test_session")
    print(result)
