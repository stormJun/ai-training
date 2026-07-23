# 预置智能体

> Eino ADK 预置了几种常用的智能体，开箱即用。

## 一、ChatModelAgent

就是咱们说的 [ChatModelAgent](./chatmodel_agent.md)，最常用的，**单 Agent 带工具调用**，开箱即用。

## 二、Plan-and-Execute

`adk/prebuilt/planexecute` —— 先规划再执行重规划，就是 Plan-and-Execute 模式。

### 设计思想

```
Planner → 出计划 → 循环: Executor执行一步 → Replanner看要不要继续 → 直到结束
```

- Planner 把用户问题拆成多步
- 每步 Executor 执行，执行完 Replanner 看要不要继续，不继续就产出最终答案

适合**长任务分解**，比 ReAct 一步一步思考更清晰。

我们已经帮你拼好图了，你直接用:

```go
import "github.com/cloudwego/eino/adk/prebuilt/planexecute"

agent, err := planexecute.New(ctx, &planexecute.Config{
	Planner:   planner,
	Executor:  executor,
	Replanner: replanner,
})
```

默认实现已经帮你拼好了拓扑，底层还是 Pregel 图，你要改可以导出图自己改。

详细设计见 [../03_graph/planexecute_design.md](../03_graph/planexecute_design.md) 我们早就写好设计了。

## 三、DeepAgent

`adk/prebuilt/deep` —— 深度智能体，更复杂的任务分解，动态规划，适合复杂任务。

## 四、Supervisor（多智能体协作）

`adk/prebuilt/supervisor` —— Supervisor 管理多个子智能体，分工协作完成任务。

- Supervisor 做计划
- 每个子智能体负责一个领域
- Supervisor 汇总结果

适合复杂问题分工解决，每个人做自己擅长的。

## 总结

| 预置智能体 | 适用场景 |
|----------|----------|
| ChatModelAgent | 单智能体工具调用，大多数场景 |
| Plan-and-Execute | 长任务分解，分步执行 |
| DeepAgent | 复杂深度任务分解 |
| Supervisor | 多智能体分工协作 |

大部分场景你只用 `ChatModelAgent` 就够了，需要更强任务分解再用 Plan-and-Execute 或 DeepAgent，复杂多领域分工用 Supervisor。
