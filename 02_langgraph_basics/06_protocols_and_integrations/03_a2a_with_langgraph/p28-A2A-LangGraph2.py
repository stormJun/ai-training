import importlib.util
import logging
import os
import sys
from pathlib import Path
from typing import List, AsyncGenerator

import click
import httpx
import uvicorn
from dotenv import load_dotenv

# 导入我们之前创建的SearchAgent
_COMPANION_PATH = Path(__file__).with_name("p28-A2A-LangGraph.py")
_COMPANION_SPEC = importlib.util.spec_from_file_location(
    "p28_a2a_langgraph_companion",
    _COMPANION_PATH,
)
if _COMPANION_SPEC is None or _COMPANION_SPEC.loader is None:
    raise ImportError(f"无法加载依赖脚本: {_COMPANION_PATH}")
_COMPANION_MODULE = importlib.util.module_from_spec(_COMPANION_SPEC)
_COMPANION_SPEC.loader.exec_module(_COMPANION_MODULE)
SearchAgent = _COMPANION_MODULE.SearchAgent
ResponseFormat = _COMPANION_MODULE.ResponseFormat

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MissingAPIKeyError(Exception):
    """Exception for missing API key."""


def import_a2a_components():
    """按需导入 A2A 运行时依赖。"""
    from a2a.server.apps import A2AStarletteApplication
    from a2a.server.request_handlers import DefaultRequestHandler
    from a2a.server.tasks import (
        BasePushNotificationSender,
        InMemoryPushNotificationConfigStore,
        InMemoryTaskStore,
    )
    from a2a.types import AgentCapabilities, AgentCard, AgentSkill

    return {
        "A2AStarletteApplication": A2AStarletteApplication,
        "DefaultRequestHandler": DefaultRequestHandler,
        "BasePushNotificationSender": BasePushNotificationSender,
        "InMemoryPushNotificationConfigStore": InMemoryPushNotificationConfigStore,
        "InMemoryTaskStore": InMemoryTaskStore,
        "AgentCapabilities": AgentCapabilities,
        "AgentCard": AgentCard,
        "AgentSkill": AgentSkill,
    }


def validate_runtime_configuration() -> dict:
    """
    校验运行所需配置。

    与原始版本不同，这里允许在缺少 TAVILY_API_KEY 时先启动服务，
    由工具层在真正执行搜索时返回清晰的降级信息。
    """
    if not (
        _COMPANION_MODULE.has_google_credentials()
        or _COMPANION_MODULE.has_openai_compatible_credentials()
    ):
        raise MissingAPIKeyError(
            "未找到可用模型密钥，请配置 GOOGLE_API_KEY / GEMINI_API_KEY，"
            "或配置 DASHSCOPE_API_KEY / OPENAI_API_KEY。"
        )

    return {
        "search_enabled": bool(os.getenv("TAVILY_API_KEY")),
        "model_source": _COMPANION_MODULE.resolve_model_source(),
    }

class SearchAgentExecutor:
    """SearchAgent的执行器，适配A2A接口"""
    
    def __init__(self, agent: SearchAgent):
        self.agent = agent
    
    async def execute_task(self, task_input: str, session_id: str) -> str:
        """执行搜索任务"""
        return self.agent.invoke(task_input, session_id)
    
    async def execute_task_streaming(self, task_input: str, session_id: str) -> AsyncGenerator[dict, None]:
        """流式执行搜索任务"""
        async for chunk in self.agent.stream(task_input, session_id):
            yield chunk

@click.command()
@click.option('--host', 'host', default='localhost')
@click.option('--port', 'port', default=10001)
def main(host, port):
    """启动搜索Agent服务器"""
    try:
        a2a = import_a2a_components()
        runtime_config = validate_runtime_configuration()
        if not runtime_config["search_enabled"]:
            logger.warning("TAVILY_API_KEY 未配置，服务将启动，但 Web 搜索功能会以降级模式运行。")

        # 配置Agent能力
        capabilities = a2a["AgentCapabilities"](streaming=True, pushNotifications=True)
        
        # 定义搜索技能
        skill = a2a["AgentSkill"](
            id="search_web",
            name="搜索工具",
            description="搜索web上的相关信息",
            tags=["Web搜索", "互联网搜索"],
            examples=["请搜索最新的黑神话悟空的消息"],
        )

        # 定义Agent卡片
        agent_card = a2a["AgentCard"](
            name="搜索助手",
            description="搜索Web上的相关信息",
            url=f"http://{host}:{port}/",
            version="1.0.0",
            defaultInputModes=SearchAgent.SUPPORTED_CONTENT_TYPES,
            defaultOutputModes=SearchAgent.SUPPORTED_CONTENT_TYPES,
            capabilities=capabilities,
            skills=[skill],
        )

        # 初始化Agent和执行器
        search_agent = SearchAgent()
        agent_executor = SearchAgentExecutor(search_agent)

        # 配置HTTP客户端和推送通知
        httpx_client = httpx.AsyncClient()
        push_config_store = a2a["InMemoryPushNotificationConfigStore"]()
        push_sender = a2a["BasePushNotificationSender"](
            httpx_client=httpx_client,
            config_store=push_config_store
        )

        # 创建请求处理器
        request_handler = a2a["DefaultRequestHandler"](
            agent_executor=agent_executor,
            task_store=a2a["InMemoryTaskStore"](),
            push_config_store=push_config_store,
            push_sender=push_sender
        )

        # 创建A2A服务器
        server = a2a["A2AStarletteApplication"](
            agent_card=agent_card, 
            http_handler=request_handler
        )

        logger.info(f"正在启动服务器，地址：{host}:{port}")
        uvicorn.run(server.build(), host=host, port=port)

    except MissingAPIKeyError as e:
        logger.error(f"错误：{e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"服务器启动过程中发生错误：{e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
