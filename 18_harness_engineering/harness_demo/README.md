# Harness Engineering CLI Demo

这个 demo 用一个最小 Python CLI 演示 Harness Engineering 的核心想法：不要只让 agent "跑一下"，而是给它一个能持续推进、能中断恢复、能留下证据的执行环境。

它不调用真实大模型，也不依赖第三方包。脚本会模拟一个 agent 任务，并把可恢复状态写入本地 workspace。

## 演示内容

- `progress.json`: 当前完成了哪些阶段，下一个阶段是什么
- `progress.log`: 每个阶段开始和完成的时间线
- `decision.log`: 关键决策记录
- `artifacts/validation.txt`: 验证证据
- `verdict.json`: 最终通过/失败结论，以及证据路径

默认任务包含四个阶段：

1. `read_plan`: 读取任务目标并写入计划快照
2. `draft_change`: 模拟生成一个小改动，并记录设计决策
3. `run_validation`: 模拟验证并写入证据
4. `write_verdict`: 生成最终 `verdict.json`

## 快速运行

从仓库根目录执行：

```bash
python3 19_harness_engineering/harness_demo/harness_demo.py run \
  --workspace 19_harness_engineering/harness_demo/runs/demo-task
```

完成后查看 verdict：

```bash
cat 19_harness_engineering/harness_demo/runs/demo-task/verdict.json
```

预期能看到：

```json
{
  "status": "pass",
  "resume_supported": true
}
```

实际文件里还会包含每一项检查和证据路径。

## 模拟中断和恢复

先让任务在完成两个阶段后停下：

```bash
python3 19_harness_engineering/harness_demo/harness_demo.py run \
  --workspace 19_harness_engineering/harness_demo/runs/interrupted-task \
  --stop-after 2
```

这个命令会返回非零退出码，并写入：

```text
Simulated interruption after 2 stage(s)
```

查看保存下来的状态：

```bash
python3 19_harness_engineering/harness_demo/harness_demo.py status \
  --workspace 19_harness_engineering/harness_demo/runs/interrupted-task
```

预期输出类似：

```text
status: interrupted
completed_stages: read_plan, draft_change
next_stage: run_validation
```

再次运行同一个 workspace，脚本会从 `run_validation` 继续：

```bash
python3 19_harness_engineering/harness_demo/harness_demo.py run \
  --workspace 19_harness_engineering/harness_demo/runs/interrupted-task
```

预期输出包含：

```text
Resuming from stage: run_validation
Verdict: pass
```

## 运行测试

```bash
python3 -m pytest 19_harness_engineering/harness_demo/tests -q
```

这些测试覆盖三件事：

- 中断后会留下可恢复状态
- 重新运行会从下一个阶段继续，并生成通过的 verdict
- `status` 命令能读出当前状态

## 课堂讨论点

- `progress.json` 相当于可版本化、可恢复的上下文。
- `decision.log` 让后续 agent 或人类知道为什么这样做。
- `verdict.json` 把"跑完了"升级成"有证据地通过了"。
- `--stop-after` 演示长任务中 session 中断不是异常路径，而是应该被设计进去的正常路径。
