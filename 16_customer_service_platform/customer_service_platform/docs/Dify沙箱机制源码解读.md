# Dify 沙箱机制源码解读（基于 `dify-sandbox-main`，含 RAGFlow 对比）

## 1. 一句话结论（面试可直接说）

Dify 的代码节点不是在 API/Worker 进程内直接执行，而是通过 HTTP 调用独立的 `dify-sandbox` 服务执行。`dify-sandbox` 本体是 **Go + Gin** 服务，内部通过 `chroot + seccomp + setuid/setgid + no_new_privs` 对 Python/Node 进程做隔离与约束。

---

## 1.1 为什么需要沙箱（先讲价值）

在 Dify 里，用户/工作流代码（Python/JS）可能包含危险操作。沙箱机制就是把这段代码放进“受限环境”，核心目标是：

1. 隔离宿主系统：避免直接读写主机敏感文件、逃逸到宿主进程。  
2. 限权执行：通过 `setuid/setgid`、`no_new_privs` 降低进程权限。  
3. 系统调用白名单：用 `seccomp` 只允许必要 syscall。  
4. 资源与并发控制：限制并发数、请求数、超时，防止卡死和滥用。  
5. 可控网络访问：可按配置关闭网络或经代理出网，降低 SSRF/横向风险。  

---

## 1.2 Dify 如何“隔离宿主系统”（分层视角）

可以按 5 层来理解：

1. 架构隔离层（进程边界）  
- API/Worker 不直接执行用户代码，而是调用独立 `dify-sandbox` 服务。  
- 这样代码执行故障不会直接污染业务主进程。  

2. 文件系统隔离层（chroot）  
- 执行前在子进程里做 `chroot`，把可见根目录限制在沙箱根内。  
- Node 路径还会把必需文件复制到临时根目录后执行。  

3. 权限隔离层（降权）  
- 执行前启用 `no_new_privs`，随后 `setuid/setgid` 到低权限 sandbox 用户。  
- 防止通过提权路径拿到宿主高权限。  

4. 系统调用隔离层（seccomp）  
- 默认 `ActKillProcess`，仅放行白名单 syscall。  
- 网络 syscall 需 `enable_network=true` 才会追加放行。  

5. 资源与流量隔离层（限流/超时）  
- `MaxRequest`、`MaxWorker` 控制请求数和并发执行数。  
- 子进程超时会被 kill，避免卡死和资源耗尽。  

---

## 1.3 五层机制的源码速查（面试可直接指文件）

1. 架构隔离层  
- Dify 调用沙箱：`api/core/helper/code_executor/code_executor.py`  
- 沙箱路由入口：`internal/controller/router.go`、`internal/controller/run.go`

2. 文件系统隔离层  
- `chroot` 实现：`internal/core/lib/python/add_seccomp.go`、`internal/core/lib/nodejs/add_seccomp.go`  
- Node 临时根目录：`internal/core/runner/temp_dir.go`、`internal/core/runner/nodejs/nodejs.go`

3. 权限隔离层  
- `no_new_privs`：`internal/core/lib/set_no_new_privs.go`  
- `setuid/setgid`：`internal/core/lib/python/add_seccomp.go`、`internal/core/lib/nodejs/add_seccomp.go`  
- sandbox 用户初始化：`internal/core/runner/init.go`

4. syscall 隔离层  
- seccomp 主逻辑：`internal/core/lib/seccomp.go`  
- Python 白名单：`internal/static/python_syscall/syscalls_amd64.go`  
- Node 白名单：`internal/static/nodejs_syscall/syscalls_amd64.go`

5. 资源与流量隔离层  
- 请求并发限制：`internal/middleware/cocrrent.go`  
- 子进程超时终止：`internal/core/runner/output_capture.go`

---

## 2. 这次看的源码范围

### 2.1 Dify 主仓（调用方）

- `api/core/helper/code_executor/code_executor.py`
- `api/core/workflow/nodes/code/code_node.py`
- `docker/docker-compose.dify.yaml`

### 2.2 Sandbox 仓（执行方）

- `dify_others/dify-sandbox-main/cmd/server/main.go`
- `internal/server/server.go`
- `internal/controller/*`
- `internal/middleware/*`
- `internal/service/*`
- `internal/core/runner/python/*`
- `internal/core/runner/nodejs/*`
- `internal/core/lib/*`
- `internal/static/*`

---

## 3. 服务启动与路由

### 3.1 启动入口

- 入口：`cmd/server/main.go` -> `server.Run()`
- `server.Run()` 主要做三件事：
  1. `initConfig()` 读配置并加载依赖清单
  2. `go initDependencies()` 异步安装 Python 依赖并准备依赖环境
  3. `initServer()` 启动 Gin HTTP 服务

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/server/server.go`

### 3.2 路由与鉴权

- 公共接口：`GET /health`
- 私有接口前缀：`/v1/sandbox/*`
- 私有接口统一 `X-Api-Key` 校验（`middleware.Auth()`）

`/v1/sandbox` 下主要接口：
1. `POST /run`：执行代码
2. `GET /dependencies`：查依赖
3. `POST /dependencies/update`：更新依赖环境
4. `GET /dependencies/refresh`：刷新依赖状态

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/controller/router.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/middleware/auth.go`

---

## 4. 请求执行主链路（从 Dify 到 Sandbox）

### 4.1 Dify 侧发起调用

Dify API 侧 `CodeExecutor` 发送请求到：

`POST {CODE_EXECUTION_ENDPOINT}/v1/sandbox/run`

请求头：
- `X-Api-Key: CODE_EXECUTION_API_KEY`

请求体关键字段：
- `language`（python3 / nodejs）
- `code`
- `preload`
- `enable_network`

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/api/core/helper/code_executor/code_executor.py`

### 4.2 Sandbox 侧接收并分发

`RunSandboxController` 根据 `language` 分流：
- `python3` -> `service.RunPython3Code`
- `nodejs` -> `service.RunNodeJsCode`

请求中的 `enable_network` 会被传给 runner options。

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/controller/run.go`

### 4.3 返回码语义（容易踩坑）

`dify-sandbox` 的业务错误很多是 **HTTP 200 + 业务码非 0**，而不是直接 HTTP 4xx/5xx：

1. 参数绑定失败：`BindRequest` 返回 HTTP 200，`code=-400`。  
2. 运行时错误：通常返回 HTTP 200，`code=-500`，错误放在 `message` 或 `data.error`。  
3. 不支持语言：返回 HTTP 400。  
4. 鉴权失败（`X-Api-Key` 不匹配）：返回 HTTP 401。  
5. 请求数超限（`MaxRequest`）：返回 HTTP 503。  

这也是 Dify API 侧会继续解析 JSON 里 `code/message/data` 的原因。

---

## 5. Python 执行器（源码细节）

### 5.1 执行前准备

`PythonRunner.InitializeEnvironment()` 做了这些事：

1. 读取并模板化 `prescript.py`（嵌入文件）。
2. 注入 UID/GID、`enable_network`、`preload`。
3. 生成 64 字节随机 key（512bit）。
4. 对用户代码做 XOR 加密，再 Base64 编码塞进脚本。
5. 生成临时脚本：`/var/sandbox/sandbox-python/tmp/<uuid>.py`。

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/runner/python/python.go`

### 5.2 子进程启动

执行命令大致是：

`python_path <tmp_script> <LIB_PATH> <encoded_key>`

并且：
- `cmd.Env` 先清空，再按配置注入代理环境变量。
- 若配置了 `AllowedSyscalls`，会注入 `ALLOWED_SYSCALLS=...`。

### 5.3 prescript.py 做了什么

`prescript.py` 核心步骤：
1. 加载 `python.so`（Go 编译出的 c-shared 库）。
2. 切到运行目录（`LIB_PATH`）。
3. 可选执行 preload 代码。
4. 调 `DifySeccomp(uid,gid,enable_network)` 启用隔离。
5. 解密并 `exec` 用户代码。

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/runner/python/prescript.py`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/cmd/lib/python/main.go`

---

## 6. NodeJS 执行器（源码细节）

### 6.1 临时根目录与文件复制

`NodeJsRunner.Run()` 会：
1. 基于 `WithTempDir("/", REQUIRED_FS, ...)` 创建临时根目录。
2. 把必需目录/文件复制进临时根（node 项目、证书、hosts、resolv 等）。
3. 在临时根中写入脚本并执行，结束后清理临时目录。

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/runner/nodejs/nodejs.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/runner/temp_dir.go`

### 6.2 代码注入方式

Node 路径是把用户代码 `base64` 后拼接成：

`eval(Buffer.from(...).toString('utf-8'))`

再接到 `prescript.js` 后面执行。

`prescript.js` 会先调用 `DifySeccomp(...)` 再执行后续代码。

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/runner/nodejs/prescript.js`

补充：当前实现里，Python runner 会按配置注入 `HTTP_PROXY/HTTPS_PROXY`，但 Node runner 默认没有注入代理环境变量（仅处理 `ALLOWED_SYSCALLS`），这在“Node 代码必须经代理出网”的场景需要单独评估或改造。

---

## 7. 真正的隔离机制（重点）

`DifySeccomp` 最终进入 `InitSeccomp`（Python/Node 各一套，但流程类似）：

1. `syscall.Chroot(".")`
- 把当前进程根目录切到当前工作目录。

2. `syscall.Chdir("/")`
- 切到 chroot 后的新根。

3. `SetNoNewPrivs()`
- 禁止进程通过 exec 获得额外权限。

4. `Seccomp(allowlist, errno_list)`
- 默认策略是 `ActKillProcess`。
- 白名单 syscall 允许执行。
- 某些 syscall 用 `ActErrno`（报错而非直接 kill）。
- `enable_network=true` 时会追加网络相关 syscall 白名单。

5. `setuid/setgid`
- 降权到 sandbox 用户（默认 UID 65537）。

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/lib/python/add_seccomp.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/lib/nodejs/add_seccomp.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/lib/seccomp.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/static/python_syscall/syscalls_amd64.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/static/nodejs_syscall/syscalls_amd64.go`

---

## 8. 资源控制与错误行为

### 8.1 并发与请求上限

`/run` 接口挂了两层中间件：

1. `MaxRequest(max_requests)`：超限返回 `503`。
2. `MaxWorker(max_workers)`：信号量限流并发执行数。

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/middleware/cocrrent.go`

### 8.2 超时与进程终止

`OutputCaptureRunner` 通过定时器超时 kill 子进程，并向 stderr 写入：

`error: timeout`

若退出信息包含 `bad system call`，会映射成：

`error: operation not permitted`

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/runner/output_capture.go`

### 8.3 preload 的真实行为

即使调用方传了 `preload`，若配置 `EnablePreload=false` 会被清空，不执行 preload。

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/service/python.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/service/nodejs.go`

### 8.4 攻击尝试在测试里的实际结果

从 `tests/integration_tests` 可以看到一些“恶意操作 -> 被拦截”的行为：

1. Python `os.execl` / `subprocess.run`  
- 预期结果：stderr 包含 `operation not permitted`。  
- 参考：`python_malicious_test.go`。

2. Python 读取 `/etc/passwd`  
- 预期结果：`No such file or directory`（chroot 后看不到宿主路径）。  
- 参考：`python_malicious_test.go`。

3. NodeJS `child_process.spawn`  
- 预期结果：stderr 包含 `operation not permitted`。  
- 参考：`nodejs_malicious_test.go`。

4. NodeJS 函数重定义注入场景  
- 预期结果：不会触发预期外命令执行，输出 `result: undefined`。  
- 参考：`nodejs_malicious_test.go`。

---

## 9. 依赖环境管理机制

### 9.1 启动时依赖处理

`initDependencies()` 会异步：
1. 根据 `dependencies/python-requirements.txt` 执行 `pip3 install`。
2. 执行 `PreparePythonDependenciesEnv()`，把 python 运行所需路径映射到沙箱目录。
3. 按 `python_deps_update_interval`（默认 30m）定时刷新。

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/server/server.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/static/config.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/runner/python/setup.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/core/runner/python/env.sh`

### 9.2 为什么很多包会报 so 缺失

因为 chroot 后只看得到沙箱根里的文件；如果没把对应 `python_lib_path` 复制/硬链接进来，就会出现 `xxx.so cannot open shared object file`。

---

## 10. 配置优先级与关键参数

配置来源：`conf/config.yaml` + 环境变量覆盖。

常用参数：
1. `API_KEY`
2. `SANDBOX_PORT`
3. `WORKER_TIMEOUT`
4. `MAX_WORKERS`
5. `MAX_REQUESTS`
6. `ENABLE_NETWORK`
7. `ENABLE_PRELOAD`
8. `ALLOWED_SYSCALLS`
9. `PYTHON_PATH`
10. `PYTHON_LIB_PATH`
11. `HTTP_PROXY/HTTPS_PROXY/SOCKS5_PROXY`

关键文件：
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/internal/static/config.go`
- `/Users/songxijun/workspace/otherProject/dify-1.9.2/dify_others/dify-sandbox-main/conf/config.yaml`

---

## 11. 和你当前 Dify 部署配置怎么对上

在 `dify-1.9.2/docker/docker-compose.dify.yaml`：

1. API/Worker 用 `CODE_EXECUTION_ENDPOINT=http://sandbox:8194` 调用 sandbox。
2. 双方通过 `CODE_EXECUTION_API_KEY` / `SANDBOX_API_KEY` 对齐。
3. sandbox 默认带 `HTTP_PROXY/HTTPS_PROXY` 指向 `ssrf_proxy`。
4. `ssrf_proxy_network` 是 internal 网络，用于减少直接外网暴露面。

---

## 12. 与 RAGFlow 的沙箱机制对比（你给的 `ragflow-main`）

### 12.1 架构形态

1. Dify
- 单一 `dify-sandbox` 服务负责代码执行。
- API 通过 HTTP `/v1/sandbox/run` 调用。

2. RAGFlow
- 通过 `sandbox-executor-manager` 管理执行器池。
- 有 `SANDBOX_MAX_MEMORY`、`SANDBOX_TIMEOUT`、`SANDBOX_ENABLE_SECCOMP` 等参数。
- `system_settings.json` 里还能切 provider（`self_managed/e2b/aliyun`）。

### 12.2 重点差异

- Dify：执行链更聚焦“工作流代码节点”。
- RAGFlow：更强调“执行器池 + provider 扩展能力”。

### 12.3 能力边界（避免过度承诺）

1. 这是容器/进程级隔离，不是虚拟机级隔离。  
2. 安全效果高度依赖 syscall 白名单、网络策略、镜像基线与宿主内核。  
3. 若放宽 `ENABLE_NETWORK`、`ALLOWED_SYSCALLS` 或 preload 策略，风险会明显上升。  
4. 生产环境仍需叠加主机侧防护（容器权限、网络隔离、审计与告警）。

---

## 13. 生产落地注意事项（基于源码）

1. 默认把 `ENABLE_PRELOAD=false` 保持关闭。  
2. 非必要不要开启 `ENABLE_NETWORK=true`；若必须开启，配合代理与域名白名单。  
3. `ALLOWED_SYSCALLS` 不要随意放开，否则 seccomp 保护会显著削弱。  
4. 根据并发量调 `MAX_WORKERS/MAX_REQUESTS`，并配合 API 侧连接池与超时。  
5. 依赖库复杂时，先补齐 `PYTHON_LIB_PATH`，再做压测。  

---

## 14. 面试速记版

“Dify 的沙箱是独立 Go 服务，不在 API 进程内执行不可信代码。请求进来后按语言分流到 Python/Node 执行器；执行前会在子进程里调用 `DifySeccomp` 做 `chroot + no_new_privs + seccomp + setuid/setgid`。并发由 `MaxWorker/MaxRequest` 控制，超时会 kill 进程。网络与 preload 都有开关，默认 preload 建议关闭。和 RAGFlow 比，Dify 更像单沙箱服务，RAGFlow 更像执行器管理层。”
