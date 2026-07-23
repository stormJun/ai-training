<!-- Converted from p03-mcpVS.DSL.ipynb -->

```python
def handle_refund_request(user_input, context):
    if "退款" in user_input:
        order_id = extract_order_id(user_input)
        if not order_id:
            return "请提供订单号"

        order = get_order_details(order_id)
        if order.status != "delivered":
            return "订单未发货，无法退款"

        if days_since_delivery(order) > 30:
            return "超过30天退款期限"

        if order.category == "digital":
            return "数字商品不支持退款"

        # 执行退款逻辑...
        process_refund(order_id)
        return "退款申请已提交"
```

这种方式的问题：

- 业务规则变更需要修改代码：退款期限从30天改为15天，需要开发人员修改代码并重新部署
- 业务人员无法直接参与：客服主管想调整流程，必须通过开发人员
- 测试和维护成本高：每次修改都要重新测试整个系统

```python
# 退款流程DSL
refund_workflow:
  name: "客服退款处理流程"

  steps:
    - step: "收集订单信息"
      type: "slot_filling"
      slot: "order_id"
      prompt: "请提供您的订单号"
      validation: "regex:^ORD[0-9]{8}$"

    - step: "验证退款条件"
      type: "business_rules"
      rules:
        - condition: "order.status == 'delivered'"
          error_message: "订单未发货，无法退款"
        - condition: "days_since_delivery <= 30"
          error_message: "超过30天退款期限"
        - condition: "order.category != 'digital'"
          error_message: "数字商品不支持退款"

    - step: "执行退款"
      type: "api_call"
      service: "payment_service"
      method: "process_refund"
      params:
        order_id: "${context.order_id}"
```

这样的DSL描述带来了根本性的改变：

- 业务人员可以直接修改：退款期限调整只需要改配置文件
- 即时生效：无需重新编译和部署
- 可视化编辑：可以开发图形化界面让业务人员操作
- 版本控制：业务规则的变更历史一目了然
