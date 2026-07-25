# 序列化（Serialization）技术原理

> **摘要**：序列化是将内存中的数据结构转换为字节序列的过程，是持久化存储、网络传输、进程间通信的基础设施。本文从计算机系统底层原理出发，阐述序列化的必要性、实现机制以及在 eino 框架中的应用。

## 目录

- [一、问题背景](#一问题背景)
- [二、存储介质的本质约束](#二存储介质的本质约束)
- [三、进程隔离与虚拟内存](#三进程隔离与虚拟内存)
- [四、序列化的本质](#四序列化的本质)
- [五、eino 框架中的序列化实现](#五eino-框架中的序列化实现)
- [六、深拷贝与序列化的对比](#六深拷贝与序列化的对比)
- [七、总结](#七总结)
- [参考文献](#参考文献)

---

## 一、问题背景

### 1.1 核心问题

在构建分布式系统、持久化存储、进程间通信等场景中，存在一个根本性矛盾：

```
内存中的数据结构（Go struct、Java Object、Python instance）
                    │
                    │ 无法直接存储或传输
                    ▼
存储介质（硬盘/Redis）与传输通道（网络）只接受字节序列
```

### 1.2 三个技术约束

1. **存储介质的底层抽象**：所有持久化存储设备只认字节
2. **进程地址空间隔离**：每个进程有独立的虚拟地址空间，指针不能跨进程
3. **运行时环境依赖**：数据结构的类型信息存在于语言运行时，进程退出即丢失

这三个约束决定了序列化的必要性。

---

## 二、存储介质的本质约束

### 2.1 存储层次结构

根据计算机体系结构[^1]，存储设备呈现层次结构，但底层抽象统一：

| 存储介质 | 物理原理 | 数据表示 | 访问粒度 |
|---------|---------|---------|---------|
| 寄存器 | 触发器 | 电平信号 | 字（Word） |
| 内存（DRAM） | 电容电荷 | 位（Bit） | 字节（Byte） |
| SSD | 浮栅电荷 | 位（Bit） | 页（Page, 4KB） |
| 硬盘（HDD） | 磁极方向 | 位（Bit） | 扇区（Sector, 512B） |
| 网络传输 | 电/光信号 | 位（Bit） | 字节流（Byte Stream） |

**所有存储介质的统一抽象是字节序列**。

### 2.2 为什么不支持"对象"直接存储

假设存储介质支持直接存储 Go struct：

```
问题 1：跨语言兼容性
  - Go 的 struct 布局与 Java 的 Object 布局不同
  - 存储介质需要识别每种语言的内存模型

问题 2：版本兼容性
  - Go 1.20 和 Go 1.21 的 struct 布局可能不同
  - 存储介质需要理解语言版本

问题 3：指针语义
  - struct 内部包含指针，指向其他内存地址
  - 存储介质需要理解进程的地址空间
```

这些问题在存储介质层面无法解决，必须在应用层处理——这就是序列化的职责。

### 2.3 文件系统与数据库的抽象

文件系统和数据库在字节抽象之上提供了结构化接口，但底层仍然存储字节：

```
文件系统：字节序列 ──► 文件（File）
数据库：  字节序列 ──► 行（Row）/ 文档（Document）
Redis：   字节序列 ──► Key-Value
```

这些系统不关心字节的语义，语义由应用层解析。

---

## 三、进程隔离与虚拟内存

### 3.1 虚拟内存机制

现代操作系统实现虚拟内存（Virtual Memory）[^2]，为每个进程提供独立的地址空间：

```
物理内存（Physical Memory）
┌────────────────────────────────────────────────────┐
│ Physical Address │ Content                         │
├──────────────────┼─────────────────────────────────┤
│ 0x0000 - 0x0FFF  │ Process A: Code Segment         │
│ 0x1000 - 0x1FFF  │ Process B: Data Segment         │
│ 0x2000 - 0x2FFF  │ Kernel Space                    │
│ 0x3000 - 0x3FFF  │ Process A: Heap                 │
│ 0x5000 - 0x5FFF  │ Process A: struct instance      │
│ 0x6000 - 0x6FFF  │ Process B: Stack                │
└────────────────────────────────────────────────────┘
```

### 3.2 页表映射

操作系统通过**页表（Page Table）**实现虚拟地址到物理地址的转换：

```
Process A Page Table:           Process B Page Table:
Virtual      Physical           Virtual      Physical
0x1000   ──► 0x3000             0x1000   ──► 0x1000
0x2000   ──► 0x5000             0x2000   ──► 0x6000
         ↑                               ↑
         │                               │
   struct instance                  different memory
```

**关键结论**：同一个虚拟地址（如 `0x2000`）在不同进程映射到不同的物理内存。

#### 补充：为什么需要页表？

**问题：为什么不能直接使用物理地址？**

早期计算机（如 DOS 时代）确实直接使用物理地址，但这带来了严重问题：

```
直接使用物理地址的问题：

1. 地址冲突
   - 程序 A 加载到 0x1000
   - 程序 B 也想加载到 0x1000
   - 必须手动协调加载位置（重定位）

2. 内存碎片
   - 程序 A 占用 0x1000-0x1FFF
   - 程序 B 占用 0x3000-0x3FFF
   - 0x2000-0x2FFF 空闲但无法利用（外部碎片）

3. 安全问题
   - 程序 A 可以读写任意物理地址
   - 可以修改程序 B 的数据，甚至操作系统代码
   - 恶意程序或程序错误会导致系统崩溃

4. 内存不足
   - 物理内存 4GB，程序需要 8GB
   - 无法运行（没有虚拟内存的换入换出机制）
```

**页表解决的问题：**

| 问题 | 页表如何解决 |
|------|-------------|
| **地址冲突** | 每个进程有独立的虚拟地址空间，都从 0x0000 开始，页表映射到不同的物理地址 |
| **内存碎片** | 虚拟地址连续，物理地址可以不连续（分页机制） |
| **安全隔离** | 页表项包含权限位，进程只能访问自己的页面 |
| **内存扩展** | 页表支持将不常用的页面换出到硬盘（Swap），实现虚拟内存大于物理内存 |

**页表的工作原理：**

```
CPU 发出虚拟地址 0x2000
        │
        ▼
┌───────────────────┐
│   MMU（内存管理单元）  │  ◄── 硬件支持，自动查页表
└───────────────────┘
        │
        ▼ 查找当前进程的页表
┌───────────────────┐
│ Page Table Entry  │
│ Virtual: 0x2000   │
│ Physical: 0x5000  │
│ Permission: RW    │
└───────────────────┘
        │
        ▼
访问物理地址 0x5000

如果页表中没有该映射，或权限不足 → 触发 Page Fault 异常
```

**为什么每个进程需要独立的页表：**

```
进程切换时：

1. CPU 切换到新进程
2. 加载新进程的页表基址到 CR3 寄存器（x86）
3. 后续所有地址访问使用新页表
4. 同一个虚拟地址，映射到不同的物理地址

这就是为什么"指针不能跨进程"的根本原因：
- 指针存储的是虚拟地址
- 页表是进程私有的
- 不同进程的页表映射不同
```

**总结**：页表是操作系统实现虚拟内存、进程隔离、内存保护的核心机制。没有页表，现代操作系统的多进程、多任务、内存安全都无法实现。

### 3.3 进程隔离的意义

进程隔离是操作系统安全机制的基础[^3]：

```
无虚拟内存（早期系统）：
  Process A bug ──► Overwrite Process B memory ──► System crash
  
有虚拟内存（现代系统）：
  Process A bug ──► Only affect Process A's address space
  Process B ──► Completely isolated, unaffected
```

这是操作系统设计的核心原则，**应用程序无法绕过**。

### 3.4 指针的本质

在 Go 中，指针存储的是虚拟地址：

```go
type Checkpoint struct {
    Step    int
    Current map[string][]Message
}

cp := &Checkpoint{Step: 1}
// cp 是指针，存储虚拟地址（如 0x2000）
// 该地址只在当前进程的页表中有效
```

**指针的局限性**：
- 指针值（虚拟地址）只在当前进程有意义
- 同一地址在不同进程映射到不同物理内存
- 进程退出后，该地址空间被回收

---

## 四、序列化的本质

### 4.1 定义

**序列化（Serialization/Marshalling）**：将内存中的数据结构转换为字节序列的过程。

**反序列化（Deserialization/Unmarshalling）**：将字节序列还原为内存中的数据结构的过程。

### 4.2 内存数据结构 vs 字节序列

```
内存中的数据结构（依赖运行时环境）：
┌─────────────────────────────────────────────────────┐
│ Type Information（Go Runtime）                       │
│ Virtual Pointers（Process-specific）                 │
│ Data Fields（语言特定的内存布局）                     │
└─────────────────────────────────────────────────────┘

字节序列（语言无关、进程无关）：
┌─────────────────────────────────────────────────────┐
│ 0x7b 0x22 0x53 0x74 0x65 0x70 ...                   │
│ 纯数据，自包含，任何环境都能解析                      │
└─────────────────────────────────────────────────────┘
```

### 4.3 序列化的转换过程

以 Go struct 为例：

```go
// 原始数据结构
cp := &Checkpoint{
    Step: 1,
    Current: map[string][]Message{
        "model": {{Answer: "test"}},
    },
}

// 内存布局（多个不连续的内存块，用指针串联）
cp (0x1000) ──► [Step=1, Current=0x2000]
                         │
                         ▼
              map header (0x2000) ──► buckets (0x3000)
                                              │
                                              ▼
                                   slice data (0x4000)

// 序列化后（一个连续的字节序列）
data, _ := json.Marshal(cp)
// []byte(`{"Step":1,"Current":{"model":[{"Answer":"test"}]}}`)

// 字节序列是连续的、自包含的
data[0] = 0x7b  // '{'
data[1] = 0x22  // '"'
data[2] = 0x53  // 'S'
...
```

### 4.4 序列化的关键操作

1. **去除指针依赖**：将指针引用转换为内联数据或引用标识
2. **类型信息编码**：将运行时类型信息编码为字节序列
3. **数据扁平化**：将不连续的内存块拼接为连续字节
4. **自包含性**：序列化结果包含所有解析所需信息

---

## 五、eino 框架中的序列化实现

### 5.1 Checkpoint 机制

eino 的 checkpoint 用于持久化图执行状态，支持断点续跑：

```go
// compose/checkpoint.go
type checkpoint struct {
    Channels       map[string]channel      // 通道状态
    Inputs         map[string]any          // 节点输入
    State          any                     // 全局状态
    SkipPreHandler map[string]bool         // 恢复时跳过的节点
    RerunNodes     []string                // 需要重跑的节点
    SubGraphs      map[string]*checkpoint  // 子图检查点
    InterruptID2Addr  map[string]Address   // 中断信号寻址
    InterruptID2State map[string]InterruptState
}
```

### 5.2 序列化架构

eino 采用自定义序列化方案，底层使用字节跳动的 **sonic** JSON 库[^4]：

```
Application Layer
       │
       ▼
checkPointer (eino 自定义序列化逻辑)
       │
       ├── Type Registration (schema.RegisterName)
       ├── Pointer Handling (flatten structure)
       └── Stream Conversion (handle streaming data)
       │
       ▼
sonic (高性能 JSON 序列化库)
       │
       ▼
[]byte (字节序列)
       │
       ▼
CheckPointStore (Redis/DB/文件)
```

### 5.3 类型注册机制

序列化时需要记录类型信息，反序列化时才能正确还原：

```go
// compose/checkpoint.go
func init() {
    // 注册类型，绑定类型名与 Go 类型
    schema.RegisterName[*checkpoint]("_eino_checkpoint")
    schema.RegisterName[*dagChannel]("_eino_dag_channel")
    schema.RegisterName[*pregelChannel]("_eino_pregel_channel")
    schema.RegisterName[dependencyState]("_eino_dependency_state")
}
```

**序列化流程**：

```go
func (c *checkPointer) set(ctx context.Context, id string, cp *checkpoint) error {
    // 1. 类型信息编码（写入类型名）
    // 2. 指针扁平化（转为内联数据）
    // 3. 序列化为字节
    data, err := c.serializer.Marshal(cp)
    if err != nil {
        return err
    }
    
    // 4. 存储字节到外部系统
    return c.store.Set(ctx, id, data)
}
```

**反序列化流程**：

```go
func (c *checkPointer) get(ctx context.Context, id string) (*checkpoint, bool, error) {
    // 1. 从外部系统读取字节
    data, existed, err := c.store.Get(ctx, id)
    if !existed {
        return nil, false, nil
    }
    
    // 2. 解析类型信息（读取类型名）
    // 3. 查找注册表，确定目标类型
    // 4. 创建 struct 实例，填充数据
    cp := &checkpoint{}
    err = c.serializer.Unmarshal(data, cp)
    
    return cp, true, nil
}
```

### 5.4 存储接口抽象

eino 定义了 `CheckPointStore` 接口，用户可实现不同的存储后端：

```go
// internal/core/interrupt.go
type CheckPointStore interface {
    Get(ctx context.Context, checkPointID string) ([]byte, bool, error)
    Set(ctx context.Context, checkPointID string, checkPoint []byte) error
}

// 可选的删除接口
type CheckPointDeleter interface {
    Delete(ctx context.Context, checkPointID string) error
}
```

**用户实现示例（Redis）**：

```go
type RedisCheckPointStore struct {
    client *redis.Client
}

func (s *RedisCheckPointStore) Get(ctx context.Context, id string) ([]byte, bool, error) {
    data, err := s.client.Get(ctx, "checkpoint:"+id).Bytes()
    if err == redis.Nil {
        return nil, false, nil
    }
    return data, true, err
}

func (s *RedisCheckPointStore) Set(ctx context.Context, id string, data []byte) error {
    return s.client.Set(ctx, "checkpoint:"+id, data, 0).Err()
}
```

### 5.5 InternalSerializer 实现

eino 自定义的序列化器处理类型信息编码：

```go
// internal/serialization/serialization.go
type InternalSerializer struct{}

func (i *InternalSerializer) Marshal(v any) ([]byte, error) {
    // 1. 内部序列化：提取类型信息，扁平化指针
    is, err := internalMarshal(v, nil)
    if err != nil {
        return nil, err
    }
    
    // 2. 使用 sonic 编码为 JSON 字节
    return sonic.Marshal(is)
}

func (i *InternalSerializer) Unmarshal(data []byte, v any) error {
    // 1. 使用 sonic 解码 JSON
    // 2. 读取类型信息，查找注册表
    // 3. 创建对应类型的实例
    // 4. 填充数据
}
```

---

## 六、深拷贝与序列化的对比

### 6.1 教学 Demo 的深拷贝方案

在 `04_pregel_checkpoint_demo` 中，使用内存存储 + 深拷贝：

```go
// checkpoint.go
type memoryStore struct {
    mu sync.Mutex
    m  map[string]*Checkpoint  // 直接存储 struct 指针
}

func (s *memoryStore) Set(_ context.Context, id string, cp *Checkpoint) error {
    s.mu.Lock()
    defer s.mu.Unlock()
    
    // 深拷贝：避免引用共享
    s.m[id] = &Checkpoint{
        Step:    cp.Step,
        Current: cloneCurrent(cp.Current),
    }
    return nil
}

// 手动深拷贝每一层
func cloneCurrent(src map[string][]Message) map[string][]Message {
    dst := make(map[string][]Message, len(src))
    for id, msgs := range src {
        cp := make([]Message, len(msgs))
        for i, m := range msgs {
            m.ToolCalls = append([]ToolCall(nil), m.ToolCalls...)
            m.Results = append([]string(nil), m.Results...)
            cp[i] = m
        }
        dst[id] = cp
    }
    return dst
}
```

### 6.2 对比分析

| 维度 | 深拷贝 | 序列化 |
|------|--------|--------|
| **输入** | Go struct 实例 | Go struct 实例 |
| **输出** | 新的 Go struct 实例 | `[]byte` |
| **跨进程** | ❌ 仅限同一进程 | ✅ 支持跨进程 |
| **持久化** | ❌ 进程退出即丢失 | ✅ 可存储到硬盘/Redis |
| **跨语言** | ❌ 仅限 Go | ✅ 使用标准格式（JSON）可跨语言 |
| **实现复杂度** | 低（手动遍历） | 高（类型注册、指针处理） |
| **性能** | 高（内存操作） | 中（涉及编解码） |
| **适用场景** | 同进程内存缓存 | 持久化存储、网络传输、进程间通信 |

### 6.3 序列化的深拷贝效应

序列化反序列化天然实现深拷贝：

```
原对象 ──► 序列化 ──► []byte ──► 反序列化 ──► 新对象
                                        │
                                        └── 新的内存地址，与原对象完全独立
```

---

## 七、总结

### 7.1 技术约束

| 约束 | 描述 | 影响 |
|------|------|------|
| 存储介质抽象 | 所有存储设备只认字节 | 数据结构必须转换为字节 |
| 进程地址隔离 | 每个进程有独立的虚拟地址空间 | 指针不能跨进程使用 |
| 运行时依赖 | 类型信息存在于语言运行时 | 进程退出后类型信息丢失 |

### 7.2 序列化的作用

```
序列化：内存数据结构（依赖环境）──► 字节序列（语言无关、进程无关）

关键操作：
1. 去除指针依赖（虚拟地址无效）
2. 编码类型信息（自包含解析所需信息）
3. 数据扁平化（连续字节序列）
```

### 7.3 一句话总结

**struct 实例依赖进程环境（虚拟地址、运行时类型），存储和传输只接受字节序列；序列化将依赖环境的数据结构转换为自包含的字节序列，实现持久化存储、网络传输和进程间通信。**

---

## 参考文献

[^1]: Hennessy, J. L., & Patterson, D. A. (2017). *Computer Architecture: A Quantitative Approach* (6th ed.). Morgan Kaufmann. — 存储层次结构与抽象

[^2]: Tanenbaum, A. S., & Bos, H. (2015). *Modern Operating Systems* (4th ed.). Pearson. — 虚拟内存机制

[^3]: Silberschatz, A., Galvin, P. B., & Gagne, G. (2018). *Operating System Concepts* (10th ed.). Wiley. — 进程隔离与保护

[^4]: ByteDance. (2023). *sonic: A blazingly fast JSON serializing & deserializing library*. https://github.com/bytedance/sonic

---

## 附录

### A. 常见序列化格式对比

| 格式 | 类型 | 性能 | 可读性 | Schema | 跨语言 |
|------|------|------|--------|--------|--------|
| JSON | 文本 | 中 | 高 | 否 | ✅ |
| XML | 文本 | 低 | 高 | 可选 | ✅ |
| YAML | 文本 | 低 | 高 | 否 | ✅ |
| Protocol Buffers | 二进制 | 高 | 低 | 是 | ✅ |
| MessagePack | 二进制 | 高 | 低 | 否 | ✅ |
| Gob (Go) | 二进制 | 中 | 低 | 否 | ❌ Go only |
| sonic (Go) | 文本(JSON) | 高 | 高 | 否 | ✅ |

### B. 序列化在分布式系统中的应用

```
应用场景              序列化的作用
─────────────────────────────────────────────────
RPC 通信              方法参数/返回值序列化传输
消息队列              消息体序列化存储
数据库存储            对象序列化为行/文档
缓存系统              对象序列化存储到 Redis/Memcached
Checkpoint/恢复       状态快照序列化持久化
配置文件              配置结构序列化为 YAML/JSON
```

### C. 相关术语

| 术语 | 英文 | 定义 |
|------|------|------|
| 序列化 | Serialization | 数据结构 → 字节序列 |
| 反序列化 | Deserialization | 字节序列 → 数据结构 |
| 编码 | Encoding | 同序列化 |
| 解码 | Decoding | 同反序列化 |
| 编组 | Marshalling | 同序列化（常见于 Go） |
| 解组 | Unmarshalling | 同反序列化（常见于 Go） |
| 持久化 | Persistence | 数据存储到非易失性介质 |
| 虚拟内存 | Virtual Memory | 操作系统提供的地址空间抽象 |
| 页表 | Page Table | 虚拟地址到物理地址的映射表 |
