# Coze可视化界面操作示例

## 用户看到的界面（拖拽操作）

```
┌─────────────────────────────────────────────────────────┐
│  Coze工作流编辑器                                        │
├─────────────────────────────────────────────────────────┤
│                                                         │
│   [开始节点]                                             │
│       ↓                                                 │
│   [LLM节点]  ← 用户用鼠标拖进来                           │
│   ┌─────────────────┐                                   │
│   │ 模型: GPT-4     │ ← 用户在表单中选择                  │
│   │ 提示词: [输入框]│ ← 用户在输入框中填写                 │
│   └─────────────────┘                                   │
│       ↓                                                 │
│   [条件判断]  ← 用户拖拽连线                              │
│   ┌─────────────────┐                                   │
│   │ 如果包含"退款" │ ← 用户在下拉菜单选择                  │
│   └─────────────────┘                                   │
│       ↓                                                 │
│   [API调用]                                             │
│                                                         │
│   [保存] [运行测试]                                      │
└─────────────────────────────────────────────────────────┘
```

## 用户体验

✅ 用户只需要：
1. 拖拽节点
2. 填写表单（选择、输入）
3. 连接节点
4. 点保存

❌ 用户**完全不需要**：
- 写代码
- 了解JSON语法
- 关心数据格式

---

## 后端自动生成的JSON（用户看不到）

当用户点击"保存"时，Coze前端自动生成JSON：

```json
{
  "workflow_id": "customer_service_001",
  "nodes": [
    {
      "id": "node_1",
      "type": "llm",
      "config": {
        "model": "gpt-4",
        "prompt": "分析用户意图"
      }
    },
    {
      "id": "node_2",
      "type": "condition",
      "config": {
        "field": "intent",
        "operator": "contains",
        "value": "退款"
      }
    },
    {
      "id": "node_3",
      "type": "api",
      "config": {
        "url": "https://api.company.com/refund",
        "method": "POST"
      }
    }
  ],
  "edges": [
    {"from": "node_1", "to": "node_2"},
    {"from": "node_2", "to": "node_3", "condition": "true"}
  ]
}
```

**关键点**：
- 这个JSON是**前端JavaScript代码自动生成的**
- 用户**永远不会看到**这段JSON
- 用户**永远不需要编辑**这段JSON

---

## 为什么Coze用JSON就够了？

### 原因1：机器生成，不需要人类可读

```javascript
// Coze前端代码（机器生成JSON）
function saveWorkflow() {
  const json = {
    nodes: nodes.map(node => ({
      id: node.id,
      type: node.type,
      config: node.config
    })),
    edges: edges.map(edge => ({
      from: edge.source,
      to: edge.target
    }))
  };

  // 发送到后端
  fetch('/api/workflow', {
    method: 'POST',
    body: JSON.stringify(json)
  });
}
```

✅ 前端代码保证了JSON格式100%正确
✅ 用户不会写错语法（因为是拖拽生成）
✅ 不需要Lark这样的解析器

### 原因2：表单验证就能保证正确性

用户在界面上填写时，前端已经做了验证：

```javascript
// Coze前端表单验证
<input
  type="text"
  placeholder="请输入API地址"
  pattern="https?://.*"  // 自动验证URL格式
  required                // 必填项
/>

<select name="model">
  <option value="gpt-4">GPT-4</option>
  <option value="gpt-3.5">GPT-3.5</option>
  <!-- 用户只能选择有效的模型，不会输入错误 -->
</select>
```

❌ 不需要验证JSON语法（前端自动生成，肯定正确）
❌ 不需要验证单位（表单控件已经限定了输入类型）

### 原因3：容错率高，出错影响小

即使用户配置错误（比如写错API地址），也只是：
- ⚠️ 对话流程失败
- ⚠️ 返回错误消息给用户
- ⚠️ 用户重新配置即可

**不会造成资金损失或安全事故**

---

## 对比：Dify也用JSON的原理

Dify和Coze一样，都是**低代码可视化平台**：

```
用户操作         Dify/Coze内部          后端存储
┌────────┐      ┌──────────┐         ┌────────┐
│拖拽节点│ -->  │生成JSON  │  -->    │数据库  │
│填表单  │      │(前端代码)│         │        │
│连线    │      └──────────┘         └────────┘
└────────┘
```

**关键**：JSON只是**内部数据格式**，用户看不到也不需要关心
