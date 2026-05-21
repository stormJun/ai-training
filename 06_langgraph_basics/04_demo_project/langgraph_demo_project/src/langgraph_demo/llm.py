"""DashScope 大模型调用与响应组装辅助函数。"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass

import httpx

from .models import StockRecord


DEFAULT_DASHSCOPE_BASE_URL = "https://dashscope.aliyuncs.com/compatible-mode/v1"
DEFAULT_DASHSCOPE_MODEL = "qwen-plus"


class LLMError(RuntimeError):
    """大模型调用相关错误的基类。"""


class LLMConfigurationError(LLMError):
    """大模型配置错误。"""


class LLMResponseError(LLMError):
    """大模型返回内容不符合预期。"""


class LLMServiceError(LLMError):
    """大模型服务调用失败。"""


@dataclass(frozen=True)
class DashScopeConfig:
    """DashScope 兼容模式调用配置。"""

    api_key: str
    model: str
    base_url: str


def get_dashscope_config() -> DashScopeConfig | None:
    """从环境变量中读取 DashScope 配置。"""

    api_key = os.getenv("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        return None

    model = os.getenv("DASHSCOPE_MODEL", DEFAULT_DASHSCOPE_MODEL).strip() or DEFAULT_DASHSCOPE_MODEL
    base_url = os.getenv("DASHSCOPE_BASE_URL", DEFAULT_DASHSCOPE_BASE_URL).strip() or DEFAULT_DASHSCOPE_BASE_URL
    return DashScopeConfig(api_key=api_key, model=model, base_url=base_url.rstrip("/"))


def is_dashscope_enabled() -> bool:
    """当前环境是否启用了 DashScope。"""

    return get_dashscope_config() is not None


def _request_chat_completion(messages: list[dict[str, str]]) -> str:
    """调用 DashScope OpenAI 兼容接口并返回文本结果。"""

    config = get_dashscope_config()
    if config is None:
        raise LLMConfigurationError("未配置 DASHSCOPE_API_KEY。")

    try:
        response = httpx.post(
            f"{config.base_url}/chat/completions",
            headers={
                "Authorization": f"Bearer {config.api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": config.model,
                "messages": messages,
                "temperature": 0.2,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError as exc:
        raise LLMServiceError("调用 DashScope 失败。") from exc
    except ValueError as exc:
        raise LLMResponseError("DashScope 返回的内容不是合法 JSON。") from exc

    try:
        content = payload["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as exc:
        raise LLMResponseError("DashScope 返回结构不符合预期。") from exc

    if isinstance(content, str):
        return content
    if isinstance(content, list):
        text_parts = [
            part.get("text", "")
            for part in content
            if isinstance(part, dict) and part.get("type") == "text"
        ]
        merged = "\n".join(part for part in text_parts if part)
        if merged:
            return merged

    raise LLMResponseError("DashScope 未返回可解析的文本内容。")


def _extract_json_payload(content: str) -> dict[str, str]:
    """从模型输出中提取 JSON 对象。"""

    normalized = content.strip()
    if normalized.startswith("```"):
        lines = normalized.splitlines()
        if lines and lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        normalized = "\n".join(lines).strip()

    start = normalized.find("{")
    end = normalized.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise LLMResponseError("模型输出中没有合法的 JSON 对象。")

    try:
        payload = json.loads(normalized[start : end + 1])
    except json.JSONDecodeError as exc:
        raise LLMResponseError("模型输出不是合法 JSON。") from exc

    if not isinstance(payload, dict):
        raise LLMResponseError("模型输出 JSON 不是对象。")
    return payload


def _generate_structured_response(*, system_prompt: str, user_prompt: str) -> tuple[str, str]:
    """请求模型返回包含 summary/detail 的 JSON 结果。"""

    content = _request_chat_completion(
        [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]
    )
    payload = _extract_json_payload(content)

    summary = str(payload.get("summary", "")).strip()
    detail = str(payload.get("detail", "")).strip()
    if not summary or not detail:
        raise LLMResponseError("模型输出缺少 summary 或 detail 字段。")
    return summary, detail


def generate_stock_response(*, query: str, stock: StockRecord) -> tuple[str, str]:
    """基于单只股票数据生成自然语言回答。"""

    system_prompt = (
        "你是一名 A 股研究助理。"
        "请严格基于用户提供的结构化数据回答，不要虚构额外事实，不要声称数据是实时行情。"
        "输出必须是 JSON 对象，且只包含 summary 和 detail 两个字符串字段。"
    )
    user_prompt = (
        f"用户问题：{query}\n"
        "请基于以下示例数据生成回答，并明确这是示例数据而非实时行情。\n"
        f"股票数据：{json.dumps(stock.model_dump(), ensure_ascii=False)}"
    )
    return _generate_structured_response(system_prompt=system_prompt, user_prompt=user_prompt)


def generate_analysis_response(
    *,
    query: str,
    plan: str,
    ranking: list[tuple[StockRecord, float]],
) -> tuple[str, str]:
    """基于多只股票排序结果生成自然语言分析回答。"""

    ranking_payload = [
        {
            **stock.model_dump(),
            "score": score,
        }
        for stock, score in ranking
    ]
    system_prompt = (
        "你是一名 A 股研究助理。"
        "请严格基于用户提供的排序结果和示例数据回答，不要虚构额外事实，不要声称数据是实时行情。"
        "输出必须是 JSON 对象，且只包含 summary 和 detail 两个字符串字段。"
    )
    user_prompt = (
        f"用户问题：{query}\n"
        f"分析计划：{plan}\n"
        "请基于以下排序结果生成回答，并明确这是示例数据下的比较结论。\n"
        f"排序数据：{json.dumps(ranking_payload, ensure_ascii=False)}"
    )
    return _generate_structured_response(system_prompt=system_prompt, user_prompt=user_prompt)
