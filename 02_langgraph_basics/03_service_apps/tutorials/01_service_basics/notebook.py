# -*- coding: utf-8 -*-
# Converted from notebook.ipynb

# %% [markdown]
# ## FastAPI 对话服务封装方案
#

# Unsupported cell 2: raw

# %%
# main.py
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import Dict, List, Optional
import uvicorn
import asyncio
from chat_chain import ChatChain
from session_manager import SessionManager

app = FastAPI(
    title="智能对话服务",
    description="基于 LangChain 0.3 的对话 API",
    version="1.0.0"
)

# 全局实例
chat_chain = None
session_manager = SessionManager()

@app.on_event("startup")
async def startup_event():
    """应用启动时初始化"""
    global chat_chain
    chat_chain = ChatChain()
    await chat_chain.initialize()

class ChatRequest(BaseModel):
    session_id: str
    message: str

class ChatResponse(BaseModel):
    reply: str
    session_id: str

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """对话接口"""
    try:
        # 获取会话历史
        history = session_manager.get_history(request.session_id)

        # 调用对话链
        reply = await chat_chain.process_message(
            message=request.message,
            history=history
        )

        # 更新会话历史
        session_manager.add_message(
            session_id=request.session_id,
            user_message=request.message,
            bot_reply=reply
        )

        return ChatResponse(
            reply=reply,
            session_id=request.session_id
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"处理失败: {str(e)}")

@app.get("/health")
async def health_check():
    """健康检查"""
    return {"status": "healthy", "langchain_version": "0.3.x"}

@app.delete("/session/{session_id}")
async def clear_session(session_id: str):
    """清除会话历史"""
    session_manager.clear_session(session_id)
    return {"message": f"会话 {session_id} 已清除"}

@app.get("/session/{session_id}/history")
async def get_session_history(session_id: str):
    """获取会话历史"""
    history = session_manager.get_history(session_id)
    return {"session_id": session_id, "history": history}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)

# %%
# chat_chain.py - LangChain 对话链
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableLambda
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_community.llms import Tongyi
from typing import List, Dict, Any
import asyncio

class ChatChain:
    def __init__(self):
        self.llm = None
        self.chain = None
        self.parser = StrOutputParser()

    async def initialize(self):
        """异步初始化"""
        # 初始化 LLM
        self.llm = Tongyi(
            temperature=0.7,
            model_name="qwen-turbo"  # LangChain 0.3 推荐明确指定模型
        )

        # 创建提示模板 - LangChain 0.3 风格
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", """你是一个智能客服助手，请遵循以下规则：
                1. 友好、专业地回答用户问题
                2. 如果不确定答案，诚实地说不知道
                3. 保持回答简洁明了
                4. 根据对话历史提供连贯的回复
                5. 用中文回答"""),
            MessagesPlaceholder(variable_name="history"),
            ("human", "{message}")
        ])

        # 构建链 - LangChain 0.3 LCEL 语法
        self.chain = (
            RunnablePassthrough.assign(
                history=RunnableLambda(self._format_history)
            )
            | self.prompt
            | self.llm
            | self.parser
        )

    async def process_message(self, message: str, history: List[Dict] = None) -> str:
        """处理用户消息"""
        try:
            # 准备输入数据
            input_data = {
                "message": message,
                "raw_history": history or []
            }

            # 异步调用链
            response = await self.chain.ainvoke(input_data)

            return response.strip()

        except Exception as e:
            print(f"处理消息时出错: {e}")
            return "抱歉，我现在无法处理您的请求，请稍后再试。"

    def _format_history(self, input_data: Dict[str, Any]) -> List:
        """格式化历史消息为 LangChain 消息格式"""
        history = input_data.get("raw_history", [])

        if not history:
            return []

        messages = []
        # 只保留最近5轮对话
        recent_history = history[-5:] if len(history) > 5 else history

        for item in recent_history:
            messages.append(HumanMessage(content=item["user_message"]))
            messages.append(AIMessage(content=item["bot_reply"]))

        return messages

# %%
# session_manager.py - 会话管理器
from typing import Dict, List, Optional
import time
from collections import defaultdict
import json
from datetime import datetime

class SessionManager:
    def __init__(self, max_history_length: int = 10):
        self.sessions: Dict[str, List[Dict]] = defaultdict(list)
        self.max_history_length = max_history_length
        self.last_activity: Dict[str, float] = {}

    def get_history(self, session_id: str) -> List[Dict]:
        """获取会话历史"""
        self._update_activity(session_id)
        return self.sessions.get(session_id, [])

    def add_message(self, session_id: str, user_message: str, bot_reply: str):
        """添加对话记录"""
        self._update_activity(session_id)

        message_record = {
            "user_message": user_message,
            "bot_reply": bot_reply,
            "timestamp": datetime.now().isoformat(),
            "unix_timestamp": time.time()
        }

        self.sessions[session_id].append(message_record)

        # 限制历史长度
        if len(self.sessions[session_id]) > self.max_history_length:
            self.sessions[session_id] = self.sessions[session_id][-self.max_history_length:]

    def clear_session(self, session_id: str):
        """清除会话"""
        if session_id in self.sessions:
            del self.sessions[session_id]
        if session_id in self.last_activity:
            del self.last_activity[session_id]

    def get_session_stats(self) -> Dict:
        """获取会话统计信息"""
        return {
            "total_sessions": len(self.sessions),
            "active_sessions": len([
                s for s, t in self.last_activity.items()
                if time.time() - t < 3600  # 1小时内活跃
            ]),
            "total_messages": sum(len(history) for history in self.sessions.values())
        }

    def _update_activity(self, session_id: str):
        """更新会话活跃时间"""
        self.last_activity[session_id] = time.time()

    def cleanup_inactive_sessions(self, timeout_hours: int = 24):
        """清理不活跃的会话"""
        current_time = time.time()
        timeout_seconds = timeout_hours * 3600

        inactive_sessions = [
            session_id for session_id, last_time in self.last_activity.items()
            if current_time - last_time > timeout_seconds
        ]

        for session_id in inactive_sessions:
            self.clear_session(session_id)

        return len(inactive_sessions)

# %%
# test_client.py - 测试客户端
import requests
import json
import time

class ChatClient:
    def __init__(self, base_url: str = "http://localhost:8000"):
        self.base_url = base_url
        self.session_id = f"test_user_{int(time.time())}"

    def send_message(self, message: str) -> dict:
        """发送消息"""
        url = f"{self.base_url}/chat"
        payload = {
            "session_id": self.session_id,
            "message": message
        }

        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def get_history(self) -> dict:
        """获取历史记录"""
        url = f"{self.base_url}/session/{self.session_id}/history"
        try:
            response = requests.get(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

    def clear_session(self) -> dict:
        """清除会话"""
        url = f"{self.base_url}/session/{self.session_id}"
        try:
            response = requests.delete(url)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            return {"error": str(e)}

def main():
    """测试主函数"""
    client = ChatClient()

    print(f"开始测试对话服务 (会话ID: {client.session_id})")
    print("=" * 50)

    # 测试对话
    test_messages = [
        "你好",
        "你能做什么？",
        "请介绍一下你自己",
        "谢谢你的帮助"
    ]

    for message in test_messages:
        print(f" 用户: {message}")

        result = client.send_message(message)
        if "error" in result:
            print(f" 错误: {result['error']}")
        else:
            print(f" 助手: {result['reply']}")

        print("-" * 30)
        time.sleep(1)

    # 获取历史记录
    print("\n 获取对话历史:")
    history = client.get_history()
    if "error" not in history:
        for i, record in enumerate(history.get("history", []), 1):
            print(f"{i}. 用户: {record['user_message']}")
            print(f"   助手: {record['bot_reply']}")
            print(f"   时间: {record['timestamp']}")

    # 清除会话
    print(f"\n 清除会话: {client.clear_session()}")

if __name__ == "__main__":
    main()

# %%
# 启动服务
python main.py

# 测试服务
python test_client.py

# curl 测试
# NOTEBOOK_MAGIC: !curl -X POST "http://localhost:8000/chat" \
     -H "Content-Type: application/json" \
     -d '{"session_id": "user_001", "message": "你好"}'

# Unsupported cell 8: raw
