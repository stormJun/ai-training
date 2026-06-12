# -*- coding: utf-8 -*-
# Converted from p06-5个特征.ipynb

# %% [markdown]
# 1. 领域语义精准映射

# %%
# 好的DSL：使用业务术语
risk_evaluation:
  customer_type: "premium"
  transaction_amount: "> 10000"
  risk_level: "medium"
  action: "manual_review"

# 坏的DSL：使用技术术语
if_condition:
  variable: "customer_tier"
  operator: "equals"
  value: 1
  then_execute: "function_call_risk_check"

# %% [markdown]
# 2. 语法简洁无冗余

# %%
# 好的DSL：简洁明了
approval_flow:
  - check_credit_score
  - if credit_score > 700:
      approve_immediately
  - else:
      manual_review

# 坏的DSL：过度复杂
approval_flow:
  steps:
    - step_id: "step_001"
      step_type: "validation"
      step_name: "check_credit_score"
      input_parameters:
        - param_name: "user_id"
          param_type: "string"
          param_source: "context.user_id"

# %% [markdown]
# 3. 可视化与文本双模式支持
#
# 优秀的DSL既支持文本编辑（便于版本控制），也支持可视化编辑（便于业务人员使用）。
#
# 4. 完善的错误反馈机制

# %%
错误示例：
 Syntax error at line 15
 在第15行：未找到必需的'action'字段。客服流程中的每个步骤都必须指定具体的执行动作。

# %% [markdown]
# 5. 无缝的系统集成能力
#
# DSL应该能够轻松调用现有的API和服务，而不需要复杂的适配层。
