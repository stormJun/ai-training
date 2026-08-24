# OpenSandbox 技术方案与开源产品对比

> 调研日期：2026-08-24
> OpenSandbox 核验基线：`opensandbox-group/OpenSandbox` `main` 分支提交 [`efe2535`](https://github.com/opensandbox-group/OpenSandbox/commit/efe2535549811ed6a7881768d6f7af79f741f447)。原地址 [`alibaba/OpenSandbox`](https://github.com/alibaba/OpenSandbox) 当前重定向到 `opensandbox-group/OpenSandbox`；本文全部源码引用使用迁移后的仓库和固定提交。
> 证据范围：OpenSandbox、E2B、Microsandbox、Daytona、Kubernetes SIG Agent Sandbox、gVisor、Firecracker、Kata Containers、nsjail 的官方文档和官方 GitHub 仓库，以及阿里云官方产品文档。除“判断/建议”外，关键结论均就地引用一手来源。
> 术语约定：本文的“OpenSandbox”指 Apache-2.0 开源项目，不自动等同于阿里云 PAI-Sandbox、ACS Agent Sandbox、FC Cloud Sandbox 或 ACK 安全沙箱。

## 一句话结论

**OpenSandbox 是一套面向 AI Agent 的通用、自托管沙箱平台和协议实现：上层提供多语言 SDK、CLI、MCP 和生命周期/执行 API，中层提供 FastAPI 控制面、`execd` 数据面、Ingress/Egress，底层把工作负载落到 Docker 或 Kubernetes，并可选接入 gVisor、Kata Containers 或 Kata + Firecracker。** 它与 E2B 属于大体同层的分布式平台；Microsandbox 是近同层但本地优先的嵌入式 microVM 沙箱；`kubernetes-sigs/agent-sandbox` 更接近 Kubernetes 工作负载控制器；gVisor、Kata、Firecracker、nsjail 则是底层隔离构件，不能与完整平台直接等同。[OpenSandbox 官方定位与组件](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L6-L25)

选型上的核心判断是：

- **优先 OpenSandbox**：希望保留 Apache-2.0、自托管、Docker/Kubernetes 双后端、Java/Go/Python/JS/C# 多语言接入，以及可替换底层安全运行时的能力。
- **优先 E2B**：接受更重的 Terraform + Nomad/Consul/PostgreSQL/Redis/ClickHouse/对象存储栈，换取从模板内存快照恢复、Firecracker 默认强隔离和更完整的团队/配额控制面。[E2B 官方架构](https://github.com/e2b-dev/infra/blob/110fa5be8dec14c1171045a3a68fd6fdf207bcd4/docs/ARCHITECTURE.md#L1-L68)
- **优先 Kubernetes Agent Sandbox**：只需要 Kubernetes 原生 `Sandbox`/`SandboxClaim`/`SandboxWarmPool` CRD，希望自己组合执行 API、入口和安全运行时；它本身不实现强隔离，而是依赖 gVisor/Kata 等 `RuntimeClass`。[官方威胁模型](https://github.com/kubernetes-sigs/agent-sandbox/blob/2fd412d55ecae90861a101a5424a75473de97c36/docs/security/threat_model.md)
- **优先 Microsandbox**：希望在开发机、CI 或单机 Agent worker 内以子进程方式嵌入 microVM，不运行常驻 daemon/集群控制面；它当前仍明确标为 beta，云能力是 private beta，不适合直接承诺集群级 SLA。[Microsandbox 官方 README](https://github.com/superradcompany/microsandbox/blob/7456552e3df86edecbc172ab85193a3d65c20a63/README.md)
- **不再把 Daytona 当作持续维护的开源首选**：Daytona 官方已于 2026-06-11 宣布生产代码闭源，旧 AGPL 仓库继续公开但不再维护；它只能作为历史实现、社区分叉基线或托管竞品评估。[Daytona 官方公告](https://www.daytona.io/dotfiles/updates/daytona-is-going-closed-source)

对当前仓库，建议先部署一个独立的 **JDK 17 `sandbox-gateway`**，由它使用 OpenSandbox JVM SDK，现有 Java 8 / Spring Boot 2.2.5 应用只调用内部 REST；备选是 Java 8 直接按 OpenAPI 调生命周期 API 和 `execd` API。当前项目基线见 [`pom.xml`](../pom.xml#L7-L10) 和 [`java.version`](../pom.xml#L49-L51)，OpenSandbox 贡献文档要求 JVM SDK 开发环境为 JDK 17+，但当前主产物又配置了 JVM 8 toolchain，所以“Java 8 必然不能运行 SDK”并不是已证实事实；若要直接引 SDK，必须先做字节码、依赖树、OkHttp/SLF4J 与 Java 8 集成测试。[OpenSandbox SDK 开发要求](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/CONTRIBUTING.md#L232-L253)；[主产物 toolchain 配置](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/sdks/sandbox/kotlin/build.gradle.kts#L103-L117)

## 事实、判断与未知的标记

- **事实**：官方文档、固定提交源码或官方产品文档直接陈述/实现的能力。
- **判断**：基于事实做的工程选型或风险推断，不是上游承诺。
- **未知**：截至核验基线没有找到足够的一手证据，不应写入采购承诺或 SLO。

## 先澄清“阿里云 OpenSandbox”

### OpenSandbox 开源项目

OpenSandbox 当前上游在 `opensandbox-group/OpenSandbox`，采用 Apache-2.0，仓库仍保留 Alibaba 命名的 JVM/npm 包坐标，并发布到 Docker Hub、GitHub Container Registry 和阿里云容器镜像服务。它的 README 将自己定义为“general-purpose sandbox platform”，支持 Docker/Kubernetes、自托管 SDK/API/CLI/MCP，并没有把自己定义成某个阿里云托管产品的开源版。[当前官方仓库与许可](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/README.md#L1-L82)

**判断**：对方案、成本和 SLA 评估时，应把 OpenSandbox 当作需要团队自行部署和运维的开源基础设施，而不是默认带阿里云 SLA、控制台、计费、合规认证和 15,000 实例/分钟承诺的云服务。

### 容易混淆的阿里云托管能力

| 名称 | 官方定位 | 与 OpenSandbox 的关系 |
| --- | --- | --- |
| [PAI-Sandbox](https://www.alibabacloud.com/help/en/pai/sandbox-overview) | PAI 提供的托管 MicroVM 沙箱，面向代码、文件和浏览器自动化 | 独立云产品；不能把其 MicroVM、启动速度或 SLA外推到开源 OpenSandbox |
| [ACS Agent Sandbox](https://www.alibabacloud.com/help/en/cs/user-guide/agent-sandbox/) | ACS 上的生产级 Agent 沙箱服务，官方文档宣称 MicroVM、休眠/唤醒、checkpoint/clone 和 15,000 沙箱/分钟 | 独立云服务且截至文档为 public preview；不是 OpenSandbox 开源版的性能证明 |
| [FC Cloud Sandbox](https://www.alibabacloud.com/help/en/functioncompute/agenrun-sandbox-upgrade-announcement) | Function Compute 推出的托管沙箱，官方公告强调接近 E2B SDK 兼容 | 独立托管服务；与 OpenSandbox API/部署模型不同 |
| [ACK 安全沙箱 runV](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/overview-10) | ACK 的轻量 VM 容器运行时，以 `RuntimeClass` 在 Pod 级提供独立 Guest Kernel | 是潜在底层运行时；OpenSandbox 官方指南只列 gVisor/Kata/Firecracker，runV 组合必须 PoC，不能宣称官方已支持 |

## OpenSandbox 的技术定位和边界

### 它提供什么

1. **统一客户端面**：Python、JavaScript/TypeScript、Java/Kotlin、C#、Go SDK，另有 `osb` CLI 和 MCP server；通用能力包括创建、查询、暂停、恢复、续期、删除、端点解析、命令流式执行、文件操作和资源指标。[SDK/CLI/MCP 能力](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L27-L69)
2. **协议面**：`specs/` 中的 OpenAPI 是生命周期、诊断、`execd` 和 egress 策略的公开契约，便于不使用官方 SDK 的客户端直接接入。[协议边界](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L71-L120)
3. **控制面**：Python/FastAPI server 负责认证、校验、生命周期编排、端点格式化、诊断和少量服务端元数据；运行时实现由 Docker 或 Kubernetes service 承担。[控制面职责](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L122-L163)
4. **数据面**：用户镜像中注入 Go `execd`，提供命令、后台任务、持久 shell、PTY、文件、Jupyter code context、CPU/内存指标；可附加 egress sidecar 和 Jupyter/code-interpreter。[数据面职责](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L221-L256)
5. **运行时面**：本机/单机走 Docker；分布式走 Kubernetes，默认 workload provider 是 OpenSandbox 自有 `BatchSandbox`，也能以 `kubernetes-sigs/agent-sandbox` 作为 provider。[运行时后端](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L165-L219)

### 它不直接提供什么

- 不提供模型推理、Agent 规划/记忆/工作流、Prompt 安全判断或业务工具授权；它只承载 Agent 要运行的代码和工具。
- 默认认证是一个 server API key；Kubernetes 可选多租户只把 tenant key 映射到 namespace，并不等于组织、用户、角色、审批、计费和预算系统。[默认 API key 配置](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/server/configuration.md#L61-L74)；[多租户模型和边界](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/multi-tenancy.md#L242-L255)
- 不自动安装 gVisor/Kata/Firecracker，也不默认获得 VM 级隔离；管理员必须先在节点安装运行时并配置 server-wide secure runtime。[安装责任](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/secure-container.md#L45-L85)
- 不负责 Kubernetes/ECS 节点扩容、镜像仓库、对象存储生命周期、云 IAM 或集中审计平台；这些需要部署环境补齐。
- 不提供开源版 SLA、官方容量上限或跨云性能保证。官方仓库中有局部 benchmark 和池机制，但不能代替目标环境压测。

## 核心架构与调用链

```text
Agent / 业务服务
  |
  +-- SDK (Python / JS / JVM / C# / Go)
  +-- osb CLI
  +-- MCP server
  +-- 直接 OpenAPI
          |
          v
OpenSandbox Server (FastAPI control plane)
  |  API key / tenant-key -> namespace
  |  validation / lifecycle / endpoint / diagnostics
  |
  +-- DockerSandboxService -------------------> Docker container
  |
  +-- KubernetesSandboxService
         +-- BatchSandbox provider -----------> BatchSandbox / Pool / Pod
         +-- agent-sandbox provider ----------> Sandbox CR / Pod
                                                     |
                                                     +-- user image / entrypoint
                                                     +-- execd
                                                     +-- optional Jupyter
                                                     +-- optional egress sidecar
                                                     +-- volumes
          |
          +-- direct endpoint / server proxy / K8s ingress gateway
                         |
                         v
                command / file / PTY / code / user service
```

这张图的关键不是组件数量，而是**控制面与数据面分离**：生命周期请求先到 server；命令、文件和代码执行则解析 sandbox 内的 `execd` 端点后直达 `execd` 或走 server/ingress proxy。[官方架构原则与调用链](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L296-L339)

### 创建链路

1. 客户端调用 `POST /v1/sandboxes`，携带镜像/快照来源、entrypoint、环境变量、CPU/内存/GPU、volume、network policy、secure access 等。[生命周期契约](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L75-L93)
2. Server 完成 API key 或 tenant key 认证、参数与运行时配置校验，再委托 Docker/Kubernetes service。
3. Docker 创建容器、端口、volume 和可选 sidecar；Kubernetes provider 合并模板、资源、RuntimeClass、volume、sidecar 和 endpoint 注解。
4. 运行时把 `execd` 和 bootstrap 注入工作负载，当前 Docker 和 Kubernetes provider 都在 create 请求内同步完成 provision，再返回 `Running` 或错误。Server `v0.2.2` 已删除从未真正使用的 `PendingSandbox`/异步 worker，并修正 OpenAPI 的 `202` 说明。[Server v0.2.2 发布说明](https://github.com/opensandbox-group/OpenSandbox/releases/tag/server/v0.2.2)

**文档漂移提醒**：当前架构页仍描述“异步 provision/轮询 readiness”，与 `v0.2.2` 发布说明和当前实现不一致。本文以固定 HEAD 与新版发布语义为准；容量评估时要把长时间拉镜像/调度对 HTTP timeout 和并发连接的占用算进去。[尚未同步的架构页](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L298-L309)

### 执行链路

1. 客户端从 sandbox 元数据或 `GET .../endpoints/{port}` 取得 `execd` 地址及必须的访问 header。
2. 客户端调用 `execd`；命令/代码输出通过 SSE，PTY 通过 WebSocket，普通文件操作使用 HTTP。
3. `execd` 在 sandbox 的进程/文件系统命名空间内执行；如果启用了 access token，需要 `X-EXECD-ACCESS-TOKEN`。[执行接口](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L98-L111)；[执行链路](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L311-L319)

## 能力逐项分析

### 1. 隔离技术和运行时

| 配置 | 实际隔离边界 | 适用性 | 关键注意点 |
| --- | --- | --- | --- |
| 默认 runc | Linux namespace/cgroup/seccomp/capability，仍共享宿主机内核 | 本地开发、可信代码 | OpenSandbox 官方指南明确 runc 是默认；不能称为 VM 级强隔离 |
| gVisor / `runsc` | 用户态 application kernel 截获/实现系统调用 | 希望比 runc 强、启动开销较低，且应用系统调用兼容 | 系统调用兼容不完整；OpenSandbox egress sidecar 需要 `nat` 表，与 gVisor netstack 当前不兼容 |
| Kata + QEMU/CLH | 每 Pod 轻量 VM 和独立 Guest Kernel | 多租户不可信代码、兼容性优先 | 需要 KVM、RuntimeClass、Guest image/kernel 和更多内存；运维更重 |
| Kata + Firecracker | Kata 负责 OCI/CRI 集成，Firecracker 是 VMM | 高密度 MicroVM、希望 Firecracker 但仍留在 Kubernetes/OCI 体系 | OpenSandbox 的 `firecracker` 实际是 Kata + Firecracker，Docker 模式不支持 |

OpenSandbox 的 secure runtime 是**服务端统一配置**，同一 server 的所有 sandbox 透明使用同一个类型；这有利于防止租户自行降级，却意味着混合 gVisor/Kata 需要拆 server/runtime pool 或额外设计。[secure runtime 配置模型](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/secure-container.md#L45-L85)

Docker 侧还默认 `no_new_privileges=true`、PID 上限 4096、可配置 capability drop/AppArmor/seccomp，但 Docker 网络默认值是 `host`；生产环境若要网络隔离和 egress sidecar，应显式使用 `bridge` 或受控自定义网络。[Docker 安全和网络默认值](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/server/configuration.md#L103-L118)

`execd` 还有可选 bubblewrap isolated session，以及 capability/seccomp/Landlock hardening floor。需要特别注意：hardening 默认关闭，当前实现对能力缺失采取 fail-open/degraded 报告，不能把它当成底层 gVisor/Kata 的替代品。[execd hardening 行为](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/components/execd.md#L235-L275)

### 2. 网络与端点

Ingress 有三种主要到达方式：Docker 端口映射/直连、server proxy、Kubernetes ingress gateway。Gateway 支持 header、URI 和 wildcard host 路由，HTTP 和 WebSocket 均可代理；`secureAccess` 当前限 Kubernetes gateway 模式。[端点解析](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L151-L163)；[Ingress 路由](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/components/ingress.md#L28-L80)

Egress 是按 sandbox 可选附加的 sidecar：

- `dns` 模式只做 DNS/FQDN 过滤，不可靠执行 CIDR/IP 规则；`dns+nft` 才加入 nftables。
- Server 只有在 create request 带 `networkPolicy` 时才附加 sidecar；Docker 还强制 bridge 网络。
- IPv6 路径并非完整覆盖，默认 `disable_ipv6=true`。
- gVisor 缺少 sidecar 所需的 iptables `nat` 路径，OpenSandbox 会拒绝 gVisor + `networkPolicy` 组合；应改用 Kata 或 CNI 层 FQDN policy。[egress 配置和限制](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/server/configuration.md#L201-L226)；[gVisor 兼容限制](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/secure-container.md#L722-L752)
- 从预热 Pool 分配时，Pod 已存在，create request 不能再动态注入 per-request egress sidecar；需要在 Pool 模板中预置网络控制。[Pool 网络限制](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/network-isolation.md#L137-L145)

**判断**：对不可信 Agent，“默认允许出网 + 需要调用方主动传 `networkPolicy`”不是足够安全的生产默认。平台层应生成 default-deny 模板、固定拒绝 Pod/Service/metadata CIDR，并禁止业务调用方关闭；否则 prompt injection 仍可把 sandbox 变成内网扫描或数据外传跳板。

### 3. 文件、卷和快照

`execd` 提供文件/目录 API，文件实际存在 sandbox rootfs 或挂载卷中。生命周期 API 抽象三种 volume：

- `host`：只允许 server 配置白名单下的宿主机路径；默认白名单为空，即拒绝所有 host bind。
- `pvc`：Docker 映射为 named volume，Kubernetes 映射为 PVC。
- `ossfs`：通过 OpenSandbox server/runtime 集成挂载阿里云 OSS。[volume 模型](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L248-L256)；[host bind 默认拒绝](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/server/configuration.md#L230-L240)

Docker pause/unpause 保留原容器进程；Docker snapshot 可提交为本地镜像。Kubernetes `BatchSandbox` 的常规 pause 会把 rootfs commit 为 OCI image、释放 Pod/池分配，resume 再重建 Pod；sandbox ID 保持不变，但默认不保留运行进程/内存，且只支持单 replica。[Kubernetes pause/resume 语义](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/pause-resume.md#L24-L80)

暂停提交 Job 会以 UID 0 挂载宿主机 containerd socket，并在源节点运行；这给 committer image 节点级 runtime 权限，必须固定 digest、限制 admission，并纳入供应链审查。推送后的 OCI image 也不会随 CR 自动删除，registry retention/GC 需外部配置。[snapshot committer 风险与回收](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/pause-resume.md#L311-L331)

### 4. 生命周期、预热和扩缩容

- 生命周期：create/list/get/delete、TTL/renew、pause/resume、endpoint；状态包含 reason/message/transition time。
- Docker：管理超时 timer，server 重启后恢复；暂停不释放容器资源。
- Kubernetes：`BatchSandbox` 支持 batch 创建、`Pool` 预热和可选任务编排；Pool 会补充被领取的实例。[Kubernetes controller 能力](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/kubernetes/index.md#L6-L48)
- Python、JVM、Go SDK 另有**实验性客户端池**，池中保存预热 sandbox ID，可用 Redis 共享状态和 leader lock；JS/C# 当前没有该池。领取后没有 `release()`，实例归调用方直到销毁。[客户端池模型与状态](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/client-pool.md#L6-L18)；[池的 acquire 语义](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/client-pool.md#L20-L88)
- Ingress/server proxy 可选“访问时续期”，但它是 best-effort 且默认关闭；Gateway 路径需要 Redis 传 renew intent。[访问续期](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/components/ingress.md#L82-L104)

**判断**：OpenSandbox 已覆盖“实例级生命周期 + warm pool”，但不等于完整容量平台。节点池扩缩容、排队/背压、租户公平调度、成本预算和全局配额仍需 Kubernetes HPA/Cluster Autoscaler/KEDA、云节点池或上层调度器补齐。官方没有给出跨区域/跨集群调度和灾备控制面。

### 5. 可观测性

- Server 状态返回 transition reason/message，提供 DevOps diagnostics 和 request ID。
- `execd` 暴露 CPU/内存指标，可选 OTLP；Ingress/Egress/execd 有组件日志和部分 OpenTelemetry 指标。[官方可观测性边界](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L369-L375)
- Server 的 OTEL 默认关闭，当前直接列出的核心指标是 HTTP request duration 和 SDK 上报的 sandbox create duration；上报不包含请求体和 API key，可由 SDK 禁用。[Server OTEL 配置](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/server/configuration.md#L306-L324)；[SDK telemetry](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/sdk-telemetry.md#L6-L29)

**判断**：要达到生产审计，需要额外汇聚 sandbox/tenant/user/request/command 元数据、Kubernetes audit、Ingress/Egress deny、runtime 异常和节点事件，同时设计敏感命令/输出脱敏。现有两项 server histogram 不能替代安全审计。

### 6. 认证、多租户和凭据安全

默认单租户模式使用一个 `OPEN-SANDBOX-API-KEY`；若不配置 key，server 要求交互确认或显式设置不安全模式环境变量才启动。[认证配置](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/server/configuration.md#L61-L74)

当前 HEAD 已实现 Kubernetes 可选多租户，不应再笼统描述为“只有一个 API key”：file/HTTP tenant provider 把一个或多个 key 映射到预创建 namespace，生命周期 list/get/create/delete 和 proxy 自动按 namespace 路由。限制是 Docker 不支持；server 自己不执行 quota/network policy；Pool API 仍在默认 namespace、不是 tenant scoped；它也没有组织成员、角色权限、审批、计费和预算模型。[多租户要求和认证流](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/multi-tenancy.md#L6-L47)；[隔离边界](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/multi-tenancy.md#L242-L255)

Credential Vault 的设计是把真实 secret 写入 egress sidecar 内存，sandbox 内只放 fake/empty value，HTTPS 请求匹配 host/path/method 后由 MITM sidecar 注入 header。它降低 secret 进入环境变量、命令行、文件和日志的概率，但条件严格：[Credential Vault 工作原理](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/credential-vault.md#L6-L62)

- egress 至少 1.1.1、`mode="dns+nft"`、default-deny，network policy 要允许绑定目标。
- 同一 Pod 不能再有 Istio/Envoy 等透明拦截 sidecar。
- Vault 内容只在 egress 进程内存；Kubernetes pause 删除 Pod 后，resume 的新 sidecar 是空 Vault，可信控制面必须先重注入再放行业务。Docker sidecar 重启/替换也同样丢失。[前提条件](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/credential-vault.md#L10-L37)；[pause/resume 语义](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/credential-vault.md#L68-L96)
- Credential Vault 写 API 的 TLS/loopback 强制默认关闭；如果 sidecar 管理口可能被不可信网络到达，必须开启 `OPENSANDBOX_EGRESS_CREDENTIAL_VAULT_REQUIRE_TLS` 并配置可信代理 CIDR。[Vault transport 配置](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/credential-vault.md#L268-L273)

### 7. 部署方式

| 模式 | 组成 | 适合 | 限制 |
| --- | --- | --- | --- |
| 本地 Docker | `opensandbox-server` + Docker daemon；可用 docker-compose | 开发、API 验证、可信工作负载 | 默认 host network/runc，不适合作为不可信多租户生产默认；Docker 无 tenant namespace 模型 |
| 单机生产 | Server + Docker bridge + secure runtime + egress + 持久卷 | 中小规模、控制成本 | 单机容量/故障域；server store 当前只支持 SQLite，HA 需自行验证 |
| Kubernetes + BatchSandbox | Server Helm + OpenSandbox controller/CRD + 可选 ingress/egress/Redis/registry | 高并发、warm pool、批量/RL、pause/recreate | 组件最多；snapshot、sidecar、RuntimeClass、CNI 和 registry 组合需系统测试 |
| Kubernetes + Agent Sandbox provider | Server + `kubernetes-sigs/agent-sandbox` controller | 已采用 SIG Agent Sandbox CRD 的团队 | OpenSandbox 只是上层 API/execd；provider 能力不一定与 BatchSandbox 完全等价 |

官方把 Docker 和 Kubernetes server backend 都标为 production-ready，并提供 PyPI server、Docker Compose、Helm/CRD 路径；这表示软件路径存在，不等于目标云环境的生产认证。[Server 安装与后端](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/components/server.md#L6-L65)

## 产品分层：不要把平台、控制器和运行时混为一谈

```text
L0  Agent 沙箱平台 / API / 控制面 / 数据面
    OpenSandbox | E2B

L0' 本地嵌入式 sandbox API / microVM runtime
    Microsandbox

L1  Kubernetes 沙箱工作负载控制器
    OpenSandbox BatchSandbox | kubernetes-sigs/agent-sandbox

L2  OCI/CRI 安全容器运行时
    gVisor runsc | Kata Containers

L3  虚拟机监控器 / MicroVM
    Firecracker（也可被 Kata 或 E2B 使用）

L2' 单机进程 jail
    nsjail
```

关系不是单向替代：OpenSandbox 可用 `agent-sandbox` 作为 Kubernetes provider，可用 gVisor/Kata 作为 RuntimeClass；OpenSandbox 的 Firecracker 路径由 Kata 集成；E2B 则直接构建自己的 Firecracker 节点数据面。[OpenSandbox provider/runtime 关系](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md#L185-L219)；[E2B Firecracker 数据面](https://github.com/e2b-dev/infra/blob/110fa5be8dec14c1171045a3a68fd6fdf207bcd4/docs/ARCHITECTURE.md#L1-L68)

## 同层或近同层平台对比

| 维度 | OpenSandbox | E2B | Kubernetes Agent Sandbox | Microsandbox |
| --- | --- | --- | --- | --- |
| 当前开源状态 | Apache-2.0，当前活跃上游 | Infra/SDK Apache-2.0，当前活跃 | Kubernetes SIG Apps，Apache-2.0，当前活跃 | Apache-2.0，当前活跃，README 明确标记 beta |
| 层级 | 完整 sandbox API + 控制/数据面 + runtime adapters | 完整 cloud sandbox 平台 | K8s CRD/controller + warm pool/router/client | 本地嵌入式 sandbox SDK/CLI/MCP + microVM runtime；不是 OSS 集群控制面 |
| 默认隔离 | runc，共享宿主内核；可选 gVisor/Kata/Firecracker | Firecracker microVM，每 sandbox 独立 VM | 默认普通 Pod；强隔离依赖 RuntimeClass | 每 sandbox 独立 microVM/kernel，底层使用 libkrun |
| Runtime/调度 | Docker 或 Kubernetes；BatchSandbox / agent-sandbox provider | 自研 Firecracker orchestrator，Nomad/Consul，GCP，AWS beta | Kubernetes 原生 Pod/CRD | SDK 创建子进程，无常驻 daemon；Linux KVM、macOS Apple Silicon、Windows WHP |
| 启动优化 | K8s Pool + 实验性客户端 pool | 预启动模板的内存/磁盘/VM state snapshot，按需页加载/COW | SandboxWarmPool 预创建 Pod | 官方报告平均启动少于 100ms；需在目标主机/镜像上独立复测 |
| 生命周期/持久化 | TTL/renew、Docker pause、K8s rootfs pause/recreate、PVC/OSSFS | pause/snapshot/resume、auto-pause/resume、object store、volume | stable identity、scheduled delete、pause/resume、PVC、claim/warm pool | named/detached sandbox、volume；快照当前仅本地磁盘，不含内存/进程/网络，不支持可恢复 snapshot |
| 网络/密钥 | endpoint API、server proxy、K8s ingress；可选 egress + Credential Vault | client proxy + node proxy；sandbox 流量不经 control API | Router + K8s NetworkPolicy；无 OpenSandbox 级 egress credential broker | 默认允许公网，阻断 private/link-local/metadata；密钥在宿主侧按目标注入，不进 guest |
| 多租户治理 | 默认单 key；K8s 可选 key->namespace；无内建角色/计费；Pool 非 tenant scoped | team API key/OIDC/admin token、quota、team/template/volume 等控制面 | 委托 Kubernetes namespace/RBAC/Quota | OSS 本地版无组织/RBAC/计费；官网所述组织/SSO/审计是 Cloud private beta，不得外推 |
| SDK | Python、JS/TS、JVM、C#、Go + CLI + MCP | Python、JS/TS + CLI | Go/Python/K8s API | Rust、Python、TypeScript、Go + CLI + MCP；无 Java SDK |
| 自托管复杂度 | 本地低，K8s 中高 | 高：Terraform、Nomad/Consul、Postgres、Redis、ClickHouse、object storage、KVM 节点 | 中：已有 K8s 时较自然，但需自组执行/入口/治理 | 单机低，只需硬件虚拟化；集群调度/治理需自建或等待 Cloud/BYOC |
| 最适合 | 多语言、K8s/Docker、可替换隔离底座、协议优先 | Firecracker 默认强隔离、模板快照启动、可接受重基础设施 | K8s 平台团队只需要标准 CRD primitive | 开发机/CI/单机 Agent worker，需嵌入式 microVM 且不要 daemon |

主要证据：OpenSandbox [架构](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md)、E2B [架构和部署拓扑](https://github.com/e2b-dev/infra/blob/110fa5be8dec14c1171045a3a68fd6fdf207bcd4/docs/ARCHITECTURE.md)、Agent Sandbox [项目架构](https://github.com/kubernetes-sigs/agent-sandbox/tree/2fd412d55ecae90861a101a5424a75473de97c36) 和 [威胁模型](https://github.com/kubernetes-sigs/agent-sandbox/blob/2fd412d55ecae90861a101a5424a75473de97c36/docs/security/threat_model.md)、Microsandbox [固定提交 README](https://github.com/superradcompany/microsandbox/blob/7456552e3df86edecbc172ab85193a3d65c20a63/README.md)、[文件系统安全语义](https://github.com/superradcompany/microsandbox/blob/7456552e3df86edecbc172ab85193a3d65c20a63/docs/security/filesystem.mdx) 和 [官网部署状态](https://agentsandbox.dev/)。

### E2B 的实质差异

E2B 不是“只有 SDK 的云 API”。官方 infra 仓库包含控制面 REST、Firecracker orchestrator、VM 内 `envd`、edge router、template builder 和 Terraform/Nomad 部署。模板是预启动 VM 的 memory + disk + VM state snapshot，create 实际是 restore；Postgres 存团队/模板/构建/快照，Redis 存运行实例和路由，ClickHouse 存指标事件，对象存储放模板/快照。[E2B 架构总览](https://github.com/e2b-dev/infra/blob/110fa5be8dec14c1171045a3a68fd6fdf207bcd4/docs/ARCHITECTURE.md#L1-L68)

因此 E2B 的优势是默认 MicroVM、快照恢复路径和更完整平台治理；代价是基础设施明显重于 OpenSandbox 的 Docker quick start 或普通 Kubernetes 部署。官方自托管以 Terraform 为主，GCP 支持、AWS beta，Azure 和通用 Linux 仍未标为支持。[E2B self-host 支持矩阵](https://github.com/e2b-dev/infra/blob/110fa5be8dec14c1171045a3a68fd6fdf207bcd4/README.md#L1-L21)

### Kubernetes Agent Sandbox 的实质差异

Agent Sandbox 是 Kubernetes SIG Apps 的 stateful singleton Pod 控制器。核心是 `Sandbox` CRD，扩展层提供 `SandboxTemplate`、`SandboxClaim`、`SandboxWarmPool`；warm pool 分配的是预创建 Pod。它不提供 OpenSandbox 的通用 lifecycle/execd/egress/credential-vault 全套，但 OpenSandbox 能把它当成 provider，从而用 OpenSandbox API 补齐上层接口。[官方 quickstart 与 CRD](https://github.com/kubernetes-sigs/agent-sandbox/blob/2fd412d55ecae90861a101a5424a75473de97c36/examples/quickstart/README.md)

安全上，Agent Sandbox 官方明确说项目自身不实现隔离，默认 kind quickstart 也是普通容器；应在模板中配置 gVisor/Kata，并通过 NetworkPolicy/Router 限制跨 sandbox 流量。[官方安全建议](https://github.com/kubernetes-sigs/agent-sandbox/blob/2fd412d55ecae90861a101a5424a75473de97c36/docs/security/threat_model.md)

## 底层隔离构件对比

| 项目 | 所在层 | 隔离机制 | 它提供什么 | 它不提供什么 | 与 OpenSandbox 的关系 |
| --- | --- | --- | --- | --- | --- |
| [gVisor](https://github.com/google/gvisor/tree/3c5eee17dc45659fb86843531074f38e78e0cc35) | OCI runtime / application kernel | Go 用户态内核实现 Linux-like syscall interface；`runsc` 对接 Docker/K8s | 比 runc 更小的宿主内核攻击面，容器工作流兼容 | 没有 Agent sandbox API、池、文件/命令 SDK、计费；也不是传统 VM | OpenSandbox `secure_runtime.type=gvisor`；但当前不能与其 egress sidecar 同用 |
| [Kata Containers](https://github.com/kata-containers/kata-containers/tree/7739b6262fccf27fcc7afd4fa39de5b4fb0b53a0) | OCI/CRI VM runtime | 每 Pod 一个轻量 VM/Guest Kernel，containerd shim + guest `kata-agent` | Kubernetes/OCI 透明 VM 隔离，支持 QEMU、Cloud Hypervisor、Firecracker、Dragonball | 没有 OpenSandbox 上层 lifecycle/execd/SDK/tenant API | OpenSandbox 最自然的 K8s 强隔离底座；`kata` 和 `firecracker` 路径都经过 Kata |
| [Firecracker](https://github.com/firecracker-microvm/firecracker/tree/81b38b9dad6056d7a48073e95ac5a9aed51cb2ab) | VMM / microVM | KVM + 极简设备模型；Rust VMM，建议配合 jailer/cgroup/namespace/seccomp | MicroVM 创建/运行、API、snapshot primitives、较小攻击面 | 不管理容器镜像、Agent API、K8s 调度、tenant/网络/volume 生命周期；snapshot 文件也需调用方保护和管理 | OpenSandbox 通过 Kata+Firecracker；E2B 直接构建 Firecracker orchestration |
| [nsjail](https://github.com/google/nsjail/tree/5ebcc30bef4af60d6e28f012dd8bf7b99b8b0acf) | 单机进程 jail | Linux namespaces、cgroups、rlimits、seccomp-bpf/Kafel | 轻量地限制一个进程/网络服务，适合编译器、评测器、单机工具 | 共享宿主内核；没有分布式调度、镜像/模板、SDK、生命周期控制面 | 可作为定制本地执行器的构件，不是 OpenSandbox 平台替代品 |

gVisor 官方明确说明它既不是简单 syscall filter，也不是日常意义的 VM；`runsc` 是 OCI runtime。[gVisor 官方定位](https://github.com/google/gvisor/blob/3c5eee17dc45659fb86843531074f38e78e0cc35/README.md) Kata 则把 Kubernetes Pod 映射为 VM，链路为 `Kubelet -> CRI -> Kata OCI runtime -> VM -> containers`。[Kata virtualization](https://github.com/kata-containers/kata-containers/blob/7739b6262fccf27fcc7afd4fa39de5b4fb0b53a0/docs/design/virtualization.md) Firecracker 官方也明确总体安全依赖正确配置的 Linux host，并建议使用 jailer；它不是买来即得的完整多租户平台。[Firecracker 设计与威胁隔离](https://github.com/firecracker-microvm/firecracker/blob/81b38b9dad6056d7a48073e95ac5a9aed51cb2ab/docs/design.md)

## 选型矩阵

| 需求 | 首选 | 次选/组合 | 原因 |
| --- | --- | --- | --- |
| 本机快速验证 sandbox API | OpenSandbox + Docker bridge | nsjail 自建最小执行器 | OpenSandbox 几条命令即有 lifecycle/command/file；nsjail 只适合极简专用场景 |
| Kubernetes 上自建通用 Agent sandbox 平台 | OpenSandbox + BatchSandbox + Kata | OpenSandbox + Agent Sandbox provider | 前者功能闭环更完整；后者适合已有 SIG CRD 资产的团队 |
| 默认 MicroVM、模板恢复极快 | E2B self-host / managed | OpenSandbox + Kata/Firecracker + Pool | E2B 的架构从一开始围绕 Firecracker snapshot restore；OpenSandbox 组合更灵活但要自行调优 |
| Java/Go/.NET 多语言统一 SDK | OpenSandbox | 直接 OpenAPI | OpenSandbox 官方 SDK 覆盖最广 |
| 只需 Kubernetes 原生 stateful sandbox CRD | Kubernetes Agent Sandbox | OpenSandbox provider 集成 | 无需先引入完整平台；强隔离仍需 gVisor/Kata |
| 强 syscall 兼容和独立 Guest Kernel | Kata/QEMU 作为 OpenSandbox runtime | ACK runV PoC | Kata 是 OpenSandbox 官方文档路径；runV 需验证集成兼容性 |
| 低开销隔离且应用兼容 gVisor | OpenSandbox + gVisor | 直接 Agent Sandbox + gVisor | 不能同时依赖 OpenSandbox egress sidecar，网络控制必须改走 CNI 层 |
| 单进程编译/评测、单机、无平台需求 | nsjail | gVisor `runsc` | nsjail 简单；多租户 hostile code 更建议独立 kernel 边界 |
| 已有 Daytona OSS 部署 | 固定旧版本并评估社区 fork/迁移 | 迁移 OpenSandbox/E2B | 官方不再维护旧 AGPL server，新增生产依赖风险不可接受 |
| 希望少运维且优先阿里云托管 | PAI/ACS/FC Sandbox 单独评估 | OpenSandbox 自建 | 这是 buy vs build 决策，不能用开源仓库能力表代替云产品规格和报价 |

## OpenSandbox 的优缺点

### 优点

1. Apache-2.0，协议、控制面、执行 daemon、K8s controller、Ingress/Egress、SDK 都在一个可审查仓库中。
2. Docker/Kubernetes 两条路径，既能低门槛本地验证，也能使用 CRD/Pool 做分布式部署。
3. Runtime-neutral API，把 runc/gVisor/Kata/Firecracker 的选择留给平台团队。
4. SDK 覆盖 Python、JS、JVM、C#、Go，另有 CLI/MCP；适合异构业务系统。
5. command/file/code interpreter/browser/desktop/RL 示例覆盖较广，便于建立统一 sandbox service。
6. Egress、Credential Vault、secure endpoint、tenant namespace、OTEL 等生产构件已经出现，不只是一个 `docker exec` wrapper。

### 缺点和风险

1. 默认是 runc + Docker host network，强隔离和网络默认拒绝都需要管理员主动配置。
2. 功能组合存在明确冲突：gVisor vs egress、Pool vs per-request network policy、service mesh vs Credential Vault。
3. Kubernetes 常规 pause 是 rootfs commit/recreate，不等价于 E2B/Daytona VM memory pause；Credential Vault 在 resume 后必须重注入。
4. 多租户仅到 tenant key -> namespace，Pool 仍共享；组织 RBAC、审批、预算、计费、完整 audit 要自建。
5. Server-managed store 当前只有 SQLite；多副本控制面、数据库迁移、灾备和一致性没有开箱即用答案。[store 配置](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/server/configuration.md#L244-L260)
6. 客户端 pool 仍标 experimental；官方没有目标环境可直接采用的 SLA、容量和延迟基线。
7. Snapshot committer 拥有节点级 containerd 权限，增加供应链和节点逃逸攻击面。
8. `execd` 的可选 hardening floor 默认关闭且 fail-open；必须把 RuntimeClass/CNI/节点加固作为主要隔离边界。

## 当前项目的落地建议

### 推荐目标架构

```text
zl-data-business (Java 8 / Spring Boot 2.2.5)
        |
        | internal REST + business auth / idempotency
        v
sandbox-gateway (JDK 17, independent deploy)
        | OpenSandbox JVM SDK / OpenAPI
        | tenant mapping / policy template / audit / quota / retry
        v
OpenSandbox Server (Kubernetes runtime)
        |
        +-- BatchSandbox Controller + Pool
        +-- Ingress Gateway
        +-- Egress dns+nft + Credential Vault
        +-- OTEL / logs
        v
Dedicated ACK sandbox node pool
        +-- first choice: officially documented Kata RuntimeClass
        +-- candidate: ACK runV RuntimeClass after PoC only
        +-- PVC / OSSFS / registry snapshots as required
```

这样做的主要原因不是“Java 8 一定不能运行 SDK”，而是把高变化的 sandbox SDK、SSE/WebSocket、生命周期补偿、凭据重注入和安全策略从旧业务进程中隔离。Gateway 也能统一实施业务身份到 tenant key/namespace 的映射，避免把 OpenSandbox API key 发到多个应用。

### 接入路径

1. **推荐：独立 JDK 17 gateway**
   使用官方 JVM SDK；对内暴露业务化 API，例如 `createJobSandbox`、`runCommand`、`writeInput`、`collectArtifact`、`destroy`。Gateway 负责 request ID、幂等键、超时、失败清理、审计、租户策略、续期和 resume 后 Vault 重注入。
2. **轻量备选：Java 8 直连 OpenAPI**
   生命周期和 `execd` 都有 OpenAPI，可以生成兼容 Java 8 的 client，命令 SSE 与 PTY WebSocket 单独实现。优点是没有新服务，缺点是安全和补偿逻辑容易散落在现有业务模块。
3. **有条件评估：主应用直接引官方 JVM SDK**
   当前 SDK 主产物配置 JVM 8 toolchain，但开发/测试要求 JDK 17。只有在 Maven 依赖树、classfile version、OkHttp/Kotlin/SLF4J 冲突、Java 8 真实运行和 Spring Boot 2.2 回归全部通过后才采用；不要只凭 Maven 能解析依赖就上线。

### ACK 上的 PoC 必测项

1. `RuntimeClass`：先用 OpenSandbox 官方文档覆盖的 Kata 跑通；runV 只做候选，验证 server startup validation、Pod 调度、`execd` 注入和 endpoint。
2. `execd`：background 模式与 `execd as init` 都测；再启用 hardening floor，确认 Agent CLI、编译器、PTY、Jupyter 所需 syscall/capability。
3. 网络：验证 egress sidecar 的 `NET_ADMIN`、iptables/nftables、DNS、Terway/CNI、IPv6 禁用、metadata/Pod/Service CIDR 拒绝、Ingress WebSocket/SSE。
4. Pool：把 egress sidecar/default-deny 固化到 Pool template，验证 warm allocate 后策略没有丢失；不要依赖 per-request `networkPolicy` 动态注入。
5. Credential Vault：验证 fake credential、MITM CA、host/path/method scope；pause/resume 后必须先重注入并做 readiness gate，故障时 fail closed。
6. 存储：验证 PVC、OSSFS 的 UID/GID、吞吐、一致性、回收、租户隔离；不要默认把 OSS inline credential 视为 Vault 已保护。
7. Pause/resume：验证 rootfs、PVC、环境变量、进程/内存、Vault、endpoint 和旧连接分别发生什么；验证 snapshot registry GC。
8. Snapshot committer：确认 ACK 节点 containerd socket、admission、安全沙箱节点限制与 runV/Kata 兼容；固定 image digest。
9. 容量：对目标镜像做 cold/warm P50/P95/P99、并发创建/删除、镜像 pull storm、API 429/503、节点扩缩容和故障注入。
10. 治理：tenant key 轮换、namespace quota、Pool 跨租户风险、审计字段、敏感输出脱敏、API key 和 Vault 管理口网络边界。

阿里云 ACK 官方说明 runV 是轻量 VM `RuntimeClass`，支持独立 Guest Kernel，并列出了网络/存储/监控优势与版本/节点池限制；但 OpenSandbox 当前 `secure_runtime` 文档没有列 runV。因此可行性是合理推断，不是官方兼容声明。[ACK runV 官方文档](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/overview-10)；[OpenSandbox 支持列表](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/secure-container.md#L45-L57)

### 分阶段落地

**阶段 0：本地功能验证（1 台开发机）**

- Docker bridge，不使用 host network。
- 固定 OpenSandbox server/execd/egress 镜像 digest。
- 验证 Java gateway 的 create -> write -> run -> collect -> kill 闭环。
- 只运行无敏感数据的测试任务。

**阶段 1：ACK 安全 PoC（独立 namespace/node pool）**

- Kata RuntimeClass、default-deny egress、Ingress secure access、API key、ResourceQuota/LimitRange。
- 禁止 hostPath；只开放测试 PVC/OSS 路径。
- 对 prompt injection、内网扫描、fork bomb、磁盘写满、进程泄漏、断线和超时做红队测试。

**阶段 2：小流量生产**

- 按租户 namespace 和 tenant key，业务身份/角色仍由 gateway 管理。
- 建 warm pool，但将网络策略固化到模板。
- OTEL、K8s audit、Ingress/Egress/runtime 日志集中化；定义自动清理和泄漏巡检。
- 在确认 pause/resume 补偿前，优先 destroy + recreate，而不是依赖有状态恢复。

**阶段 3：规模化**

- 引入 Redis 分布式 client pool 或按目标负载使用 BatchSandbox Pool。
- 对 node autoscaling、registry/cache、失败域、配额公平性和成本做容量模型。
- 若 OpenSandbox 的治理/HA补齐成本高于托管服务，再用同一 workload 和 SLO 对比 ACS/PAI/FC Sandbox 或 E2B managed，而不是只比 API 名称。

## 明确的未知项和采用前问题

1. **未知：OpenSandbox 开源版与各阿里云托管 Sandbox 的代码/控制面复用关系。** 官方资料没有给出可依赖的版本映射，不能用云产品指标替代 OSS 压测。
2. **未知：目标 ACK 版本和 runV 与 OpenSandbox 的组合兼容性。** 需验证 `RuntimeClass`、init/sidecar、`NET_ADMIN`、snapshot committer、PVC/OSSFS。
3. **未知：本项目真实 sandbox 工作负载。** 代码解释器、浏览器、Claude/Codex CLI、数据处理和 RL 对镜像、网络、CPU、内存、GPU、会话时长的需求不同。
4. **未知：多副本 OpenSandbox server 的正式 HA 拓扑。** 当前服务端持久 store 只有 SQLite；需要确认可否把控制面做成无状态多副本、snapshot 元数据如何共享和恢复。
5. **未知：安全认证与外部审计结果。** Apache-2.0 和 secure-runtime 支持不等于通过企业所需的 SOC 2、等保、渗透测试或供应链审查。
6. **未知：端到端性能。** 官方组件文档中的局部启动/池 benchmark 不能代表本项目镜像、ACK CNI/CSI、镜像仓库和峰值并发。
7. **未知：Java 8 直接引 JVM SDK 的完整兼容性。** 主产物 toolchain 是 8，但开发基线为 17，仍需对发布 artifact 和依赖做实测。
8. **未知：成本优势。** 自建时节点空闲、warm pool、镜像/快照存储、网络、运维人力和安全事件响应都要计入，不能只按 Pod CPU/内存计价。

## 最终建议

在“必须自托管、保持开源、需要 JVM/Go 等多语言、计划运行在 ACK/Kubernetes”这组条件下，**OpenSandbox 是当前最值得进入 PoC 的上层平台，建议默认组合为 OpenSandbox + BatchSandbox + Kata + default-deny egress + 独立 sandbox-gateway**。这不是直接上线建议：默认 runc/host network、组合兼容限制、轻量多租户治理、SQLite store 和 pause/Vault 语义都要求平台团队补齐。

E2B 是最有价值的同层对照组，尤其适合把“默认 Firecracker + snapshot restore + 完整团队控制面”放在第一优先级的团队，但自托管栈更重。Kubernetes Agent Sandbox 是很好的下层 CRD primitive，也可以成为 OpenSandbox provider；它不应被宣传为独立完整平台。gVisor、Kata、Firecracker、nsjail 应按隔离层选型，不应出现在与 OpenSandbox/E2B 同一行的“产品胜负”结论中。Daytona 因官方停止维护旧开源 server，不应成为新的开源生产基座。

## 主要一手来源

### OpenSandbox

- [当前官方仓库固定提交 `efe2535`](https://github.com/opensandbox-group/OpenSandbox/tree/efe2535549811ed6a7881768d6f7af79f741f447)
- [总体架构](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/index.md)
- [Server 配置](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/server/configuration.md)
- [Kubernetes controller](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/kubernetes/index.md)
- [Secure runtime](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/secure-container.md)
- [Network isolation](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/architecture/network-isolation.md)
- [Pause/resume](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/pause-resume.md)
- [Credential Vault](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/credential-vault.md)
- [Multi-tenancy](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/multi-tenancy.md)
- [Client pool](https://github.com/opensandbox-group/OpenSandbox/blob/efe2535549811ed6a7881768d6f7af79f741f447/docs/guides/client-pool.md)

### 同层平台与 Kubernetes 控制器

- [E2B infra 固定提交](https://github.com/e2b-dev/infra/tree/110fa5be8dec14c1171045a3a68fd6fdf207bcd4)
- [E2B 架构](https://github.com/e2b-dev/infra/blob/110fa5be8dec14c1171045a3a68fd6fdf207bcd4/docs/ARCHITECTURE.md)
- [E2B self-host](https://github.com/e2b-dev/infra/blob/110fa5be8dec14c1171045a3a68fd6fdf207bcd4/self-host.md)
- [Kubernetes SIG Agent Sandbox 固定提交](https://github.com/kubernetes-sigs/agent-sandbox/tree/2fd412d55ecae90861a101a5424a75473de97c36)
- [Agent Sandbox threat model](https://github.com/kubernetes-sigs/agent-sandbox/blob/2fd412d55ecae90861a101a5424a75473de97c36/docs/security/threat_model.md)
- [Daytona 官方闭源公告](https://www.daytona.io/dotfiles/updates/daytona-is-going-closed-source)
- [Daytona 当前产品文档](https://www.daytona.io/docs/sandboxes)

### 底层运行时

- [gVisor 固定提交](https://github.com/google/gvisor/tree/3c5eee17dc45659fb86843531074f38e78e0cc35)
- [Firecracker 固定提交](https://github.com/firecracker-microvm/firecracker/tree/81b38b9dad6056d7a48073e95ac5a9aed51cb2ab)
- [Firecracker snapshot security](https://github.com/firecracker-microvm/firecracker/blob/81b38b9dad6056d7a48073e95ac5a9aed51cb2ab/docs/snapshotting/snapshot-support.md)
- [Kata Containers 固定提交](https://github.com/kata-containers/kata-containers/tree/7739b6262fccf27fcc7afd4fa39de5b4fb0b53a0)
- [Kata virtualization architecture](https://github.com/kata-containers/kata-containers/blob/7739b6262fccf27fcc7afd4fa39de5b4fb0b53a0/docs/design/virtualization.md)
- [nsjail 固定提交](https://github.com/google/nsjail/tree/5ebcc30bef4af60d6e28f012dd8bf7b99b8b0acf)

### 阿里云产品边界

- [ACK 安全沙箱 runV](https://help.aliyun.com/zh/ack/ack-managed-and-ack-dedicated/user-guide/overview-10)
- [PAI-Sandbox](https://www.alibabacloud.com/help/en/pai/sandbox-overview)
- [ACS Agent Sandbox](https://www.alibabacloud.com/help/en/cs/user-guide/agent-sandbox/)
- [FC Cloud Sandbox 升级公告](https://www.alibabacloud.com/help/en/functioncompute/agenrun-sandbox-upgrade-announcement)
