# ralph_demo.py 设计文档

## 1. 目标

`ralph_demo.py` 用一个最小可运行的 Python 示例演示 Ralph 风格的多角色编码工作流：

- 任务由多个角色协作完成，而不是一个 Agent 一次性完成。
- 每个角色职责固定：`Planner`、`Builder`、`Critic`、`Finalizer`。
- 协作上下文只通过 `scratchpad.md` 传递，不依赖 Agent 历史记忆。
- Builder 必须遵守 TDD：先写测试，再写最小实现，再运行验证。
- 主循环有明确上限：`MAX_ITERATIONS = 6`，防止无限循环。

本 demo 优先做成离线、确定性、可测试的教学版本。角色逻辑先用普通 Python 函数模拟，后续可以把角色函数替换成真实 LLM 调用。

## 2. 核心概念

### 2.1 迭代与角色阶段

建议把“4 轮迭代”理解为“每个迭代周期包含 4 个角色阶段”：

1. `Planner`：读取目标和当前上下文，拆解下一步任务。
2. `Builder`：按 Planner 指令执行 TDD 开发。
3. `Critic`：独立审查测试、实现和 scratchpad 记录。
4. `Finalizer`：判断目标是否完成，完成则写入结束标志。

外层循环最多执行 6 个迭代周期：

```python
MAX_ITERATIONS = 6

for iteration in range(1, MAX_ITERATIONS + 1):
    run_planner()
    run_builder()
    run_critic()
    run_finalizer()

    if is_done():
        break
```

这样可以同时保留“四角色轮转”和“最大 6 次迭代”的约束。

### 2.2 scratchpad.md

`scratchpad.md` 是唯一共享上下文。每个角色运行前都重新读取它，运行后追加自己的输出。

文件建议包含以下区域：

```markdown
# Ralph Scratchpad

## Goal
用户目标。

## Current Status
当前状态，例如 planning / building / review_needed / done。

## Plan
Planner 写入的任务拆解。

## TDD Log
Builder 写入的测试、实现、验证记录。

## Review
Critic 写入的问题、建议和结论。

## Finalizer
Finalizer 写入完成判断。

## Done Marker
未完成为空；完成时写入 FINAL_DONE。
```

## 3. 角色职责

### 3.1 Planner

职责：

- 把用户目标拆成小步骤。
- 每轮只安排一个具体、可验证的动作。
- 计划中必须显式包含 TDD 步骤。

Planner 输出示例：

```markdown
### Planner - iteration 1
Next task: implement add(a, b).
TDD steps:
1. Add a failing test for add(1, 2) == 3.
2. Implement the smallest code that passes.
3. Run tests and record the result.
```

### 3.2 Builder

职责：

- 严格按 TDD 执行。
- 先创建或更新测试，再创建或更新实现。
- 运行测试并把结果写回 `scratchpad.md`。
- 每轮只完成 Planner 指定的一个动作。

Builder 不应该绕过测试直接写完整实现。

### 3.3 Critic

职责：

- 检查 Builder 是否真的先写测试。
- 检查测试是否覆盖 Planner 指定的行为。
- 检查实现是否过度复杂、是否与目标不一致。
- 给出 `approved` 或 `changes_requested`。

Critic 只做审查，不直接改代码。

### 3.4 Finalizer

职责：

- 检查目标、计划、测试结果和 Critic 结论。
- 只有在所有目标完成、测试通过、Critic 通过后，才写入：

```markdown
FINAL_DONE
```

- 如果未完成，说明下一轮应该继续处理什么。

## 4. 文件结构

建议目录结构：

```text
ralph_demo/
  DESIGN.md
  ralph_demo.py
  scratchpad.md
  demo_workspace/
    target.py
    test_target.py
```

说明：

- `ralph_demo.py`：主程序和四个角色函数。
- `scratchpad.md`：运行时共享上下文，可删除后重新运行。
- `demo_workspace/target.py`：Builder 要实现的目标代码。
- `demo_workspace/test_target.py`：Builder 先写入的测试。

如果只想做最小版本，也可以让 `ralph_demo.py` 在首次运行时自动创建 `demo_workspace/`。

## 5. 主流程设计

### 5.1 启动

CLI 默认命令：

```bash
python ralph_demo.py "实现一个 add(a, b) 函数"
```

启动后：

1. 如果 `scratchpad.md` 不存在，创建它并写入用户目标。
2. 如果 `scratchpad.md` 已存在，读取现有进度并继续。
3. 进入最多 6 次的角色轮转。

### 5.2 单轮迭代

每轮执行：

```text
读取 scratchpad.md
Planner 追加下一步计划

重新读取 scratchpad.md
Builder 追加 TDD 执行记录，并修改 demo_workspace 文件

重新读取 scratchpad.md
Critic 追加审查结论

重新读取 scratchpad.md
Finalizer 追加完成判断
```

重点是每个角色都只依赖文件内容，模拟“无记忆 Agent”的协作方式。

### 5.3 结束条件

满足任一条件即退出：

- `scratchpad.md` 包含 `FINAL_DONE`。
- 达到 `MAX_ITERATIONS = 6`。
- 出现不可恢复错误，例如测试命令无法执行。

退出时打印：

```text
status: done | max_iterations_reached | failed
scratchpad: /path/to/scratchpad.md
```

## 6. TDD 约束

Builder 的行为必须满足：

1. 没有测试文件时，先写测试文件。
2. 测试失败后，才写实现。
3. 实现后必须运行测试。
4. 测试结果必须记录到 `scratchpad.md`。

demo 版可以用简单规则保证 TDD：

- 第一次 Builder 执行只写 `test_target.py`。
- 第二次 Builder 执行才写 `target.py`。
- 后续 Builder 执行运行 `python -m pytest demo_workspace` 或内置 `unittest`。

为了降低依赖，最小版本建议使用 Python 标准库 `unittest`，不强制依赖 `pytest`。

## 7. 错误处理

需要处理的错误：

- `scratchpad.md` 缺失：自动初始化。
- `demo_workspace/` 缺失：自动创建。
- 测试失败：记录失败结果，不直接终止，让 Critic 和 Finalizer 决定下一轮。
- 达到最大迭代次数仍未完成：退出并提示查看 `scratchpad.md`。

## 8. 测试策略

`ralph_demo.py` 自身应至少覆盖：

- 初始化 scratchpad。
- Planner 输出包含 TDD 步骤。
- Builder 先写测试，再写实现。
- Critic 能识别通过和未通过状态。
- Finalizer 只在测试通过且 Critic approved 后写入 `FINAL_DONE`。
- 主循环在 `MAX_ITERATIONS` 内正常退出。

测试可以放在：

```text
ralph_demo/
  tests/
    test_ralph_demo.py
```

## 9. 后续扩展

第一版不接真实模型。等本地确定性流程稳定后，再扩展：

- 增加 `AgentBackend` 接口。
- 默认实现为 `RuleBasedBackend`。
- 可选实现为 `LLMBackend`。
- 四个角色仍然只读写 `scratchpad.md`，不直接共享内存状态。

这样可以保证教学 demo 的核心不变：角色分工、TDD、文件上下文、有限迭代。

