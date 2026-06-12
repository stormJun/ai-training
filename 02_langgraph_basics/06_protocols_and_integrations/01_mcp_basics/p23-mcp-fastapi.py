# -*- coding: utf-8 -*-
# Converted from p23-mcp-fastapi.ipynb

# %%
# NOTEBOOK_MAGIC: %pip install -qU fastapi-mcp

# %%
# 最简单的 FastAPI + MCP 示例

from fastapi import FastAPI
from fastapi_mcp import FastApiMCP
import nest_asyncio
nest_asyncio.apply()

# Your existing FastAPI app
app = FastAPI()

# Add MCP server to your FastAPI app
mcp = FastApiMCP(
    app,
    name="My API MCP",
    describe_all_responses=True,     # 在工具描述中包含所有可能的响应模式
    describe_full_response_schema=True  # 在工具描述中包含完整的 JSON 模式
)

# Mount the MCP server to your app
mcp.mount()

# Run your app as usual
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# %%
# 与原始 FastAPI 应用分开部署
from fastapi import FastAPI
from fastapi_mcp import FastApiMCP

# 您的 API 应用
api_app = FastAPI()
# ... 在 api_app 上定义您的 API 端点 ...

# 一个单独的 MCP 服务器应用
mcp_app = FastAPI()

# 从 API 应用创建 MCP 服务器
mcp = FastApiMCP(api_app)

# 将 MCP 服务器挂载到单独的应用
mcp.mount(mcp_app)

# 现在您可以分别运行两个应用：
# uvicorn main:api_app --host api-host --port 8001
# uvicorn main:mcp_app --host mcp-host --port 8000

# %% [markdown]
# # 客户端配置
#
# ```json
# {
#   "mcpServers": {
#     "my-api-mcp": {
#       "url": "http://localhost:8000/mcp",
#       "alwaysAllow": [],
#       "disabled": false
#     }
#   }
# }
# ```
#
#
# ```json
# {
#   "mcpServers": {
#     "my-api-mcp-proxy": {
#       "command": "/Full/Path/To/Your/Executable/mcp-proxy",
#       "args": ["<http://127.0.0.1:8000/mcp>"]
#     }
#   }
# }
# ```

# %%
# MCP 示例

from fastapi import FastAPI, Path
from fastapi_mcp import FastApiMCP
import nest_asyncio
nest_asyncio.apply()

# Your existing FastAPI app
app = FastAPI()

# # (不推荐) 自动生成的 operation_id（类似于 "read_user_users__user_id__get"）
# @app.get("/users/{user_id}")
# async def read_user(user_id: int):
#     return {"user_id": user_id}

# 显式 operation_id（工具将被命名为 "get_user_info"）
@app.get(
    "/users/{user_id}",
    operation_id="get_user_info",
    summary="获取用户信息",
    description="根据用户ID获取用户的详细信息",
    response_description="包含用户基本信息的JSON对象")
async def read_user(
    user_id: int = Path(..., description="用户的唯一数字标识符，必须是正整数", example=123)
):
    return {"user_id": user_id}


# Add MCP server to your FastAPI app
mcp = FastApiMCP(
    app,
    name="My API MCP",
    describe_all_responses=True,     # 在工具描述中包含所有可能的响应模式
    describe_full_response_schema=True,  # 在工具描述中包含完整的 JSON 模式
)

# Mount the MCP server to your app
mcp.mount()

# Run your app as usual
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)

# %% [markdown]
