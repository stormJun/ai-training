# LangGraph Studio

这份材料的目标不是讲业务流程，而是讲：

> 当你已经有一张 LangGraph 图时，怎样在本地把它跑成服务，并用 Studio 观察和调试。

---

## LangGraph Studio 是什么

LangGraph Studio 可以理解成一个专门面向 LangGraph 项目的可视化调试入口。

它通常和 `langgraph dev` 一起使用：

- `langgraph dev`
  在本地启动 LangGraph API
- Studio
  连接这个本地 API，查看图、输入、输出和执行过程

所以 Studio 本身不是“单独运行一个脚本”，而是：

> 先有一个符合 LangGraph 项目结构的目录，再通过 `langgraph dev` 启动它。

---

## 什么时候需要它

当你只是想理解 `StateGraph` 基础概念时，其实不需要 Studio。

Studio 更适合下面这些场景：

- 图节点变多了，想看整体结构
- 想验证不同输入会走哪条边
- 想观察节点执行顺序和返回结果
- 想在服务化项目里本地联调

也就是说：

- `01_intro`
  主要靠读代码和直接运行脚本
- `Studio`
  更适合开始做项目化、本地服务化调试的时候用

---

## 最小准备

先安装 CLI：

```bash
pip install -U "langgraph-cli[inmem]"
```

如果你想配合调试器，也可以装：

```bash
pip install debugpy
```

---

## 创建一个新的 LangGraph 项目

如果你想从空目录生成一个标准项目骨架，可以用：

```bash
langgraph new "/absolute/path/to/my_graph_app" --template new-langgraph-project-python
```

这个命令会生成一套标准结构，通常包括：

- `src/agent/graph.py`
- `langgraph.json`
- `pyproject.toml`
- `README.md`

这类目录适合直接拿来跑 `langgraph dev`。

---

## 在本仓库里怎么用

这个仓库里最适合配合 Studio 使用的不是当前 `02_workflows` 目录，而是后面的服务化项目：

- `03_service_apps/projects/02_langgraph_server_minimal/`
- `03_service_apps/projects/03_order_workflow_app/`

推荐你直接在这些目录里运行：

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/03_service_apps/projects/02_langgraph_server_minimal
langgraph dev
```

或者：

```bash
cd /Users/songxijun/workspace/otherProject/ai-training/02_langgraph_basics/03_service_apps/projects/03_order_workflow_app
langgraph dev
```

---

## 启动后你通常会看到什么

`langgraph dev` 正常启动后，通常会给出几个本地地址：

- API
  例如 `http://127.0.0.1:2024`
- API 文档
  例如 `http://127.0.0.1:2024/docs`
- Studio URL
  一般是带 `baseUrl=http://127.0.0.1:2024` 的链接

你可以把它理解成这样一条链路：

```text
graph.py
  -> langgraph dev
  -> 本地 API
  -> Studio 连接本地 API
  -> 可视化调试
```

---

## 调试时重点看什么

第一次用 Studio，不要试图一下看太多东西，先只看 4 个点：

1. 图结构
   节点和边是不是和你预期一致
2. 输入状态
   传入的字段是不是完整
3. 节点输出
   每个节点到底写回了什么
4. 路由结果
   条件边最后走到了哪里

这样你就能把“代码里定义的图”和“运行时真实发生的事情”对上。

---

## `debugpy` 有什么用

Studio 主要解决“图级别的观察”。

但如果你还想进一步：

- 在节点函数里打断点
- 单步看具体 Python 逻辑
- 检查某个状态字段为什么被写成某个值

那就可以配合 `debugpy` 或 IDE 调试器一起用。

也就是说：

- Studio 负责看“工作流”
- `debugpy` 负责看“节点内部代码”

这两个并不冲突。

---

## 这份材料真正要你学会什么

- Studio 不是替代 LangGraph，而是辅助调试工具
- 它依赖 `langgraph dev` 提供本地 API
- 最适合配合“服务化项目目录”使用
- 当图开始复杂时，可视化调试会比只看终端输出高效很多

---

## 建议下一步

如果你只是第一次接触 Studio，建议下一步直接去跑：

- `03_service_apps/projects/02_langgraph_server_minimal`

这是最小、最干净、最适合配 Studio 的示例。  
