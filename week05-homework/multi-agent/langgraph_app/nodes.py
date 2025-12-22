import json
import textwrap
from typing import Any, Dict, List, Tuple, Callable

from langchain_core.messages import SystemMessage, HumanMessage

from .state import AgentState


class AgentNodes:
    """Nodes executed inside the LangGraph workflow."""

    def __init__(self, mcp_tools: list):
        self.mcp_tools = {tool.name: tool for tool in mcp_tools}
        self.llm = self._init_llm()

    def _init_llm(self):
        """Lazily load the LLM; return None if SDK/model is unavailable."""
        try:
            from langchain_community.chat_models import ChatTongyi
        except Exception:
            return None

        try:
            return ChatTongyi(model="qwen-plus")
        except Exception:
            return None

    def _parse_search_results(self, raw_results: str) -> List[Dict[str, Any]]:
        try:
            data = json.loads(raw_results)
        except json.JSONDecodeError:
            return [{"title": "解析失败", "href": "", "body": raw_results}]
        if isinstance(data, dict):
            data = [data]
        if not isinstance(data, list):
            return [{"title": "未知格式", "href": "", "body": str(data)}]
        return data

    async def _call_mcp_tool(self, tool_name: str, **kwargs):
        if tool_name not in self.mcp_tools:
            raise ValueError(f"Tool '{tool_name}' not found.")
        tool = self.mcp_tools[tool_name]
        return await tool.ainvoke(kwargs)

    async def _maybe_generate(
        self,
        system_prompt: str,
        user_prompt: str,
        fallback: Callable[[], str],
    ) -> Tuple[str, bool]:
        """Try LLM generation; fall back to deterministic template on failure."""
        if self.llm is None:
            return fallback(), False

        try:
            messages = [SystemMessage(content=system_prompt), HumanMessage(content=user_prompt)]
            response = await self.llm.ainvoke(messages)
            return response.content, True
        except Exception:
            return fallback(), False

    def _format_sources(self, results: List[Dict[str, Any]]) -> str:
        lines = []
        for idx, item in enumerate(results[:6], start=1):
            title = item.get("title") or f"结果 {idx}"
            href = item.get("href") or ""
            snippet = item.get("body") or ""
            lines.append(f"{idx}. {title} - {href}\n   {snippet}")
        return "\n".join(lines) or "无搜索结果"

    def _fallback_research(self, topic: str, results: List[Dict[str, Any]]) -> str:
        sources = self._format_sources(results)
        focus_points = [item.get("title", topic) for item in results[:3]]
        aspects = "; ".join(focus_points) or topic
        return textwrap.dedent(
            f"""
            ## 核心概念
            - 主题：“{topic}”，围绕 {aspects} 展开。

            ## 关键技术或重点
            - {aspects}

            ## 应用场景
            - 实际案例可以从上述搜索结果中提炼，例如产品发布、技术解读或行业实践。

            ## 未来趋势
            - 预期将继续深化落地，关注安全、成本和可解释性。

            ## 参考资料
            {sources}
            """
        ).strip()

    def _fallback_draft(self, topic: str, research_report: str) -> str:
        return textwrap.dedent(
            f"""
            引言：围绕“{topic}”，本文将概述背景与现状。

            正文：基于研究资料，核心概念、关键技术与应用场景按层次展开：
            {research_report}

            结论：主题“{topic}”仍在快速演进，未来需要关注实践落地与风险治理。
            """
        ).strip()

    def _fallback_review(self, draft: str) -> str:
        findings = []
        if len(draft) < 200:
            findings.append("文章略短，可增加示例和数据支撑。")
        if "结论" not in draft:
            findings.append("补充结论部分，强调行动建议。")
        if not findings:
            findings.append("文章质量良好，无需重大修改。")
        return "\n".join(f"- {item}" for item in findings)

    def _fallback_polish(self, draft: str, suggestions: str) -> str:
        return textwrap.dedent(
            f"""
            {draft}

            （已采纳审核建议：{suggestions.replace(' -', '').strip()}）
            """
        ).strip()

    async def research_node(self, state: AgentState) -> Dict[str, Any]:
        prompt = await self._call_mcp_tool("get_prompt", agent_name="research")
        raw_results = await self._call_mcp_tool("search", topic=state["topic"])
        search_items = self._parse_search_results(raw_results)
        sources_text = self._format_sources(search_items)

        user_prompt = f"主题：{state['topic']}\n\n搜索结果：\n{sources_text}"
        report, used_llm = await self._maybe_generate(
            prompt, user_prompt, lambda: self._fallback_research(state["topic"], search_items)
        )
        prefix = "✅" if used_llm else "ℹ️ (fallback)"
        log_entry = f"## 研究报告\n{report}\n\n来源：\n{sources_text}"
        return {
            "research_report": report,
            "search_sources": search_items,
            "log": state.get("log", []) + [f"{prefix} 研究阶段完成"],
            "log_research": log_entry,
        }

    async def writing_node(self, state: AgentState) -> Dict[str, Any]:
        prompt_template = await self._call_mcp_tool("get_prompt", agent_name="write")
        prompt = prompt_template.format(style=state["style"], length=state["length"])
        user_prompt = state["research_report"]
        draft, used_llm = await self._maybe_generate(
            prompt, user_prompt, lambda: self._fallback_draft(state["topic"], state["research_report"])
        )
        prefix = "✅" if used_llm else "ℹ️ (fallback)"
        log_entry = f"## 文章初稿\n{draft}"
        return {"draft": draft, "log": state.get("log", []) + [f"{prefix} 撰写阶段完成"], "log_draft": log_entry}

    async def review_node(self, state: AgentState) -> Dict[str, Any]:
        prompt = await self._call_mcp_tool("get_prompt", agent_name="review")
        suggestions, used_llm = await self._maybe_generate(
            prompt, state["draft"], lambda: self._fallback_review(state["draft"])
        )
        prefix = "✅" if used_llm else "ℹ️ (fallback)"
        log_entry = f"## 审核建议\n{suggestions}"
        return {
            "review_suggestions": suggestions,
            "log": state.get("log", []) + [f"{prefix} 审核阶段完成"],
            "log_review": log_entry,
        }

    async def polishing_node(self, state: AgentState) -> Dict[str, Any]:
        prompt = await self._call_mcp_tool("get_prompt", agent_name="polish")
        user_input = f"文章初稿：\n{state['draft']}\n\n审核建议：\n{state['review_suggestions']}"
        final_article, used_llm = await self._maybe_generate(
            prompt,
            user_input,
            lambda: self._fallback_polish(state["draft"], state["review_suggestions"]),
        )
        prefix = "✅" if used_llm else "ℹ️ (fallback)"
        log_entry = f"## 最终稿件\n{final_article}"
        return {
            "final_article": final_article,
            "log": state.get("log", []) + [f"{prefix} 润色阶段完成"],
            "log_polish": log_entry,
        }
