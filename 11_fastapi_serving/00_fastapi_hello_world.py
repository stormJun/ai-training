"""最小 FastAPI hello world 示例。

这个文件故意保持得很小，目的是让读者先看清最基础的几个点：

1. `FastAPI(...)` 怎么创建应用对象
2. `@app.get(...)` 这种装饰器怎么注册路由
3. 路径参数怎么映射到 Python 函数参数
4. 返回 Python 字典时，FastAPI 为什么会自动转成 JSON
5. `uvicorn` 是怎么把 FastAPI 应用真正跑起来的
"""

from fastapi import FastAPI


# `FastAPI(...)` 用来创建应用对象。
# 可以把 `app` 理解成整个 Web 服务的根容器，后续会往里面挂：
# - 路由定义
# - 应用标题、版本等元数据
# - 中间件、依赖注入、生命周期钩子等扩展能力
app = FastAPI(title="FastAPI Hello World Demo", version="0.1.0")


# `@app.get("/")` 是 Python 装饰器语法。
# 装饰器会“包住”下面这个函数，并附加额外行为。
# 在 FastAPI 里，它的语义是：
# “把下面的 `root` 函数注册为 HTTP GET / 的处理函数”。
@app.get("/")
async def root():
    # 这里直接返回 Python 字典就够了。
    # FastAPI 会自动帮我们做两件事：
    # 1. 把字典序列化成 JSON
    # 2. 设置正确的响应头（如 application/json）
    return {
        "message": "Welcome to the FastAPI hello world demo",
        "endpoints": {
            "root": "/",
            "hello": "/hello",
            "health": "/health",
        },
    }


# 第二个 GET 路由。
# 因为函数参数为空，所以这个接口不需要从 URL、查询参数或请求体里再读取额外数据。
@app.get("/hello")
async def hello():
    return {"message": "Hello, World!"}


# `"/hello/{name}"` 里的 `{name}` 叫“路径参数”。
# 访问 `/hello/song` 时，FastAPI 会把 URL 里的 `song` 取出来，
# 并作为参数传给下面这个函数里的 `name`。
#
# `name: str` 是 Python 的类型标注语法。
# FastAPI 会利用这些类型标注：
# - 生成接口文档
# - 做基础参数校验
# - 帮助编辑器提供更好的类型提示
@app.get("/hello/{name}")
async def hello_name(name: str):
    # 这里用的是 Python f-string（格式化字符串）语法：
    # f"...{变量}..."
    # 它会把变量 `name` 的值插进字符串里。
    return {"message": f"Hello, {name}!"}


# `/health` 是后端服务里非常常见的健康检查接口。
# 它的重点不是业务功能，而是让调用方、监控系统、负载均衡器快速判断：
# “这个服务进程现在是不是活着、是不是至少能正常响应请求”。
@app.get("/health")
async def health():
    return {"status": "ok"}


# `if __name__ == "__main__":` 是 Python 里非常经典的入口写法。
# 含义是：
# - 如果这个文件是“直接执行”的，就进入这个分支
# - 如果这个文件是“被别的文件 import 进来”的，就不会进入这个分支
#
# 例如：
# - `python 00_fastapi_hello_world.py` -> 会进入
# - `import 00_fastapi_hello_world` -> 不会进入
if __name__ == "__main__":
    import uvicorn

    # Uvicorn 是一个 ASGI Server。
    # FastAPI 应用本质上是一个 ASGI 应用，所以真正负责：
    # - 打开端口
    # - 接收 HTTP 请求
    # - 把请求转发给 `app`
    # - 再把响应返回给客户端
    # 的，是 uvicorn 这个服务器进程。
    #
    # `host="0.0.0.0"` 表示监听所有网卡地址。
    # `port=8000` 表示服务监听在 8000 端口。
    uvicorn.run(app, host="0.0.0.0", port=8000)
