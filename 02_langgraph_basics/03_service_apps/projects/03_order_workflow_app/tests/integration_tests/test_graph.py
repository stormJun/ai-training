import pytest

from agent import graph

pytestmark = pytest.mark.anyio


async def test_agent_simple_passthrough() -> None:
    inputs = {
        "user_input": "我想查询订单状态",
        "intent": "",
        "order_info": {},
        "response": "",
        "next_action": "",
        "messages": [],
    }
    res = await graph.ainvoke(
        inputs,
        context={"user_id": "integration-user", "session_id": "integration-session"},
    )
    assert res is not None
