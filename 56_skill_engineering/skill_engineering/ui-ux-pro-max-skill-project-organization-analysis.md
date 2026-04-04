# UI UX Pro Max 项目组织方式详细分析

更新时间：2026-04-01

本文分析项目：

- `/Users/songxijun/workspace/otherProject/ui-ux-pro-max-skill-main`

本文目的：

- 从 skill engineering 视角，拆解 `ui-ux-pro-max-skill-main` 是如何组织一套可分发、可扩展、可维护的技能体系
- 解释它如何把 `SKILL.md`、`references/`、`scripts/`、`data/`、`templates/` 串联起来
- 说明这种组织方式对仓库内技能设计，尤其是 `zl-base-business/tools/codex-skills/local-api-self-test` 一类项目型 skill，有哪些启发

---

## 1. 先给结论

`ui-ux-pro-max-skill-main` 不是一个“单独 skill 目录”，而是一个“技能产品仓库”。

它的核心组织思想是：

1. 用一个仓库承载一组相关 skill，而不是只承载一个 skill。
2. 用不同层次的 skill 处理不同粒度的问题：
   - 顶层总入口 skill
   - 领域型 skill
   - 专项 skill
3. 用共享的 `data/`、`scripts/`、`templates/` 作为知识和执行底座。
4. 用 `SKILL.md` 做路由和编排，而不是把所有细节硬塞进一个超长文档。
5. 用 CLI 和 marketplace 元数据把技能从“本地目录”升级成“可安装、可发布的产品”。

如果从技能工程成熟度看，这个仓库已经明显超过“写几个 skill 文件”的阶段，进入了“技能平台化”阶段。

---

## 2. 整体分层结构

从目录看，这个项目大致可以分成四层。

### 2.1 发布与产品元数据层

相关文件：

- `skill.json`
- `.claude-plugin/plugin.json`
- `.claude-plugin/marketplace.json`

这一层负责回答：

- 这个技能产品叫什么
- 对外怎么描述
- 版本号是什么
- 支持哪些平台
- 如何安装
- marketplace 暴露哪个 skill 作为入口

例如：

- `skill.json` 更像跨平台产品描述
- `.claude-plugin/plugin.json` 更像 Claude Marketplace 发布清单

这说明作者把 skill 当成了“可发布能力包”，不是只在本地仓库里自己用的脚本集合。

### 2.2 源码真相层

相关目录：

- `src/ui-ux-pro-max/data`
- `src/ui-ux-pro-max/scripts`
- `src/ui-ux-pro-max/templates`

这个层是整个项目最关键的设计点：**把真正需要维护的内容集中到一个 source of truth 目录里**。

`CLAUDE.md` 明确说明：

- `src/ui-ux-pro-max/` 是唯一真相来源
- 日常修改只改这里
- 其他位置要么通过符号链接复用，要么通过打包同步得到

这个设计避免了多份知识副本长期漂移。

### 2.3 运行时 skill 层

相关目录：

- `.claude/skills/ui-ux-pro-max`
- `.claude/skills/design`
- `.claude/skills/brand`
- `.claude/skills/design-system`
- `.claude/skills/slides`
- `.claude/skills/banner-design`
- `.claude/skills/ui-styling`

这一层才是模型真正会命中的技能入口层。

它不是“一个总 skill + 一堆注释文件”，而是一个多 skill 体系：

- `ui-ux-pro-max`：大范围设计 intelligence skill
- `design`：总路由/总编排 skill
- `brand`：品牌相关专项 skill
- `design-system`：design token 和规范专项 skill
- `slides`：演示文稿专项 skill
- `banner-design`：横幅广告与视觉素材专项 skill
- `ui-styling`：UI 实现与样式专项 skill

### 2.4 分发与安装层

相关目录：

- `cli/`
- `cli/assets/`

这层负责把源文件打包给 npm CLI 使用。

也就是说，这个项目并不只考虑“Claude 本地怎么读 skill”，还考虑：

- 用户如何安装
- 如何把 skill 内容变成 CLI 初始化模板
- 如何从源码目录同步到发布资产

这是很典型的“技能产品化”思路。

---

## 3. 它不是单 skill，而是 skill 平台

很多项目会把 skill 做成下面这种结构：

```text
my-skill/
  SKILL.md
  references/
  scripts/
```

而 `ui-ux-pro-max-skill-main` 更像：

```text
skill-product-repo/
  runtime-skills/
    skill-a/
    skill-b/
    skill-c/
  shared-source/
    data/
    scripts/
    templates/
  distribution/
    cli/
    marketplace/
```

这背后的思想变化非常重要：

- 单 skill 仓库：重点是“把一个任务做对”
- 多 skill 平台：重点是“把一组相关能力拆开、路由、复用、分发”

所以在看这个仓库时，不能只问“一个 skill 怎么写”，而要问：

- 总入口 skill 怎么设计
- 专项 skill 怎么分界
- 知识资产放在哪一层
- 执行能力如何复用
- 分发链路如何统一

---

## 4. 它是如何划分 skill 粒度的

这个仓库采用的是“多层粒度”的 skill 划分方式。

### 4.1 顶层广义能力 skill

代表：

- `.claude/skills/ui-ux-pro-max/SKILL.md`

这个 skill 的特点是：

- 描述范围很大
- 关键词覆盖很多
- 更偏向“设计智能入口”
- 携带大量规则、风格、产品类型、UX 检查项

它的作用更像：

- 作为总的 discoverability 入口
- 让模型在遇到广义 UI/UX 任务时容易命中

也就是说，它首先解决的是“被找到”的问题。

### 4.2 聚合型编排 skill

代表：

- `.claude/skills/design/SKILL.md`

这个 skill 的特点是：

- 不只处理一个窄任务
- 明确承担“分流器”职责
- 会把任务继续导向 `brand`、`design-system`、`ui-styling`、`slides`、`banner-design` 等

它更像一个 orchestration layer。

其中很关键的一份文件是：

- `.claude/skills/design/references/design-routing.md`

这份文件直接把“什么任务应该进哪个 skill”写成了显式路由表。这个做法非常工程化，因为它把本来隐含在作者脑子里的知识外显出来了。

### 4.3 专项 skill

代表：

- `brand`
- `design-system`
- `slides`
- `banner-design`
- `ui-styling`

这些 skill 的特点是：

- 主题边界相对清晰
- 每个 skill 内部再通过 `references/`、`scripts/`、`templates/` 组织知识
- `SKILL.md` 更像任务说明书和路由器，而不是百科全书

这类 skill 适合承载稳定领域能力。

---

## 5. SKILL.md 是如何充当“路由器”的

这个仓库非常值得学习的一点，是它没有把 `SKILL.md` 写成纯知识库，而是把 `SKILL.md` 写成“调度中心”。

### 5.1 `brand` skill 的模式

`brand/SKILL.md` 里有几个典型部分：

- When to Use
- Quick Start
- Subcommands
- References
- Scripts
- Templates
- Routing

它实际上在做下面这件事：

1. 告诉模型什么时候应该使用 `brand`
2. 告诉模型有哪些子任务，比如 `update`
3. 告诉模型应该去读哪些 `references/*.md`
4. 告诉模型有哪些脚本可以执行
5. 告诉模型执行时的路由顺序

也就是说，这个 `SKILL.md` 的作用不是承载所有品牌知识，而是把模型送到正确的知识文件和脚本。

### 5.2 `slides` skill 的模式

`slides/SKILL.md` 更薄，几乎是一个非常典型的“技能路由骨架”：

- 写明场景
- 列出子命令
- 列出知识库文件
- 明确 routing 步骤

这里能看到一个清晰模式：

```text
触发技能
  -> 解析子命令
  -> 加载对应 reference
  -> 结合剩余参数执行
```

这就是技能内部知识串联的标准套路。

### 5.3 `design` skill 的模式

`design` skill 则更进一步：

- 既自己包含内建能力
- 又把一部分任务转给其他专项 skill

这形成了两级路由：

```text
用户任务
  -> 进入 design
  -> 判断任务类型
  -> 内建处理 / 跳转到 brand / 跳转到 design-system / 跳转到 ui-styling
```

这说明 skill 不一定都要是“叶子节点”，也可以是编排节点。

---

## 6. 它如何组织知识库

这个项目并不是把“知识库”都堆在 Markdown 里，而是按知识类型拆分介质。

### 6.1 `references/` 负责规则、说明、示例

例如：

- `brand/references/*.md`
- `design-system/references/*.md`
- `slides/references/*.md`
- `ui-styling/references/*.md`

这里面的内容适合放：

- 规范
- 决策原则
- 使用说明
- 例子
- checklist

这是最接近传统“知识库”的部分。

### 6.2 `data/` 负责结构化知识

例如：

- `src/ui-ux-pro-max/data/products.csv`
- `src/ui-ux-pro-max/data/styles.csv`
- `src/ui-ux-pro-max/data/colors.csv`
- `src/ui-ux-pro-max/data/ux-guidelines.csv`

以及 `design-system/data/slide-*.csv`

这些不是给人逐段阅读的，而是给脚本检索和排序的。

这说明作者把知识分成了两类：

- 需要模型阅读理解的知识，放 `references/*.md`
- 需要程序搜索、匹配、打分的知识，放 `data/*.csv`

这是很成熟的设计。因为并不是所有知识都应该写成 Markdown。

### 6.3 `scripts/` 负责确定性执行

例如：

- `search.py`
- `design_system.py`
- `generate-tokens.cjs`
- `validate-tokens.cjs`
- `inject-brand-context.cjs`

脚本承担的是：

- 搜索
- 生成
- 校验
- 同步
- 注入上下文

这意味着这个项目不依赖模型“记住所有规则”，而是把可确定执行的部分交给脚本兜底。

### 6.4 `templates/` 负责起始结构

例如：

- `templates/base/`
- `templates/platforms/`
- `brand/templates/brand-guidelines-starter.md`
- `design-system/templates/design-tokens-starter.json`

模板的价值是：

- 降低每次从零开始生成的随机性
- 让产物结构更稳定
- 把最佳实践嵌入初始文件

---

## 7. 它如何把知识和执行串起来

这个问题是理解该项目的核心。

它不是简单的：

```text
SKILL.md 里写所有东西
```

而是：

```text
metadata -> SKILL.md -> references/scripts/data/templates
```

更细一点可以写成：

```text
1. 模型先根据 name/description 命中某个 skill
2. 读取该 skill 的 SKILL.md
3. SKILL.md 判断任务类型、子命令和路由
4. 按需读取 reference 文件
5. 按需调用 scripts
6. 必要时使用 data 做搜索/匹配
7. 必要时使用 templates 产出稳定结构
```

这其实就是 progressive disclosure 的工程化落地。

---

## 8. Source of Truth 设计非常关键

这个仓库里有一份很重要的说明文档：

- `docs/三个 data-scripts-templates 的区别.md`

它专门解释为什么会同时存在三处相似内容：

- `src/ui-ux-pro-max/`
- `.claude/skills/...`
- `cli/assets/...`

作者给出的答案非常清楚：

- 三处用途不同，不能简单删掉
- 但内容只维护一份即可
- 真正维护的只有 `src/ui-ux-pro-max/`
- `.claude` 运行时尽量通过符号链接复用
- `cli/assets` 只在发布前从 `src` 同步

这个设计解决了 skill 工程里的一个高频问题：**同一份知识在运行时、源码态、发布态如何避免漂移**。

对于中大型 skill 项目，这是必须认真设计的。

---

## 9. 从实现细节看，它在做两类复用

### 9.1 资产复用

典型例子：

- `.claude/skills/ui-ux-pro-max/data -> ../../../src/ui-ux-pro-max/data`
- `.claude/skills/ui-ux-pro-max/scripts -> ../../../src/ui-ux-pro-max/scripts`

也就是直接通过符号链接复用共享知识资产。

### 9.2 能力复用

典型例子：

- `design` skill 复用 `brand`、`design-system`、`ui-styling`
- `banner-design` 又会依赖 `ui-ux-pro-max`、`frontend-design`、`ai-artist`、`ai-multimodal`

也就是说，它不只是复用文件，还复用“技能之间的分工关系”。

这让整个 skill 体系更像一个 capability graph，而不是一堆彼此孤立的目录。

---

## 10. 这个仓库最值得学习的几个设计优点

### 10.1 Skill 边界有层次

不是所有任务都塞给一个超级 skill，也不是每个小知识点都拆成一个独立 skill。

它的分层是：

- 广义入口
- 编排入口
- 专项 skill
- 专项 knowledge files

这种层次化能兼顾 discoverability 和 maintainability。

### 10.2 知识介质选择合理

不是所有东西都写 Markdown：

- 规则用 `references`
- 检索知识用 `data`
- 确定性动作用 `scripts`
- 起始结构用 `templates`

这比单纯堆文档高效很多。

### 10.3 `SKILL.md` 不承担全部负担

很多 skill 写坏的原因是：把 `SKILL.md` 变成又长又乱的大百科。

这个项目里，比较成熟的 skill 都把 `SKILL.md` 写成：

- 触发说明
- 路由入口
- 快速用法
- 资源索引

这是更符合大模型加载机制的。

### 10.4 考虑了分发和发布

它不仅是“本地好用”，而且是“可安装、可打包、可发布”。

这意味着作者从一开始就把 skill 当作产品资产，而不是个人笔记。

### 10.5 显式写路由文档

`design/references/design-routing.md` 这种文件很有价值。

因为随着 skill 增多，最容易坏掉的不是某个 skill 内部逻辑，而是“到底该用哪个 skill”。

把路由规则外显出来，是非常有经验的做法。

---

## 11. 它也存在一些代价和问题

这个项目组织得很好，但也不是没有代价。

### 11.1 体系变复杂后，认知门槛上升

新维护者需要同时理解：

- 哪一层是源码真相
- 哪一层是运行时目录
- 哪一层是发布资产
- 哪个 skill 是总入口
- 哪个 skill 是专项技能

这明显比单 skill 项目复杂。

### 11.2 某些能力边界有重叠

例如：

- `ui-ux-pro-max`
- `design`
- `slides`
- `banner-design`

这些 skill 的主题都跟“设计”有关，边界并不是天然互斥的。

所以它必须额外用路由文档和 skill 内说明来约束，否则会出现：

- 漏触发
- 重复触发
- 描述重叠

### 11.3 聚合型 skill 容易再次膨胀

像 `design/SKILL.md` 这种聚合型 skill，如果持续把更多子领域往里加，很容易变成第二个“大而全说明书”。

这类 skill 后期需要强约束：

- 只保留入口和路由
- 把细节继续下沉到 references 或下级 skill

### 11.4 多副本分发需要纪律

虽然项目已经通过 source of truth + sync 减轻了漂移问题，但只要存在：

- `src`
- `.claude`
- `cli/assets`

三层分发，就必须维护同步纪律。

否则内容不一致几乎一定会发生。

---

## 12. 用这个案例反看 `local-api-self-test`

如果把这个案例映射到：

- `zl-base-business/tools/codex-skills/local-api-self-test`

可以得出一个很清晰的判断：

### 12.1 `local-api-self-test` 当前属于“单专项 skill”

它已经具备：

- `SKILL.md`
- `references/*.md`
- `scripts/*.sh`
- `tests/`

这说明它已经不是“只有一个说明文件”的初级状态，而是一个结构化专项 skill。

### 12.2 它还没有进入“skill 平台化”阶段

目前它没有：

- 多个并列 runtime skill
- 总路由 skill
- 共享的 source-of-truth 资产层
- 面向分发的 CLI/marketplace 结构

所以现阶段最自然的类比对象，不是整个 `ui-ux-pro-max-skill-main`，而是其中的一个专项 skill，比如：

- `slides`
- `brand`
- `design-system`

### 12.3 如果将来扩展，可以借鉴它的演进路径

可以按下面这个顺序演进：

1. 先把 `local-api-self-test` 继续保持为单专项 skill
2. 当出现第二个、第三个稳定专项能力时，再考虑并列 skill
3. 当专项 skill 足够多时，再新增一个总路由 skill
4. 当需要分发、安装、跨平台复用时，再考虑 source-of-truth + CLI + 发布清单

也就是说，不要一开始就照搬它的全部复杂度，而要借鉴它的演进方向。

---

## 13. 对 skill engineering 的具体启发

结合这个案例，可以总结出几条很有操作性的原则。

### 13.1 一个 skill 目录不等于一个 skill 体系

小规模项目：

- 一个 skill 目录就够

中等规模项目：

- 多个专项 skill + 一个聚合 skill

大规模技能产品：

- 运行时 skill 层
- 共享资产层
- 分发层
- 发布元数据层

### 13.2 先按“用户意图”拆 skill，再按“知识主题”拆 references

这点特别重要。

应该优先这样拆：

- `brand`
- `slides`
- `design-system`

而不是先拆成：

- `colors`
- `fonts`
- `layout`
- `animations`

前者是用户会表达的任务意图，后者更适合作为 skill 内部 reference 主题。

### 13.3 知识库不一定都该写成 Markdown

如果知识是：

- 稳定规则
- 示例
- 判断原则

用 Markdown 很合适。

如果知识是：

- 结构化候选项
- 检索数据
- 排序规则

CSV 或其他结构化数据更好。

### 13.4 聚合 skill 的职责是路由，不是替代子 skill

`design` 的做法说明：

- 聚合 skill 不应该吃掉所有内容
- 它最重要的职责是“识别任务类型并分流”

这是设计总 skill 时必须把握的边界。

### 13.5 source of truth 必须尽早明确

只要 skill 项目出现多份副本，必须尽早回答：

- 哪一份是唯一可编辑版本
- 其他副本如何生成
- 什么时候同步
- 如何验证一致性

否则后期维护会越来越痛苦。

---

## 14. 可以抽象出的通用模式

可以把这个项目抽象成一个通用组织模板：

```text
skill-product/
  skill.json
  plugin-manifest/
  runtime-skills/
    aggregator-skill/
    domain-skill-a/
    domain-skill-b/
    domain-skill-c/
  src/
    data/
    scripts/
    templates/
  cli/
    assets/
  docs/
    architecture-notes.md
    sync-rules.md
```

其中：

- `aggregator-skill/` 解决大范围 discoverability 和任务分流
- `domain-skill-*` 解决专项任务
- `src/` 解决共享真相来源
- `cli/assets/` 解决分发
- `docs/` 解决团队维护认知

---

## 15. 最终评价

`ui-ux-pro-max-skill-main` 的组织方式是一个比较成熟的技能工程案例。

它最有价值的不是“skill 内容很多”，而是它同时解决了下面几个问题：

- 如何让 skill 更容易被发现
- 如何把广义能力拆成多个专项能力
- 如何让 `SKILL.md` 只承担路由和编排职责
- 如何把知识分成 `references`、`data`、`scripts`、`templates`
- 如何避免源码、运行时目录、分发目录之间的知识漂移
- 如何让技能从“本地好用”走向“可安装、可发布、可维护”

对 skill engineering 学习来说，这个案例最值得模仿的不是它的 UI/UX 领域知识本身，而是它的工程组织方式。

如果一句话概括，可以写成：

**它把 skill 从“一个 Markdown 文件”升级成了“一个分层的能力产品系统”。**

---

## 16. 可直接复用的观察清单

以后分析其他 skill 项目时，可以直接用下面这份清单：

1. 它是单 skill，还是 skill 平台？
2. 是否有总入口 skill？是否有专项 skill？
3. `SKILL.md` 是百科全书，还是路由器？
4. 规则、数据、脚本、模板是否分介质存放？
5. 是否存在 source of truth？
6. 运行时目录和发布目录如何同步？
7. 是否有显式 routing 文档？
8. skill 的边界是按用户意图划分，还是按内部步骤划分？
9. 能否支持未来扩展为多 skill 体系？
10. 是否已经考虑安装、版本、分发和维护成本？

用这 10 个问题，基本就能判断一个 skill 项目的工程成熟度。
