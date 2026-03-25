### 多代理文章自动编写系统（assignments/multi_agent_homework）

本作业实现了一个基于 MCP 工具服务的四代理写作流程：研究 → 撰写 → 审核 → 润色。LangGraph 负责串联节点，工具层通过 FastMCP 暴露 `search` 和 `get_prompt`，并在模型不可用时提供内置回退逻辑。

---

#### 系统设计
- **MCP 工具服务**：`multi-agent/mcp_server/main.py` 暴露搜索与提示词工具；搜索失败时返回占位数据，确保流程不中断。
- **代理角色**：`langgraph_app/nodes.py` 定义四个节点，优先调用通义千问（`qwen-plus`），失败时自动切换到模板化写作回退。
- **编排**：`langgraph_app/graph.py` 用线性图描述完整流程，状态中携带日志与阶段性产出，便于最终汇总。
- **输出**：`main.py` 将最终文章与过程日志写入 `article_output_*.md`，同时在终端回显执行状态。

#### 使用方式
1. 安装/激活环境（两种方式二选一）：
   - 已有仓库外的共享 `.venv`：进入 `assignments/multi_agent_homework` 后 `source ../.venv/bin/activate`（或你的实际路径），然后 `pip install -e .` 以当前项目元数据安装依赖。
   - 使用 uv：`cd assignments/multi_agent_homework && uv sync`（无锁文件，直接安装）。
2. 启动 MCP 工具服务：`cd assignments/multi_agent_homework && python -m multi-agent.mcp_server.main`（在已激活的环境中运行；若用 uv 亦可 `uv run ...`）。
3. 另开终端运行客户端：`cd assignments/multi_agent_homework && python -m multi-agent.main`，按提示输入主题/风格/字数。
4. 生成文件位于 `assignments/multi_agent_homework/multi-agent/article_output_*.md`。
   - 可在运行前导出 `DASHSCOPE_API_KEY`（或复制 `.env.example` 为 `.env` 填入 Key），启用 Qwen 在线生成；未设置时会走本地回退模板，流程依旧可跑通。

#### 示例输出（节选）
```
# 最终文章：帮我写一篇关于AI Agent的文章

引言：围绕“帮我写一篇关于AI Agent的文章”，本文将概述背景与现状。
正文：基于研究资料，核心概念、关键技术与应用场景按层次展开：
## 核心概念
- 主题：“帮我写一篇关于AI Agent的文章”，围绕 AI 智能体应用展开。
...
结论：主题“帮我写一篇关于AI Agent的文章”仍在快速演进，未来需要关注实践落地与风险治理。

---

## 执行记录
- 研究：ℹ️ (fallback) 研究阶段完成
- 撰写：ℹ️ (fallback) 撰写阶段完成
- 审核：ℹ️ (fallback) 审核阶段完成
- 润色：ℹ️ (fallback) 润色阶段完成
```

> 若已配置 `DASHSCOPE_API_KEY` 并联网，示例中的“ℹ️ (fallback)”会变为“✅”，内容也会由模型实时生成。
