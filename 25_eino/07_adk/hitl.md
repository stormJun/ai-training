# HITL 人机交互(Interrupt/Resume)

> 源码: `/Users/songxijun/workspace/otherProject/eino/adk/interrupt.go`
> HITL = Human-In-The-Loop，就是让人类能介入 Agent 执行过程，需要批准才能继续，适合审批场景。

## 一、概述

Eino 编排层已经支持[中断恢复](../03_graph/interrupt_resume.md)，ADK 在这之上封装了更易用的 HITL 接口:
- 运行到需要人工批准的地方停下来
- 保存检查点
- 人类批准后，从检查点恢复继续跑

## 二、怎么用

在你的 Agent 里，工具执行前需要人工批准，你只要 `adk.Hitl` 包装一下:

```go
agent, err := adk.NewChatModelAgent(ctx, &adk.ChatModelAgentConfig{
	// ...
})

// 包装支持 HITL
hitlAgent := adk.NewHITL(agent, adk.HitlConfig{
	// Before each tool call, interrupt for approval
	InterruptBeforeTool: true,
})
```

## 三、运行一次需要批准的

```go
runner := adk.NewRunner(hitlAgent)
iter := runner.Query(ctx, input)

for {
	event, ok := iter.Next()
	if !ok {
		break
	}
	if event.Err != nil {
		// handle error
		break
	}

	if event.IsInterrupt() {
		// 需要人工批准，保存 checkpoint，拿到 interrupt info
		info := event.GetInterruptInfo()
		// 告诉你哪个工具要批准
		fmt.Printf("need approve: tool %s\n", info.ToolName)
		// 你保存 checkpoint ID，让用户批准之后再来恢复
		checkpointID := info.CheckpointID
		break
	}

	// handle event message
}
```

## 四、恢复执行

用户批准后，你拿着 `checkpointID` + 批准了，恢复:

```go
resumer := adk.NewResumer(hitlAgent, checkpointID, adk.ResumeConfig{
	Approved: true, // 批准继续，拒绝就是 stop
})

iter := resumer.Resume(ctx)
// 继续跑，和正常 Query 一样迭代事件
```

## 五、哪里中断

配置告诉你什么时候中断:

```go
hitlConfig := adk.HitlConfig{
	// 工具执行前中断，需要用户批准才执行工具
	InterruptBeforeTool: true,

	// 工具执行后中断，需要用户批准结果才继续
	InterruptAfterTool: false,
}
```

常用:
- `InterruptBeforeTool: true` —— 工具执行要批准，批准错了可以不执行，安全
- `InterruptAfterTool: true` —— 工具执行完结果要批准，结果错了你可以不让继续

## 六、小结

- Eino 编排层已经支持检查点中断恢复，ADK 封装成简单 API
- 你只要配置在哪中断，框架处理保存检查点、恢复执行
- 适合需要人工审批的生产场景，比如删除文件需要审批

## 参考

- 编排层中断恢复: [../03_graph/interrupt_resume.md](../03_graph/interrupt_resume.md)
