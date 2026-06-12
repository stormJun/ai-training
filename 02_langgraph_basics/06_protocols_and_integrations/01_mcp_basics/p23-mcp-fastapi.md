<!-- Converted from p23-mcp-fastapi.ipynb -->

```python
%pip install -qU fastapi-mcp
```

输出：

```text
Note: you may need to restart the kernel to use updated packages.
```

```python
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
```

```python
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
```

# 客户端配置

```json
{
  "mcpServers": {
    "my-api-mcp": {
      "url": "http://localhost:8000/mcp",
      "alwaysAllow": [],
      "disabled": false
    }
  }
}
```


```json
{
  "mcpServers": {
    "my-api-mcp-proxy": {
      "command": "/Full/Path/To/Your/Executable/mcp-proxy",
      "args": ["<http://127.0.0.1:8000/mcp>"]
    }
  }
}
```

```python
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
```

输出：

```text
C:\Users\Administrator\AppData\Local\Temp\ipykernel_9232\1148449145.py:24: DeprecationWarning: `example` has been deprecated, please use `examples` instead
  user_id: int = Path(..., description="用户的唯一数字标识符，必须是正整数", example=123)
C:\Users\Administrator\AppData\Local\Temp\ipykernel_9232\1148449145.py:38: DeprecationWarning: mount() is deprecated and will be removed in a future version. Use mount_http() for HTTP transport (recommended) or mount_sse() for SSE transport instead.
  mcp.mount()
INFO:     Started server process [9232]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     127.0.0.1:57507 - "GET /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53295 - "GET /mcp HTTP/1.1" 200 OK
INFO:     127.0.0.1:53297 - "POST /mcp/messages/?session_id=ab5babaa31ed445a940efdd847441da9 HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:53298 - "POST /mcp/messages/?session_id=ab5babaa31ed445a940efdd847441da9 HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:53299 - "POST /mcp/messages/?session_id=ab5babaa31ed445a940efdd847441da9 HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:53300 - "POST /mcp/messages/?session_id=ab5babaa31ed445a940efdd847441da9 HTTP/1.1" 202 Accepted
INFO:     127.0.0.1:53301 - "POST /mcp/messages/?session_id=ab5babaa31ed445a940efdd847441da9 HTTP/1.1" 202 Accepted
INFO:     Shutting down
ERROR:    Exception in ASGI application
Traceback (most recent call last):
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 409, in run_asgi
    result = await app(  # type: ignore[func-returns-value]
             ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\uvicorn\middleware\proxy_headers.py", line 60, in __call__
    return await self.app(scope, receive, send)
           ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\fastapi\applications.py", line 1054, in __call__
    await super().__call__(scope, receive, send)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\applications.py", line 113, in __call__
    await self.middleware_stack(scope, receive, send)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\middleware\errors.py", line 186, in __call__
    raise exc
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\middleware\errors.py", line 164, in __call__
    await self.app(scope, receive, _send)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\middleware\exceptions.py", line 63, in __call__
    await wrap_app_handling_exceptions(self.app, conn)(scope, receive, send)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\routing.py", line 716, in __call__
    await self.middleware_stack(scope, receive, send)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\routing.py", line 736, in app
    await route.handle(scope, receive, send)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\routing.py", line 290, in handle
    await self.app(scope, receive, send)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\routing.py", line 78, in app
    await wrap_app_handling_exceptions(app, request)(scope, receive, send)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\_exception_handler.py", line 53, in wrapped_app
    raise exc
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\_exception_handler.py", line 42, in wrapped_app
    await app(scope, receive, sender)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\routing.py", line 76, in app
    await response(scope, receive, send)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\responses.py", line 158, in __call__
    await send(
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\_exception_handler.py", line 39, in sender
    await send(message)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\_exception_handler.py", line 39, in sender
    await send(message)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\starlette\middleware\errors.py", line 161, in _send
    await send(message)
  File "d:\software\miniconda3\envs\MLOps\Lib\site-packages\uvicorn\protocols\http\httptools_impl.py", line 517, in send
    raise RuntimeError(msg % message_type)
RuntimeError: Expected ASGI message 'http.response.body', but got 'http.response.start'.
INFO:     Waiting for application shutdown.
INFO:     Application shutdown complete.
INFO:     Finished server process [9232]
```
