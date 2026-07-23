# -*- coding: utf-8 -*-
# Converted from p05-interVS.exterl.ipynb

# %%
# 使用Python构建的工作流DSL
workflow = (
    WorkflowBuilder()
    .add_step("validate_input", validate_user_input)
    .add_step("process_data", process_business_data)
    .add_condition("data_valid", lambda ctx: ctx.validation_result)
    .add_step("send_notification", send_success_notification)
    .build()
)

# %% [markdown]
# 优势：开发成本低，可以复用宿主语言的工具链
#
# 劣势：受宿主语言语法限制，业务人员难以直接理解

# %%
# 客服对话流程DSL
conversation_flow:
  name: "customer_service_flow"

  triggers:
    - intent: "greeting"
      response: "您好！我是智能客服，有什么可以帮您的？"

    - intent: "refund_request"
      conditions:
        - check: "order_exists"
        - check: "order_refundable"
      actions:
        - type: "api_call"
          service: "payment_service"
          method: "process_refund"
        - type: "send_message"
          template: "refund_success"

# %% [markdown]
# 优势：语法完全自定义，业务人员可以直接理解和修改
#
# 劣势：需要开发专门的解析器，开发成本相对较高
