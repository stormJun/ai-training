# -*- coding: utf-8 -*-
# Converted from p07-常见场景.ipynb

# %% [markdown]
# 1. 客服流程编排：工作流DSL

# %%
# 智能客服退款流程DSL
workflow:
  name: "智能客服退款流程"

  nodes:
    - id: "start"
      type: "start"
      data:
        title: "开始"

    - id: "intent_recognition"
      type: "llm"
      data:
        title: "意图识别"
        model: "gpt-3.5-turbo"
        prompt: "分析用户意图：${#start.user_input#}"
        variables:
          - name: "intent"
            type: "string"

    - id: "condition_check"
      type: "if_else"
      data:
        title: "退款条件检查"
        conditions:
          - variable: "${#intent_recognition.intent#}"
            comparison_operator: "contains"
            value: "退款"
        logical_operator: "and"

    - id: "order_validation"
      type: "http_request"
      data:
        title: "订单验证"
        method: "GET"
        url: "https://api.company.com/orders/${order_id}"
        headers:
          Authorization: "Bearer ${api_token}"

    - id: "process_refund"
      type: "http_request"
      data:
        title: "处理退款"
        method: "POST"
        url: "https://api.company.com/refunds"
        body:
          order_id: "${order_id}"
          reason: "${refund_reason}"

  edges:
    - source: "start"
      target: "intent_recognition"
    - source: "intent_recognition"
      target: "condition_check"
    - source: "condition_check"
      target: "order_validation"
      condition: "true"
    - source: "order_validation"
      target: "process_refund"

# %% [markdown]
# 2. 风控审批流程：动态规则引擎

# %%
# 风控规则DSL（简化版）
risk_rules:
  - name: "高额交易检查"
    priority: 1
    condition: "amount > 50000 AND account_age < 180"
    action: "manual_review"
    reason: "新账户大额交易需人工审核"

  - name: "异地交易检查"
    priority: 2
    condition: "location NOT IN user.frequent_locations AND amount > 10000"
    action: "sms_verification"
    reason: "异地大额交易需短信验证"

  - name: "信用评分检查"
    priority: 3
    condition: "credit_score < 600"
    action: "reject"
    reason: "信用评分过低"

decision_flow:
  - evaluate_all_rules
  - if any_rule_triggered:
      execute_corresponding_action
  - else:
      auto_approve

# %% [markdown]
# 3. 多Agent协作调度：标准化任务编排

# %%
# 多Agent协作DSL核心结构
multi_agent_workflow:
  agents:
    - name: "document_analyzer"
      max_concurrent: 3
      timeout: 300
    - name: "risk_evaluator"
      max_concurrent: 2
      timeout: 240

  tasks:
    - stage: "parallel_analysis"
      type: "parallel"
      tasks:
        - agent: "document_analyzer"
          task: "extract_info"
        - agent: "document_analyzer"
          task: "verify_authenticity"

    - stage: "risk_assessment"
      type: "sequential"
      depends_on: ["parallel_analysis"]
      tasks:
        - agent: "risk_evaluator"
          task: "calculate_risk"
          input: "${parallel_analysis.results}"

# %% [markdown]
# 其他案例

# %%
# 腾讯云智能体DSL示例
intelligent_agent:
  mode: "standard"
  rag_config:
    knowledge_base: "enterprise_docs"
    retrieval_strategy: "hybrid_search"
    text2sql_enabled: true
    response_template: "基于文档${doc_name}，答案是：${answer}"

# %%
multi_agent_workflow:
  agents:
    - name: "document_processor"
      type: "nlp_agent"
      capabilities: ["text_extraction", "entity_recognition"]
    - name: "business_analyzer"
      type: "rule_engine"
      capabilities: ["risk_assessment", "decision_making"]

  collaboration_flow:
    - stage: "parallel_processing"
      agents: ["document_processor", "business_analyzer"]
    - stage: "result_integration"
      coordinator: "business_analyzer"
