---
type: "maintenance"
status: "active"
created: "2026-06-12"
updated: "2026-06-12"
aliases:
  - "只读巡检协议"
  - "LLM Wiki Audit Protocol"
tags:
  - "ai-training"
  - "llm-wiki"
  - "maintenance"
  - "maintenance/audit"
sources:
  - "llm_wiki/AGENTS.md"
  - "llm_wiki/sources.yml"
---

# 只读巡检协议

本页定义 `llm_wiki/` 的手动只读巡检方式。巡检用于发现知识库漂移，但默认不修改任何课程文件、wiki 页面或维护记录。

## 巡检目标

- 发现 `llm_wiki/sources.yml` 中不存在的来源路径。
- 发现 wiki 页面中的失效 Markdown 链接和 Obsidian 双链。
- 发现已存在但尚未纳入 `llm_wiki/` 的顶层主题目录。
- 发现疑似重复笔记，供人工判断是否合并或建立主次关系。

## 默认行为

- 巡检默认只读。
- 报告默认输出到终端。
- 只有用户明确要求保存报告时，才写入 `runtime_artifacts/llm_wiki_audit/`。
- 只有用户明确要求采纳报告时，才更新 `llm_wiki/` 下的治理页面。

## 严重级别

| 级别 | 含义 | 例子 |
| --- | --- | --- |
| `ERROR` | 明确错误，需要优先修复 | 来源路径不存在、内部链接目标不存在 |
| `WARN` | 高概率漂移，需要人工确认 | 新主题未登记、疑似重复笔记 |
| `INFO` | 可选改进，不阻塞使用 | 可补充的主题页、可加强的项目入口 |

## 报告结构

```md
# LLM Wiki Audit Report

## Summary

- Errors: 0
- Warnings: 0
- Info: 0

## Stale Paths

## Broken Links

## Uncovered Topics

## Duplicate Candidates

## Suggested Next Actions
```

## Obsidian 连接

- [[wiki/index|AI 工程化训练营 LLM Wiki]]
- [[wiki/maintenance/index|维护索引]]
