# 00 FastAPI Hello World 深入理解

这篇文档围绕 [00_fastapi_hello_world.py](/Users/songxijun/workspace/otherProject/ai-training/11_fastapi_serving/00_fastapi_hello_world.py) 这份最小示例，解释 FastAPI 背后的运行机制。

重点回答这些问题：

- `app = FastAPI(...)` 到底创建了什么
- `@app.get(...)` 为什么能把函数变成接口
- 为什么类型标注能参与接口校验和文档生成
- 返回 Python 字典为什么会自动变成 JSON
- `async def` 和 `await` 在 FastAPI 里意味着什么
- `uvicorn.run(...)` 启动后，底层请求链路是怎么流动的
- FastAPI、Starlette、ASGI、Uvicorn 各自分工是什么

如果你已经能跑通 `00_fastapi_hello_world.py`，这篇文档就是下一步的“机制层理解”。

## 一、整体关系图

先建立一个总图，再往下拆细节：

```text
浏览器 / curl / requests
        |
        v
      HTTP 请求
        |
        v
      Uvicorn
  (ASGI Server，负责监听端口、收发请求)
        |
        v
      ASGI 调用协议
        |
        v
     FastAPI 应用对象
        |
        v
     Starlette 路由与请求分发
        |
        v
   你的 Python 路由函数
        |
        v
    返回 dict / JSON / Response
        |
        v
   FastAPI / Starlette 组装 HTTP 响应
        |
        v
      Uvicorn 发回客户端
```

一句话概括：

- `Uvicorn` 负责“跑服务”
- `ASGI` 负责“定义调用协议”
- `Starlette` 负责“底层 Web 框架能力”
- `FastAPI` 负责“在 Starlette 之上提供类型驱动的 API 开发体验”

## 二、基础运行机制

这一部分把 `ASGI`、`Starlette`、`FastAPI(...)` 放在一起理解。

### 1. ASGI 到底是什么

ASGI 全称是：

```text
Asynchronous Server Gateway Interface
```

更标准、也更容易记住的一句话是：

> ASGI 是 Python 异步 Web 应用与服务器之间的标准调用接口。

它解决的问题主要是：

- Web 服务器怎么调用 Python 应用
- Python 应用怎么把响应结果交还给服务器
- 异步请求、流式响应、WebSocket 怎么统一抽象

所以 ASGI 不是框架，也不是服务器，而是一套约定。

#### 为什么会有 ASGI

在 ASGI 之前，Python Web 领域常见的是 WSGI。

- `WSGI`
  - 单次请求 -> 单次响应
  - 同步模型
  - 更适合传统短请求 Web 应用

- `ASGI`
  - 双向异步事件模型
  - 一个连接里可以多次 `receive`
  - 也可以多次 `send`
  - 适合 WebSocket、流式响应、分块传输、长连接、高并发异步 I/O

所以它和 WSGI 最大的区别，不只是“支持 async”，而是：

> ASGI 把一次 HTTP/WebSocket 交互抽象成了可持续收发的事件流，而不是一次性函数调用。

#### ASGI 应用长什么样

从协议角度看，一个 ASGI 应用本质上接收 3 个东西：

- `scope`
- `receive`
- `send`

可以粗略理解成：

- `scope`
  - 这次连接/请求的静态上下文
  - 比如路径、方法、请求头、协议类型
- `receive`
  - 从客户端继续接收数据
- `send`
  - 把响应或事件发回服务器

最底层的 ASGI 应用更接近：

```python
async def app(scope, receive, send):
    ...
```

在这份 hello world 代码里你看不到 `scope / receive / send`，原因是：

- FastAPI 把底层协议细节封装掉了
- Starlette 负责大部分底层适配
- Uvicorn 按 ASGI 协议去调用这个应用

更准确地说：

```text
你写的是 FastAPI 路由函数
FastAPI / Starlette 把它们组织成 ASGI 应用
Uvicorn 再按 ASGI 协议去执行
```

### 2. Starlette 在 FastAPI 里扮演什么角色

FastAPI 并不是从零重写整个 Web 框架，它的大量底层能力来自 Starlette。

Starlette 负责的是更底层、更通用的 Web 能力，例如：

- 路由分发
- Request / Response 对象
- 中间件
- 生命周期管理
- 静态文件和 WebSocket 支持

FastAPI 在这些基础能力上，再叠加：

- Pydantic 数据校验
- 类型驱动的参数解析
- OpenAPI schema 自动生成
- Swagger / ReDoc 文档

所以从设计分工看：

```text
Starlette = 底层 Web 基础设施
FastAPI = 面向 API 开发体验的增强层
```

#### 为什么 FastAPI 要建立在 Starlette 之上

这样设计有几个直接好处：

1. 避免重复实现底层 Web 能力
2. 可以直接复用成熟的 ASGI 生态
3. FastAPI 可以把精力集中在“API 开发体验”上

也就是说，FastAPI 的创新重点是把：

- Python 类型标注
- 数据校验
- 文档生成

这些能力更自然地嫁接到 Web 开发里。

#### 一个 Starlette 原生极简示例

如果把 FastAPI 的增强层拿掉，只看 Starlette 原生写法，一个最小例子会更接近这样：

```python
from starlette.applications import Starlette
from starlette.responses import JSONResponse
from starlette.routing import Route


async def homepage(request):
    return JSONResponse({"message": "Hello from Starlette"})


async def hello(request):
    name = request.path_params["name"]
    return JSONResponse({"message": f"Hello, {name}!"})


app = Starlette(
    debug=True,
    routes=[
        Route("/", homepage),
        Route("/hello/{name}", hello),
    ],
)
```

这个例子有助于看清 FastAPI 和 Starlette 的边界：

- Starlette 原生写法里：
  - 需要显式写 `Route(...)`
  - 路由函数通常接收 `request`
  - 路径参数要自己从 `request.path_params` 里取
  - 响应通常显式写成 `JSONResponse(...)`

- FastAPI 写法里：
  - 用 `@app.get(...)` 这类装饰器注册路由
  - 函数参数可以直接声明成 `name: str`
  - 框架会自动做参数解析
  - 返回 dict 时会自动转成 JSON 响应

### 3. `app = FastAPI(...)` 背后做了什么

代码里这一行：

```python
app = FastAPI(title="FastAPI Hello World Demo", version="0.1.0")
```

看起来很简单，但它背后做的事情不只是“创建对象”。

#### 它创建的是一个 ASGI 应用

FastAPI 应用对象本质上是一个可被 ASGI Server 调用的应用。

所以 `app` 的角色是一个“能够接收请求、返回响应”的可调用对象。

从运行时角度看，Uvicorn 不关心你写的是 FastAPI 还是别的 ASGI 框架，它只关心：

- 这里有没有一个符合 ASGI 协议的应用对象

#### 它会保存应用元数据

像：

```python
FastAPI(title="...", version="...")
```

这些参数会进入应用元数据，后续用于：

- 自动生成 OpenAPI schema
- Swagger UI 展示
- ReDoc 展示

所以这些值会参与 API 文档系统的生成。

## 三、路由与参数

这一部分围绕：

- `@app.get(...)`
- 路径参数
- 类型标注
- 参数分类

解释 FastAPI 是怎么把 Python 函数声明成接口的。

### 1. `@app.get(...)` 为什么能把函数注册成接口

代码里最核心的语法是：

```python
@app.get("/hello")
async def hello():
    return {"message": "Hello, World!"}
```

这里的关键在装饰器。

装饰器本质上是：

```python
hello = app.get("/hello")(hello)
```

也就是：

1. 先调用 `app.get("/hello")`
2. 它返回一个“包装函数”
3. 再把 `hello` 这个函数传进去
4. 最终完成注册

所以 `@app.get(...)` 对应的是一次真实的注册逻辑。

FastAPI / Starlette 会把下面这些信息放进路由表：

- HTTP 方法：`GET`
- 路径：`/hello`
- 对应处理函数：`hello`
- 参数信息
- 返回类型信息
- 依赖注入信息（如果有）

所以路由注册的本质是：

```text
把 “路径 + 方法 + 处理函数” 记录到应用内部的路由系统里
```

后续请求到来时，再去路由表里查该调哪个函数。

### 2. 为什么路径参数能自动映射到函数参数

这段代码很典型：

```python
@app.get("/hello/{name}")
async def hello_name(name: str):
    return {"message": f"Hello, {name}!"}
```

这里的 `{name}` 是一个占位符，表示一段动态路径片段。

例如访问：

```text
/hello/song
```

时，路由系统会把：

- `song`

提取出来，绑定给参数 `name`。

FastAPI 的一个核心设计点是：直接读 Python 函数签名。

也就是说，它会分析：

```python
async def hello_name(name: str):
```

从这里提取：

- 参数名：`name`
- 参数类型：`str`

再和路由里的 `{name}` 对应起来。

### 3. 类型标注为什么重要

`name: str` 不只是给编辑器看，它会参与：

- 请求参数解析
- 基础类型转换
- 参数校验
- OpenAPI 文档生成

所以在 FastAPI 里，Python 类型标注会直接参与运行时接口定义。

### 4. FastAPI 里的参数一共可以分成 6 大类

最常见的 6 大类是：

1. `Path`
   - 路径参数
   - 例如：`/users/{user_id}`
2. `Query`
   - 查询参数
   - 例如：`/items?page=2`
3. `Body`
   - 请求体参数
   - 常见于 JSON 请求
4. `Header`
   - 请求头参数
5. `Cookie`
   - Cookie 参数
6. `Form` / `File`
   - 表单或文件参数

可以先记成一句：

```text
Path / Query / Body / Header / Cookie / Form(File)
```

### 5. FastAPI 为什么能“自动猜参数类型”

FastAPI 有一套默认推断规则，所以很多时候你不显式写 `Path(...)`、`Query(...)`、`Body(...)` 也能工作。

最常见的推断逻辑是：

- 如果参数名出现在路由路径里，例如 `{name}`
  - 就按 `Path` 处理
- 如果参数是简单标量类型，且不在路径里
  - 通常按 `Query` 处理
- 如果参数是 Pydantic 模型、`dict`、`list` 这类复杂对象
  - 通常按 `Body` 处理

所以在当前 hello world 例子里：

```python
@app.get("/hello/{name}")
async def hello_name(name: str):
```

之所以能自动识别，是因为：

- `name` 出现在 `/hello/{name}`
- `name` 又出现在函数参数里
- FastAPI 就把它认定成了路径参数

### 6. 显式写法是什么样

在更完整的接口里，你也可以显式声明参数来源，例如：

```python
from fastapi import Path, Query, Body, Header, Cookie, Form, File, UploadFile


@app.post("/users/{user_id}")
async def demo(
    user_id: int = Path(...),
    page: int = Query(1),
    payload: dict = Body(...),
    authorization: str | None = Header(None),
    session_id: str | None = Cookie(None),
    note: str | None = Form(None),
    avatar: UploadFile | None = File(None),
):
    ...
```

FastAPI 的优势之一就在于：

- 简单场景下可以自动推断，写法简洁
- 复杂场景下也能显式声明，语义清楚

## 四、返回值与响应

这一部分围绕“为什么返回 dict 会自动变 JSON”展开。

### 1. 先记住最终结论

当你只写：

```python
@app.get("/")
def index():
    return {"code": 200, "msg": "ok"}
```

框架实际上在背后做了 4 件事：

1. 把 Python 对象变成可 JSON 化的数据结构
2. 序列化成 JSON 字符串 / 字节流
3. 构造标准 HTTP 响应对象
4. 再按 ASGI 协议把响应事件发给 Uvicorn

所以链路是：

```text
Python 对象
-> JSON 可序列化结构
-> HTTP 响应
-> ASGI 事件
-> Uvicorn 发回客户端
```

### 2. 路由函数返回的是“Python 对象”

你的函数本身不知道 HTTP，它只是返回：

- dict
- list
- Pydantic model
- Response 对象

### 3. 数据层：先把 Python 对象变成可 JSON 结构

如果返回的是普通 `dict` / `list`，框架会先做可 JSON 化处理，例如：

- 清洗嵌套结构
- 处理 Python 特有类型
- 把一些不能直接进 JSON 的对象转成兼容表示

常见会被处理的类型包括：

- `datetime`
- `UUID`
- `Enum`
- `set`
- `Pydantic` 模型

如果你返回的是 Pydantic 模型，例如：

```python
return Item(name="苹果", price=9.9)
```

框架会先把它导出成标准数据结构，再进入 JSON 响应流程。

### 4. 序列化层：再转成 JSON 字符串 / 字节

概念上可以近似理解成：

```python
import json

json_str = json.dumps(python_obj, ensure_ascii=False)
body = json_str.encode("utf-8")
```

HTTP 真正发送出去的是字节，不是 Python dict。

### 5. 响应层：构造标准 HTTP 响应对象

概念上可以近似理解成：

```python
from starlette.responses import JSONResponse

return JSONResponse(
    content=python_dict,
    media_type="application/json",
)
```

这一步会统一处理：

- 状态码
- 响应体
- 响应头
- `Content-Type: application/json`

### 6. 协议层：最后按 ASGI 事件发出去

再往下一层，就到了 ASGI 协议本身。

最终会组装成两类事件：

1. `http.response.start`
   - 包含状态码和响应头
2. `http.response.body`
   - 包含真正的 JSON 字节流

然后交给 Uvicorn 写回客户端。

### 7. 如果你写原生 ASGI，这些都得自己做

如果不使用 FastAPI / Starlette，而是自己写原生 ASGI 应用，这些步骤都得手工完成：

```python
import json


async def app(scope, receive, send):
    data = {"code": 200, "msg": "ok"}

    body = json.dumps(data, ensure_ascii=False).encode("utf-8")

    await send(
        {
            "type": "http.response.start",
            "status": 200,
            "headers": [
                [b"content-type", b"application/json"],
            ],
        }
    )

    await send(
        {
            "type": "http.response.body",
            "body": body,
        }
    )
```

这样对比就能看清 FastAPI / Starlette 省掉了什么：

- JSON 序列化
- 响应对象封装
- HTTP 头设置
- ASGI 响应事件拼装

### 8. FastAPI 为什么能自动处理这么多返回类型

FastAPI 会根据你 `return` 的对象类型决定后续包装策略。

常见情况包括：

- `dict` / `list`
  - 自动转 JSON
- Pydantic 模型
  - 先序列化，再转 JSON
- `str`
  - 可作为普通文本响应
- `bytes`
  - 可作为二进制响应
- `Response` 对象
  - 直接按你给的响应对象原样返回

所以它不是只支持 dict，而是有一层“返回值类型分发机制”。

## 五、协程与服务启动

这一部分把 `async def`、`await`、`__main__` 和 `uvicorn.run(...)` 放在一起理解。

### 1. `async def` 在这里到底意味着什么

协程可以先理解成：

> 用户态的轻量级线程，用单线程实现并发。

它的特点是：

- 切换成本很低
- 主要适合 I/O 密集场景
- 遇到等待时可以主动让出执行权
- 一个线程里可以调度很多个协程

所以在 FastAPI 语境里，`async def` 的意义主要不是“更高级的函数写法”，而是把路由函数放进异步调度模型里。

#### `async def` 定义的是协程函数

这意味着它返回的是一个可被事件循环调度的协程对象。

最小例子可以理解成：

```python
import asyncio


async def hello():
    print("开始")
    await asyncio.sleep(1)
    print("结束")
```

这里：

- `async def`
  - 定义协程函数
- `await`
  - 表示“我在这里等待，同时把执行权让出去”

#### `await` 的本质是什么

`await` 最核心的含义是：

> 当前协程在等待某个异步操作完成，同时把执行权交回事件循环，让别的协程先运行。

所以协程能并发的关键，不是“同时开很多线程”，而是：

- 某个任务遇到 I/O 等待
- 它主动让出执行权
- 事件循环去调度别的任务

#### 为什么协程在 I/O 场景下特别有优势

协程的优势主要来自：

- 网络请求
- 数据库查询
- Redis
- 文件 I/O
- 消息队列

也就是“等待很多、CPU 计算不重”的场景。

#### FastAPI 里最需要记住的协程规则

1. `async def` 定义协程函数
2. `await` 只能出现在 `async def` 里面
3. 协程内部尽量调用异步 I/O 库
4. 不要在异步路由里随手塞阻塞代码，例如：
   - `time.sleep(...)`
   - 同步 `requests`
   - 纯阻塞数据库驱动

否则虽然代码表面写成了 `async def`，但实际仍然可能把整个异步服务卡住。

### 2. `if __name__ == "__main__"` 为什么常见

这段代码：

```python
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
```

让同一个文件既能：

- 被导入
- 也能直接运行

例如：

- `python 00_fastapi_hello_world.py`
  - 会进入这个分支
- `import 00_fastapi_hello_world`
  - 不会进入这个分支

### 3. `uvicorn.run(...)` 到底做了什么

Uvicorn 是一个 ASGI Server。

它的职责集中在：

- 打开 socket
- 监听端口
- 接收 HTTP 请求
- 按 ASGI 协议调用你的应用对象
- 把应用返回结果再写回给客户端

可以把它理解成：

```text
Python Web 服务真正对外接流量的那一层服务器进程
```

更具体一点，`uvicorn.run(...)` 启动后会经历这些步骤：

1. 读取启动参数
2. 创建服务器配置对象
3. 打开 socket 并监听端口
4. 启动事件循环
5. 接收客户端连接
6. 把请求转换成 ASGI 事件
7. 调用 FastAPI 应用
8. 收集响应并写回客户端

可以压缩理解成：

```text
Uvicorn = 监听端口 + 接收请求 + 转成 ASGI 调用 + 把响应写回去
```

#### 为什么 FastAPI 需要 Uvicorn

FastAPI 只是一个应用对象，不会自己监听端口。

它更关心的是：

- 请求来了之后该怎么处理

真正负责把它跑成网络服务的，是 Uvicorn 这样的 ASGI Server。

#### `host="0.0.0.0"` 和 `port=8000` 是什么

- `host="0.0.0.0"`
  - 监听所有网络接口
- `host="127.0.0.1"`
  - 只允许本机访问
- `port=8000`
  - 监听 TCP 8000 端口

#### 直接运行 Python 文件 vs `uvicorn module:app`

方式一：直接运行脚本

```bash
python 00_fastapi_hello_world.py
```

触发的是文件里的：

```python
if __name__ == "__main__":
    uvicorn.run(app, ...)
```

方式二：用 uvicorn 命令加载模块

```bash
uvicorn 00_fastapi_hello_world:app --host 0.0.0.0 --port 8000
```

这里：

- `00_fastapi_hello_world`
  - 模块名
- `app`
  - 模块里的应用对象名

这种方式更接近真实项目常用启动姿势，也更容易配合：

- `--reload`
- 多 worker
- 容器启动命令
- 进程管理器

#### `--reload` 背后做了什么

在开发环境里你经常会看到：

```bash
uvicorn 00_fastapi_hello_world:app --reload
```

它的作用是：

- 监控代码文件变化
- 代码变化后自动重启服务进程

这不是 FastAPI 自动完成的，而是 Uvicorn 提供的开发便利能力。

## 六、一次请求的完整流动 + 为什么这样设计

### 1. 从一次请求的角度看完整链路

假设你访问：

```text
http://localhost:8000/hello/song
```

一次请求大致会这样流动：

```text
浏览器发出 HTTP 请求
-> Uvicorn 收到请求
-> Uvicorn 按 ASGI 协议调用 FastAPI 应用
-> Starlette 路由系统匹配到 /hello/{name}
-> 提取路径参数 name = "song"
-> FastAPI 根据函数签名调用 hello_name(name="song")
-> 你的函数返回 {"message": "Hello, song!"}
-> FastAPI/Starlette 把 dict 序列化成 JSON Response
-> Uvicorn 把 HTTP 响应发回浏览器
```

这个链路一旦理解了，你后面再看：

- 请求体解析
- Pydantic 模型校验
- `StreamingResponse`
- 中间件
- WebSocket

都会更顺。

### 2. FastAPI 为什么这样设计

FastAPI 的设计有几个非常明显的取向：

1. 用 Python 函数签名做接口声明
2. 用类型标注驱动运行时行为
3. 底层能力复用 Starlette，避免重复造轮子
4. 建立在 ASGI 之上，天然支持异步

所以它的重点不在“重写整个 Web 世界”，而在：

- 用已有成熟底层能力
- 提供更强的 API 开发体验

### 3. 和后续 AI 服务 demo 的关系

`00_fastapi_hello_world.py` 可以看作后面所有服务化 demo 的最小前置知识。

只要你理解了这份文件：

- 应用对象
- 路由注册
- 参数映射
- JSON 响应
- 协程调度
- Uvicorn 启动

你就已经掌握了后面这些示例最底层的共同骨架：

- [01_ollama_fastapi_server.py](/Users/songxijun/workspace/otherProject/ai-training/11_fastapi_serving/01_ollama_fastapi_server.py)
- [02_mock_llm_fastapi_server.py](/Users/songxijun/workspace/otherProject/ai-training/11_fastapi_serving/02_mock_llm_fastapi_server.py)
- 多模态 FastAPI 服务
- LangGraph 子代理服务

后面那些复杂例子，本质上都是在这个骨架上再加：

- 请求体模型
- 流式响应
- 代理转发
- 多模态输入
- 中间件和依赖

## 七、一句话总结

`00_fastapi_hello_world.py` 表面上只是几个接口，但背后已经把 FastAPI 的核心主线都露出来了：

- FastAPI 是建立在 Starlette 上的 ASGI 应用框架
- 路由函数是被装饰器注册进路由系统的 Python 函数
- 类型标注会参与参数解析、校验和文档生成
- 返回 dict 会被框架序列化成 HTTP JSON 响应
- Uvicorn 才是真正监听端口并驱动整个请求生命周期的 ASGI Server

把这些理解透，再往后学服务化、流式输出和 AI 接口封装，就会轻松很多。
