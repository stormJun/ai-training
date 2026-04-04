# OpenAI Skills 学习笔记与最佳实践

更新时间：2026-03-26

这份文档用于补充 `27_autogen_two_agent_chat` 目录下关于多 Agent 工作流复用能力的学习材料，重点整理 OpenAI 官方文档里关于 `skills` 的定义、使用方式和最佳实践。

## 1. 先给结论

如果只想快速理解 OpenAI 的 `skills`，可以先记住下面 6 点：

1. `skill` 不是普通提示词，而是一整个可复用能力包。
2. 一个 skill 至少包含一个 `SKILL.md`，也可以带 `scripts/`、`references/`、`assets/`。
3. 模型不会一开始就把 skill 全文塞进上下文，而是先看 `name` 和 `description` 决定要不要加载。
4. 在 OpenAI API 里，skills 主要用于 shell 环境中的可复用流程。
5. 在 Codex 体系里，skills 更偏向仓库内工作流沉淀，比如验证、文档同步、发布检查。
6. skills 很强，但也有安全风险，尤其是联网场景下的 prompt injection 和数据外泄风险。

## 2. OpenAI 里说的 Skill 到底是什么

OpenAI API 文档把 skill 定义为：

- 一个带版本的文件包
- 以 `SKILL.md` 作为 manifest
- 可以把流程、约定、规范、多步工作流封装进去

更直白一点说，skill 是“把一类任务需要的操作说明、脚本、参考资料打包成一个独立模块”，让模型在需要时再读取和执行，而不是把所有规则都硬塞进 system prompt。

Codex 官方文档也用了同样的思路：skill 适合承载可重复工作流，因为它能携带更丰富的说明、脚本和参考资料，同时又不会在一开始把上下文撑爆。

## 3. Skill 的典型目录结构

官方文档里最常见的结构是：

```text
my-skill/
├── SKILL.md
├── scripts/
├── references/
└── assets/
```

各部分作用可以这样理解：

- `SKILL.md`：必须有，负责元数据和主说明。
- `scripts/`：可选，放可执行脚本。
- `references/`：可选，放补充文档、规则、说明书。
- `assets/`：可选，放模板、示例输入、静态资源。

## 4. 它为什么比“把流程写进 prompt”更好

OpenAI Cookbook 对 skills 的定位很清楚：它处在 prompt 和 tools 之间，是一层“中间层”。

- Prompt 负责 always-on 的全局行为。
- Tool 负责原子能力和副作用。
- Skill 负责把可重复流程打包起来，按需挂载和按需调用。

这样做的价值主要有四个：

- 更省上下文，因为默认只暴露 skill 元数据。
- 更利于复用，同一套流程可以重复挂载给不同 agent。
- 更利于版本管理，能区分 `default_version` 和 `latest_version`。
- 更利于工程化，可以把流程和脚本一起测试、一起迭代。

## 5. OpenAI 的 Skill 是怎么被模型“发现”和“触发”的

这一点很关键。

根据 OpenAI API 官方文档和 Cookbook：

- 平台会先把每个 skill 的 `name`、`description`、`path` 放进模型可见上下文。
- 模型先根据这些元数据判断是否应该用某个 skill。
- 只有模型决定要使用该 skill 时，才会去读完整的 `SKILL.md`。
- 如果还需要更多资料，模型再继续读取 references，或执行脚本。

这就是典型的 progressive disclosure。

所以 skill 设计里最重要的，不只是正文写得好，而是：

- `name` 是否好理解
- `description` 是否清楚说明“什么时候该用”
- `SKILL.md` 是否把触发边界写清楚

## 6. OpenAI API 里的使用方式

### 6.1 创建 skill

官方支持两种创建方式：

- 直接上传目录中的多个文件
- 上传 zip 包

Cookbook 明确建议在很多实际场景里优先用 zip，因为更稳定、也更方便做版本化管理。

### 6.2 在 Responses API 里挂载

skills 主要通过 shell tool 挂载到运行环境中。

Hosted shell 场景下，常见思路是：

```json
{
  "model": "gpt-5.4",
  "tools": [
    {
      "type": "shell",
      "environment": {
        "type": "container_auto",
        "skills": [
          { "type": "skill_reference", "skill_id": "<skill_id>" }
        ]
      }
    }
  ]
}
```

如果是 local shell，则不是挂远端 `skill_reference`，而是直接给本地 skill 路径。

### 6.3 版本管理

官方文档里已经明确有这些概念：

- `default_version`
- `latest_version`
- `skill_reference.version`

生产环境里更推荐显式 pin 版本，而不是总是追着 `latest` 跑。因为你真正想要的是“运行某个稳定流程版本”，而不是“运行当前最新但未必验证过的版本”。

## 7. OpenAI 官方总结出来的最佳实践

基于 OpenAI Cookbook 和 Codex 文档，可以把最佳实践压缩成下面这些原则。

### 7.1 让 skill 容易被发现

- frontmatter 里的 `name` 和 `description` 要清楚。
- `SKILL.md` 里要写明：什么时候用、怎么运行、预期输出、常见坑。
- 最好显式写出 `Use when...` 和 `Don't use when...`。
- 正例和反例都要给，能提升路由准确率。

### 7.2 把 skill 设计成“小而稳”的工作流

OpenAI 在介绍自己维护 OSS 仓库的实践时，强调每个 skill 都应该具备：

- narrow contract
- clear trigger
- concrete output

也就是：

- 解决一个明确问题
- 触发条件清楚
- 输出结果具体

不要把 skill 写成“全能说明书”。

### 7.3 把 skill 设计成 tiny CLI

Cookbook 特别建议把 skill 里的脚本设计成小型命令行工具：

- 可以直接从命令行执行
- stdout 尽量稳定
- 出错时要明确失败
- 输出文件路径尽量固定

这会显著提升 agent 调用时的稳定性。

### 7.4 不要把 skill 全文再抄进 system prompt

如果 system prompt 里又写了一遍完整流程：

- 可复用性会下降
- 技能边界会变模糊
- 版本化意义会被削弱

skill 的价值本来就是“条件触发 + 独立维护 + 独立版本化”。

### 7.5 把 skill 放在离工作流最近的地方

Codex 官方实践建议：

- 通用个人习惯型 skills 放全局目录
- 仓库专属 workflow 放 repo 内的 `.agents/skills`

这样可以把技能和代码、CI、文档一起维护，避免知识漂移。

## 8. Skill 和 MCP、Tool、Prompt 的关系

这几个概念很容易混。

可以这样记：

- Prompt：定义长期生效的全局行为
- Tool：提供具体动作能力
- Skill：定义“什么时候用哪些工具、按什么流程做”
- MCP：把外部系统能力接进来

一个很实用的理解方式是：

- Tool 是 capability endpoint
- Skill 是 orchestration guidance
- MCP 是 external connectivity layer

Codex 官方文档也明确提到，skills 和 MCP 往往是配套关系：

- skill 负责定义流程
- MCP 负责连接外部系统

## 9. OpenAI 自己怎么用 Skills

OpenAI 在 2026-03-09 发布的官方博客里，专门介绍了他们如何在 `openai-agents-python` 和 `openai-agents-js` 这两个仓库里使用 repo-local skills。

典型 skill 包括：

- 代码改动验证
- 文档同步检查
- 示例自动运行
- 发布前检查
- PR 摘要生成
- 测试覆盖率改进

这里最值得学习的不是具体 skill 名字，而是它背后的组织方式：

- 把高频工作流沉淀到仓库里
- 用 skill 让 agent 能稳定复用
- 对需要强约束的流程，配合 CI 或 GitHub Action

这已经不是“写提示词”的思路，而是比较完整的 agent engineering。

## 10. 风险与安全注意事项

这一部分不能忽略。

OpenAI 官方文档明确提醒：

- skill 要被当作高权限代码和指令来审查
- skill 可能影响模型规划、工具调用和命令执行
- 联网场景下尤其要注意 prompt injection 驱动的数据外泄

几个务实建议：

1. 不要把开放 skill 仓库直接暴露给普通终端用户自由选择。
2. 对写操作、高影响操作加显式审批。
3. 对联网 skill 使用严格 allowlist。
4. 把 skill 视为潜在不可信输入，先审查再集成。

另外，官方还提到一个容易忽略的限制：

- OpenAI hosted containers 中运行的 skills，不能用于启用了 Zero Data Retention 的场景。

## 11. 最推荐阅读的 4 篇官方资料

如果要系统学，我建议按这个顺序读。

### 1) Skills | OpenAI API

作用：

- 看官方定义
- 看上传、挂载、版本化
- 看 hosted/local shell 的差异

链接：

- https://developers.openai.com/api/docs/guides/tools-skills

### 2) Skills in OpenAI API | Cookbook

作用：

- 看最完整的 runnable example
- 看工程化最佳实践
- 看为什么 skills 是 prompt 和 tools 之间的中间层

链接：

- https://developers.openai.com/cookbook/examples/skills_in_api

### 3) Customization | Codex

作用：

- 看 Codex 视角下 skill 的定位
- 看和 `AGENTS.md`、MCP、subagents 的关系

链接：

- https://developers.openai.com/codex/concepts/customization

### 4) Using skills to accelerate OSS maintenance

作用：

- 看 OpenAI 官方团队自己的真实落地方法
- 最接近“经典实战文章”

发布时间：

- 2026-03-09

链接：

- https://developers.openai.com/blog/skills-agents-sdk

## 12. 一句话总结

OpenAI 的 `skills` 本质上是“给 agent 使用的可版本化工作流模块”。它比单纯 prompt 更可维护，比单独 tool 更接近真实流程编排，也比一次性临时说明更适合沉淀成团队资产。

如果你在做多 Agent、工具调用、MCP 集成或者仓库级自动化，skills 是非常值得重点学习的一层。

## 参考来源

- OpenAI API Docs: Skills
- OpenAI Cookbook: Skills in OpenAI API
- OpenAI Developers: Customization
- OpenAI Developers Blog: Using skills to accelerate OSS maintenance
