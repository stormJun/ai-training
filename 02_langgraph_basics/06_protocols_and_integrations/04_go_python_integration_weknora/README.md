# Go ↔ Python 服务对接方式(以 WeKnora 为案例)

> 案例源码:`~/workspace/otherProject/WeKnora`(分支 `main`)
> 学习目标:看一个真实项目里 **Go 主应用如何按场景选择不同机制调用 Python 服务**,把"通信协议 × 生命周期 × 信任边界"三条轴串起来。

WeKnora 是一个 Go 写的 RAG 后端,但把重型文档解析、agent 技能脚本、MCP 工具生态、模型 rerank 分别交给 Python 完成。它**没有**用一套通用桥梁把所有 Python 逻辑塞进去,而是按每种任务的**调用频率、负载大小、信任边界**分别选了 4 种不同的对接方式。这是这个案例最值得学的地方。

---

## 全景对比

| # | 场景 | 对接方式 | 生命周期 | 数据面 | 传输 | 信任边界 | 关键源码 |
|---|---|---|---|---|---|---|---|
| 1 | 文档解析 (docreader) | **gRPC**(共享 proto 生成双端桩) | 常驻服务 | 二进制 + 流式 | HTTP/2,内网 `:50051` | 内部服务,TLS+Token 可选 | `docreader/main.py`、`internal/infrastructure/docparser/grpc_parser.go` |
| 2 | Agent 技能脚本 (sandbox) | **子进程 exec / `docker run`** | 一次性 | stdin/stdout/exit code | 进程管道 | 强隔离(容器 or 白名单) | `internal/sandbox/local.go`、`internal/sandbox/docker.go` |
| 3 | MCP 工具生态 | **MCP-over-HTTP (SSE / Streamable HTTP)** | 常驻,双向 | JSON-RPC | HTTPS | 支持 OAuth / API Key,Stdio 传输被禁用 | `internal/mcp/client.go`、`mcp-server/` |
| 4 | Rerank 重排序 | **REST HTTP (Jina 兼容)** | 常驻 | JSON | HTTPS | 外部/自托管均可 | `internal/models/rerank/jina_reranker.go`、`rerank_server_demo.py` |

选型的思考路径:

```
调用一次几秒 + 每天成千上万次 + 二进制 payload 大  →  gRPC(方式 1)
用户上传的不可信脚本 + 每次都不一样 + 只要一次结果  →  子进程隔离(方式 2)
第三方工具生态 + 已有开放协议 + 需要双向流式响应   →  MCP-over-HTTP(方式 3)
外部 SaaS 兼容 + 可选自托管 + 无状态请求-响应      →  REST(方式 4)
```

---

## 方式 1:gRPC(docreader 文档解析)

**为什么选它**:文档解析是核心热路径,响应时长几百毫秒到几十秒不等,payload 可能是几十 MB 的 PDF、返回可能是几百张图。要保持强类型、支持流式、要能跨机器部署。

### 契约共享

单一真源:`docreader/proto/docreader.proto`

```protobuf
service DocReader {
  rpc Read(ReadRequest) returns (ReadResponse) {}
  rpc ReadStream(ReadRequest) returns (stream ReadStreamResponse) {}
  rpc ListEngines(ListEnginesRequest) returns (ListEnginesResponse) {}
}
```

同一份 proto 用 `protoc` 生成两份桩:
- Go 侧:`docreader/proto/docreader.pb.go` + `docreader_grpc.pb.go`(`go_package` 选项指定生成路径)
- Python 侧:`docreader/proto/docreader_pb2.py` + `docreader_pb2_grpc.py`

Go 侧 import 时把生成物挂在 `github.com/Tencent/WeKnora/docreader/proto` 下,和 Python 项目根**共享同一个 `docreader/` 目录**,proto 文件不重复。

### Python 服务端(docreader/main.py)

```python
server = grpc.server(
    futures.ThreadPoolExecutor(max_workers=CONFIG.grpc_max_workers),
    options=[
        ("grpc.max_send_message_length", CONFIG.grpc_max_file_size_mb),
        ("grpc.max_receive_message_length", CONFIG.grpc_max_file_size_mb),
    ],
    interceptors=[AuthInterceptor()],
)
docreader_pb2_grpc.add_DocReaderServicer_to_server(DocReaderServicer(), server)
health_pb2_grpc.add_HealthServicer_to_server(HealthServicer(), server)  # 标准健康检查
```

要点:
- `AuthInterceptor` 是自研拦截器,校验 metadata 里的 `authorization` token(`docreader/auth.py`)。
- `HealthServicer` 用 gRPC 官方 `grpc.health.v1`,给 compose 的 `grpc_health_probe` 使用。
- `grpc.max_*_message_length` 用环境变量控制,应付大 PDF。

**为大 payload 设计的流式 RPC** —— 这是这个案例最有教学价值的点:

```python
def ReadStream(self, request, context):
    result, source_desc = self._parse_request(request)
    yield ReadStreamResponse(meta=ReadStreamMeta(
        markdown_content=..., image_count=len(images), ...))
    for ref in _iter_image_refs(images):        # 一边 pop 一边 yield
        yield ReadStreamResponse(image=ref)
```

`_iter_image_refs` 边解 base64 边发送边释放源数据(`images.pop(ref_path)`),让 Python 侧**峰值内存**不会同时住着 base64 源和解码后的 bytes。

### Go 客户端(internal/infrastructure/docparser/grpc_parser.go)

关键三点:

1. **DNS resolver + gRPC Dial**
   ```go
   resolver.SetDefaultScheme("dns")
   conn, err := grpc.Dial("dns:///"+addr, opts...)
   ```
   compose 里 `DOCREADER_ADDR=docreader:50051`,让 gRPC client 感知容器 DNS 变化。

2. **优先 stream,失败时降级到 unary**
   ```go
   result, err := p.readStream(ctx, client, protoReq)
   if status.Code(err) == codes.Unimplemented {
       return p.readUnary(ctx, client, protoReq)
   }
   ```
   这是**版本 skew 时的兼容策略**:老版本 docreader 没实现 `ReadStream` 会返回 `Unimplemented`,Go 侧不会中断请求。

3. **`sync.RWMutex` 保护 conn**,支持运行时 `Reconnect(addr)` 切换后端。

### 关键学习点

- gRPC 用于内部服务间高频调用是标准做法,proto 生成双端桩就是主要的**开发工效点**。
- 大 payload 用 **server-streaming** 而不是加大 message-size,单帧越小越好,内存和网络更平稳。
- 一定要留 fallback 分支:`Unimplemented` 是滚动升级里最常见的错误码。
- 双端各自的 health probe / TLS / auth 都是**独立环境变量控制**,fail-fast 而不是静默降级到明文(`docreader/auth.py` 的 `TLSConfigError`)。

---

## 方式 2:子进程隔离(sandbox 执行技能脚本)

**为什么选它**:用户/agent 提交的技能脚本是**不可信输入**,每次执行内容都不同,而且执行完立刻退出。RPC 反而是错的抽象 —— 这里要的是"发起 → 隔离 → 收 stdout"。

### 分层架构(internal/sandbox/)

```
sandbox.go          接口 (Execute / Cleanup / Type / IsAvailable)
├── local.go        LocalSandbox:直接 exec.CommandContext
├── docker.go       DockerSandbox:docker run 到独立容器
├── validator.go    脚本静态黑名单校验
└── manager.go      按配置选后端,支持 fallback
```

`local.go` 的核心几行:

```go
interpreter := s.getInterpreter(config.Script)          // .py → python3
if !s.isAllowedCommand(interpreter) { ... }             // 白名单
execCtx, cancel := context.WithTimeout(ctx, timeout)
cmd := exec.CommandContext(execCtx, interpreter, args...)
cmd.Dir = ...                       // 限工作目录
cmd.Env = s.buildEnvironment(...)   // 环境变量白名单
setupProcessGroup(cmd)              // 便于超时后 kill 整个组
```

`docker.go` 则是 `docker run` 一个预建镜像 `wechatopenai/weknora-sandbox`,该镜像基于 `python:3.11-slim` + node 20,`UID 1000` 非 root 用户跑在 `/workspace`。

### 三层防御

1. **命令白名单**:`defaultAllowedCommands()` 只放行 `python3 / node / bash / cat / grep / ...`。
2. **脚本静态审查**:`validator.go` 一堆正则,拦 `os.system` / `subprocess shell=True` / `pickle.load` / `python.*pty.spawn` / `python.*http.server` 等模式。
3. **进程/容器隔离**:Local 走进程组 + 超时,Docker 走用户命名空间 + 只读挂载。

### 关键学习点

- **信任边界差异决定通信模型**:MCP 那边是可信第三方服务,gRPC 那边是自己写的服务,这里是用户脚本 —— 唯一的合理选项是子进程 + 静态审查 + 容器,而不是让脚本反向连接一个 API。
- 就算是内网自己人,`stdio` 传输也可能被禁 —— 见方式 3 的 MCP 分析。
- 通信协议(stdout)简单可预测,反而适合"任意脚本"这种发散场景。

---

## 方式 3:MCP-over-HTTP(工具生态)

**为什么选它**:MCP 是 Anthropic 主导的开放协议,已有大量第三方 server 实现。Go 主应用要接的是**别人写的**工具服务,而不是自己实现协议,共用生态最重要。

### Go 客户端(internal/mcp/client.go)

用 `github.com/mark3labs/mcp-go` 封装:

```go
switch config.Service.TransportType {
case types.MCPTransportSSE:
    mcpClient, err = client.NewSSEMCPClient(*config.Service.URL, ...)
case types.MCPTransportStreamable:
    mcpClient, err = client.NewStreamableHttpClient(*config.Service.URL, ...)
case types.MCPTransportStdio:
    return nil, fmt.Errorf(
        "stdio transport is disabled for security reasons; " +
        "please use SSE or HTTP Streamable transport instead")
}
```

**Stdio 传输被显式禁用** —— 因为 stdio MCP server 要求本机 spawn 一个进程,存在命令注入面。生产环境强制走 HTTPS。

支持的鉴权策略(`applyAuthHeaders`):
- 静态 API Key(自定义 header,默认 `X-API-Key`)
- Bearer Token
- **OAuth 2.0**(`buildOAuthConfig`),token 按 `(TenantID, Principal, Service.ID)` scope 存 `MCPOAuthRepository`

### Python 服务端(mcp-server/)

- 基于 FastMCP,`main.py` 是入口,`weknora_mcp_server.py` 定义工具。
- 反向调用 Go 主应用的 REST API(`WEKNORA_BASE_URL=http://app:8080/api/v1`),形成**Go→Python(MCP)→Go(REST)**的环。
- compose 里作为独立容器,单独 `expose 8000`,profile 开关 `--profile full`。

### 关键学习点

- 用**开放协议**接生态,比自己造契约成本低得多。工具会越接越多,契约不能随意改。
- 传输方式取决于部署形态:同机开发用 stdio,跨机生产用 HTTP —— **WeKnora 直接砍掉 stdio 分支**,拒绝在生产开这个洞。
- OAuth token 必须按"租户 × 用户 × 服务"scope 存,别偷懒用单例 —— 多租户系统里这是必然踩的坑。

---

## 方式 4:REST(rerank 兼容外部 SaaS)

**为什么选它**:rerank 是可插拔的模型层,用户可能用 Jina SaaS,也可能自托管。选一个**已有 API 规范**(Jina)当契约,让两条路径同一个客户端就能跑。

### Go 客户端(internal/models/rerank/jina_reranker.go)

```go
baseURL := "https://api.jina.ai/v1"     // 默认走 SaaS
if url := config.BaseURL; url != "" {
    baseURL = url                        // 或指到自托管
}
req, err := http.NewRequestWithContext(ctx, "POST",
    fmt.Sprintf("%s/rerank", baseURL), bytes.NewBuffer(jsonData))
```

一份 `net/http` 代码同时打 SaaS 和自建。

### Python 参考实现(rerank_server_demo.py)

FastAPI + transformers + torch,把 HuggingFace 上的 rerank 模型包成 Jina 兼容的 `/rerank` 端点:

```python
class RerankRequest(BaseModel):
    query: str
    documents: List[str]

@app.post("/rerank")
def rerank(req: RerankRequest):
    scores = model.compute(...)         # 本地 transformers 推理
    return {"results": [{"index": i, "score": s} for ...]}
```

demo 只是个"胶水",用户按需自己实现 —— 只要遵守协议就能替换。

### 关键学习点

- 面对"可插拔的第三方模型"这种需求,**复用已有 API 规范**永远比自定义协议更有价值。
- 客户端和服务端的解耦程度取决于契约的稳定性 —— Jina 协议是公开且极简的,契约不会漂移。
- `demo.py` 是提供**参考实现**而不是**生产服务**,项目里保持这个边界很重要,不要让 demo 变成隐式依赖。

---

## 综合的选型 heuristic

如果把 4 种方式压成一个决策树,大致是这样:

```
Python 侧是"服务"还是"脚本"?
├── 脚本(一次性、内容不可信)
│   └── 子进程 + 容器 + 白名单(方式 2)
└── 服务(常驻)
    ├── 数据面是自己控制的、payload 大、需要类型契约
    │   └── gRPC + 共享 proto(方式 1)
    └── 数据面是开放生态或外部 SaaS
        ├── 已有开放协议(MCP、OpenAI/Jina API 等)
        │   ├── 双向、需要工具编排  → MCP-over-HTTP(方式 3)
        │   └── 单向、请求-响应即可 → REST(方式 4)
        └── 无现成协议 → 参考方式 1 自己定 proto
```

三条永远该问的问题:
1. **信任边界在哪?** 决定进程/容器/网络隔离等级。
2. **数据面多大?** 决定要不要 streaming、要不要压缩、要不要绕开消息大小上限。
3. **契约谁维护?** 自己写就用 proto/OpenAPI,别人写就复用他们的协议,用户写就走通用管道(stdout / MCP)。

---

## 延伸阅读

- WeKnora `README_CN.md`、`docker-compose.yml`(整体拓扑)
- gRPC Python 官方文档:<https://grpc.io/docs/languages/python/>
- MCP 规范:<https://modelcontextprotocol.io/specification>
- 本仓库同级参考:
  - `02_langgraph_basics/06_protocols_and_integrations/01_mcp_basics/`
  - `11_fastapi_serving/`(FastAPI 服务化)
  - `12_dockerized_service_apps/`(compose 编排)

---

## 复现建议

WeKnora 是完整的 compose 项目,想跑起来看一下 4 种通道各自的行为:

```bash
cd ~/workspace/otherProject/WeKnora
cp .env.example .env                  # 至少填 LLM key
docker compose up -d docreader app    # 只起 Go app + docreader,验证方式 1
docker compose up -d mcp              # 起 MCP server,验证方式 3
# 方式 2:在 UI 里给 agent 上传一段技能脚本触发
# 方式 4:在设置里把 rerank BaseURL 指向本地 rerank_server_demo.py
```

抓包/看日志时重点关注:
- 方式 1:`docreader` 容器日志里的 `Read(File)` / `ReadStream response`,以及 Go 侧 `Connected to docreader in ...`。
- 方式 2:`internal/sandbox/*` 记录的 stderr,以及 `wechatopenai/weknora-sandbox` 容器的短命周期。
- 方式 3:`mcp` 容器接收的 SSE 事件流。
- 方式 4:`jina_reranker.go` 发出的 POST,body 是标准 `{query, documents}`。
