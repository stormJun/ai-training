"""
Pure-Python DeerFlow prompt layering demo.

This script demonstrates three ideas from 13a_deerflow_prompt_template_design.md:
1. Stable rules stay in a static system prompt
2. Dynamic context is injected as hidden reminder messages
3. Title extraction must skip reminder messages and use real user/assistant turns
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
import re


_DYNAMIC_CONTEXT_REMINDER_KEY = "dynamic_context_reminder"
_SUMMARY_MESSAGE_NAME = "summary"
_CURRENT_DATE_RE = re.compile(r"<current_date>([^<]+)</current_date>")
_THINK_TAG_RE = re.compile(r"<think>[\s\S]*?</think>", flags=re.IGNORECASE)


@dataclass
class Message:
    role: str
    content: str
    name: str | None = None
    additional_kwargs: dict[str, Any] = field(default_factory=dict)


def build_system_prompt(
    *,
    skill_names: list[str] | None = None,
    subagent_enabled: bool = True,
    max_concurrent_subagents: int = 3,
) -> str:
    """Build a static system prompt plus optional capability sections."""
    sections = [
        "<role>You are a lead AI agent focused on accurate, concise help.</role>",
        "<working_style>Clarify ambiguous requests, cite concrete facts, and prefer direct execution for simple tasks.</working_style>",
        "<response_style>Use short technical explanations and keep output structured.</response_style>",
        "<critical_reminders>Stable rules belong here; per-user or per-date context does not.</critical_reminders>",
    ]

    if skill_names:
        skills_text = "\n".join(f"- {skill}" for skill in skill_names)
        sections.append(
            "<available_skills>\n"
            "Use these skills when they materially improve accuracy or efficiency.\n"
            f"{skills_text}\n"
            "</available_skills>"
        )

    if subagent_enabled:
        sections.append(
            "<subagent_system>\n"
            f"You may decompose complex work across up to {max_concurrent_subagents} parallel subagents.\n"
            "</subagent_system>"
        )

    return "\n\n".join(sections)


def build_full_reminder(memory_facts: list[str], current_date: str) -> str:
    lines = ["<system-reminder>"]
    if memory_facts:
        lines.append("<memory>")
        lines.extend(memory_facts)
        lines.append("</memory>")
        lines.append("")
    lines.append(f"<current_date>{current_date}</current_date>")
    lines.append("</system-reminder>")
    return "\n".join(lines)


def build_date_update_reminder(current_date: str) -> str:
    return "\n".join(
        [
            "<system-reminder>",
            f"<current_date>{current_date}</current_date>",
            "</system-reminder>",
        ]
    )


def is_dynamic_context_reminder(message: Message) -> bool:
    return (
        message.role == "human"
        and bool(message.additional_kwargs.get(_DYNAMIC_CONTEXT_REMINDER_KEY))
    )


def extract_last_injected_date(messages: list[Message]) -> str | None:
    for message in reversed(messages):
        if is_dynamic_context_reminder(message):
            match = _CURRENT_DATE_RE.search(message.content)
            if match:
                return match.group(1)
    return None


def can_receive_dynamic_injection(message: Message) -> bool:
    return (
        message.role == "human"
        and not is_dynamic_context_reminder(message)
        and message.name != _SUMMARY_MESSAGE_NAME
    )


def inject_dynamic_context(
    messages: list[Message],
    *,
    memory_facts: list[str],
    current_date: str,
) -> list[Message]:
    """Inject full reminder on first turn, or date-only reminder on day change."""
    injected_messages = list(messages)
    last_injected_date = extract_last_injected_date(injected_messages)

    if last_injected_date is None:
        reminder = Message(
            role="human",
            content=build_full_reminder(memory_facts, current_date),
            additional_kwargs={
                "hide_from_ui": True,
                _DYNAMIC_CONTEXT_REMINDER_KEY: True,
            },
        )
        first_human_index = next(
            i for i, message in enumerate(injected_messages) if can_receive_dynamic_injection(message)
        )
        injected_messages.insert(first_human_index, reminder)
        return injected_messages

    if last_injected_date == current_date:
        return injected_messages

    reminder = Message(
        role="human",
        content=build_date_update_reminder(current_date),
        additional_kwargs={
            "hide_from_ui": True,
            _DYNAMIC_CONTEXT_REMINDER_KEY: True,
        },
    )
    last_human_index = next(
        i
        for i in range(len(injected_messages) - 1, -1, -1)
        if can_receive_dynamic_injection(injected_messages[i])
    )
    injected_messages.insert(last_human_index, reminder)
    return injected_messages


def normalize_content(content: Any) -> str:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(normalize_content(item) for item in content if normalize_content(item))
    if isinstance(content, dict):
        if isinstance(content.get("text"), str):
            return content["text"]
        if "content" in content:
            return normalize_content(content["content"])
    return ""


def strip_think_tags(text: str) -> str:
    return _THINK_TAG_RE.sub("", text).strip()


def build_title_prompt(messages: list[Message], max_words: int = 8) -> tuple[str, str]:
    """Build a small title-generation prompt from the first real user/assistant exchange."""
    first_user = next(
        normalize_content(message.content)
        for message in messages
        if message.role == "human" and not is_dynamic_context_reminder(message)
    )
    first_ai = next(
        strip_think_tags(normalize_content(message.content))
        for message in messages
        if message.role == "ai"
    )

    prompt = (
        f"Write a concise conversation title in at most {max_words} words.\n"
        f"User: {first_user[:500]}\n"
        f"Assistant: {first_ai[:500]}"
    )
    return prompt, first_user


def print_messages(messages: list[Message], title: str) -> None:
    print(f"\n=== {title} ===")
    for index, message in enumerate(messages, start=1):
        hidden = " hidden" if message.additional_kwargs.get("hide_from_ui") else ""
        print(f"[{index}] {message.role}{hidden}")
        print(message.content)
        print()


def main() -> None:
    system_prompt = build_system_prompt(
        skill_names=["requesting-code-review", "verification-before-completion"],
        subagent_enabled=True,
        max_concurrent_subagents=3,
    )

    day_one_messages = [
        Message(role="human", content="帮我解释一下 DeerFlow 的 prompt template 是怎么设计的"),
    ]
    day_one_history = inject_dynamic_context(
        day_one_messages,
        memory_facts=["User prefers concise technical explanations."],
        current_date="2026-05-12, Tuesday",
    )
    day_one_history.append(
        Message(
            role="ai",
            content=(
                "<think>internal reasoning omitted</think>\n"
                "DeerFlow 把稳定规则放到静态 system prompt，把动态上下文放到运行时 middleware 注入。"
            ),
        )
    )

    title_prompt, fallback_user_text = build_title_prompt(day_one_history)

    day_two_history = list(day_one_history)
    day_two_history.append(Message(role="human", content="如果对话跨天，为什么不直接改第一条 reminder？"))
    day_two_history = inject_dynamic_context(
        day_two_history,
        memory_facts=["User prefers concise technical explanations."],
        current_date="2026-05-13, Wednesday",
    )

    print("=== Static System Prompt ===")
    print(system_prompt)
    print_messages(day_one_history, "Model Message History - Day One")
    print("=== Title Prompt Built From First Real Exchange ===")
    print(title_prompt)
    print("\n=== Title Fallback Source ===")
    print(fallback_user_text)
    print_messages(day_two_history, "Model Message History - Next Day")


if __name__ == "__main__":
    main()
