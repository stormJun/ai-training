# Root Reinforcement Learning Notes Design

## Goal

在仓库根目录新增一个独立的强化学习学习笔记目录，提供一份系统化、可独立阅读的 Markdown 文档，帮助读者从基础概念逐步进入 MDP、Q-Learning、Policy Gradient 和 Actor-Critic。

## Scope

本设计仅覆盖以下新增内容：

- 根目录新建 `22_reinforcement_learning_notes/`
- 在该目录下新增 `README.md`
- 文档采用中文撰写，风格为系统学习笔记

本设计不会替换或重组现有的强化学习专题目录 `17_model_extensions/03_reinforcement_learning/`，两者并行存在。

## Target Structure

完成后，仓库根目录将新增：

- `22_reinforcement_learning_notes/`
- `22_reinforcement_learning_notes/README.md`

## Design Decisions

### 1. 使用根目录独立目录，而不是复用现有 55 号主题目录

仓库已经存在 `17_model_extensions/03_reinforcement_learning/`，但用户明确要求在仓库根目录下再创建一个全新的独立目录。因此本次新增文档将作为一个单独入口存在，不修改既有专题资料结构。

### 2. 使用单文件 `README.md` 作为入口文档

本任务的目标是先落地一份可直接阅读的强化学习文档，而不是扩展成一个多文件教程站点。使用 `README.md` 有三个好处：

- 打开目录即可阅读
- 结构简单，后续易于继续拆分
- 便于与仓库中其他主题目录保持一致

### 3. 内容结构采用“概念到算法递进式”

文档顺序将从“强化学习是什么”开始，逐步推进到：

- 核心概念
- MDP
- 回报、价值函数、贝尔曼方程
- Q-Learning
- Policy Gradient
- Actor-Critic
- 典型应用与后续学习路径

这种组织方式比纯公式堆叠更适合独立学习文档，也比纯故事化说明更利于复习检索。

### 4. 公式深度控制在“理解原理”层级

文档会保留关键公式，包括：

- 回报 `G_t`
- 状态价值函数 `V^\pi(s)`
- 动作价值函数 `Q^\pi(s, a)`
- 贝尔曼期望方程与最优方程
- Q-Learning 更新公式
- Policy Gradient 基本目标与梯度表达
- Actor-Critic 的 TD 误差更新思路

但不会展开完整数学证明，也不会深入到 measure theory、收敛性证明或复杂变体推导。

### 5. 补充与大模型训练的关系，但不把文档改写成 RLHF 专题

为了让学习路径更完整，文档会用一个短节说明强化学习与大模型对齐训练的关系，例如 PPO、RLHF 的位置。但这部分仅作连接说明，不作为主线内容展开。

## Content Outline

`22_reinforcement_learning_notes/README.md` 将至少包含以下部分：

1. 强化学习的定义与直觉
2. 强化学习与监督学习的差异
3. Agent、Environment、State、Action、Reward、Policy、Value 等核心概念
4. MDP 五元组与马尔可夫性质
5. 回报、折扣因子、状态价值、动作价值
6. 贝尔曼方程与最优性思想
7. Q-Learning 的核心思想、更新公式、优缺点
8. Policy Gradient 的动机、目标函数与基本梯度形式
9. Actor-Critic 的协作机制与稳定性来源
10. 强化学习的应用场景
11. 后续学习路线建议

## Risks

### 1. 与现有强化学习资料产生重复

仓库已有 `17_model_extensions/03_reinforcement_learning/`。本次新增文档需要明确定位为“独立系统学习入口”，而不是重复搬运已有文件。

### 2. 公式密度过高导致阅读负担增加

如果公式堆叠过多，文档会失去入门可读性。因此每个公式后都需要配简明解释，优先建立含义理解，再提数学表达。

### 3. 范围膨胀

如果继续展开 DQN、PPO、SAC、DDPG、TRPO 等变体，文档很快会超出“系统学习版基础主线”的范围。本次设计显式限制在 Q-Learning、Policy Gradient 和 Actor-Critic。

## Testing and Verification

这是一次文档型变更，验证方式以结构与内容检查为主：

1. 确认 `22_reinforcement_learning_notes/README.md` 已创建。
2. 确认文档包含 MDP、Q-Learning、Policy Gradient、Actor-Critic 等目标章节。
3. 确认文档中没有 `TODO`、`TBD` 或明显占位内容。
4. 确认现有 `17_model_extensions/03_reinforcement_learning/` 未被改动。

## Out of Scope

以下内容明确不在本次范围内：

- 新增强化学习代码示例或训练脚本
- 重构现有 `03_reinforcement_learning/` 目录
- 深入讲解 DQN、PPO、SAC、DDPG、TRPO 等高级算法
- 将文档拆分为多篇系列文章
