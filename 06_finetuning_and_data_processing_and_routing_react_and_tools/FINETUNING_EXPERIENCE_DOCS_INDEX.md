# 微调经验总结类文档清单

本清单整理 `ModelOps Platform` 项目里偏“经验总结 / 根因分析 / 案例复盘 / 排障方法”的文档，方便后续统一查找。

## 原始项目目录

- 主项目目录：`/Users/songxijun/workspace/modelops-platform-main`
- 兼容旧路径：`/Users/songxijun/workspace/hailinpython2`
  - 这是一个软链接，指向 `modelops-platform-main`
- 历史备份目录：`/Users/songxijun/workspace/modelops-platform-backup`
  - 兼容旧路径：`/Users/songxijun/workspace/hailinpython2_bak`

## 原始文档主目录

- 主要来源：`/Users/songxijun/workspace/modelops-platform-main/docs/1.1/modelops/technical`

## 核心经验文档

### 1. 微调问题根因分析（任务23）

- 原始文件：
  `/Users/songxijun/workspace/modelops-platform-main/docs/1.1/modelops/technical/FINE_TUNING_ROOT_CAUSE_ANALYSIS.md`
- 类型：根因分析 / 经验总结
- 重点内容：
  - 任务23的错误分布和问题回顾
  - 训练与评估 prompt 格式不一致的代码级问题
  - 微调前三阶段分析：数据、训练参数、后处理
  - 优先级排序、行动计划、SQL 排查速查

### 2. 微调问题根因分析（任务27）

- 原始文件：
  `/Users/songxijun/workspace/modelops-platform-main/docs/1.1/modelops/technical/FINE_TUNING_ROOT_CAUSE_ANALYSIS_TASK27.md`
- 类型：根因分析 / 经验总结
- 重点内容：
  - 任务27的评估结果和错误明细抽样
  - 高频意图混淆对
  - 槽位口径冲突和数据规范问题
  - 优先修复项与数据侧建议

### 3. 任务23错误案例详细分析

- 原始文件：
  `/Users/songxijun/workspace/modelops-platform-main/docs/1.1/modelops/technical/TASK23_ERROR_CASE_STUDY.md`
- 类型：案例复盘
- 重点内容：
  - 错误类型分布
  - 意图错误分析
  - 槽位错误模式分析
  - 逐条错误样本复盘

### 4. 评估结果错误样本分析

- 原始文件：
  `/Users/songxijun/workspace/modelops-platform-main/docs/1.1/modelops/technical/EVALUATION_ERROR_ANALYSIS.md`
- 类型：排障总结 / 分析方法
- 重点内容：
  - `fine_tune_evaluations` 与 `fine_tune_evaluation_errors` 的数据流
  - 错误类型判定规则
  - 常用 SQL 分析方式
  - 前端展示和模型迭代联动方式

### 5. Prompt 格式统一修复

- 原始文件：
  `/Users/songxijun/workspace/modelops-platform-main/docs/1.1/modelops/technical/PROMPT_FORMAT_UNIFICATION.md`
- 类型：问题修复复盘
- 重点内容：
  - 训练与评估 prompt 格式不一致的发现过程
  - 后端和前端统一修改方案
  - 风险、验证步骤和预期收益

## 次级经验文档

### 6. AutoDL 混合运行实现说明

- 原始文件：
  `/Users/songxijun/workspace/modelops-platform-main/docs/AUTODL_MIXED_MODE_ARCHITECTURE.md`
- 类型：架构经验总结
- 重点内容：
  - 本地网关 + AutoDL 前缀代理
  - 回退策略
  - 运行前提和限制

### 7. 部署运维指南

- 原始文件：
  `/Users/songxijun/workspace/modelops-platform-main/docs/1.1/modelops/technical/DEPLOYMENT_OPS_GUIDE.md`
- 类型：运维经验 / 操作手册
- 重点内容：
  - 启停方式
  - 目录和依赖关系
  - 排障顺序
  - 常见部署问题

### 8. Badcase Repair Loop / LoRA Patch

- 原始文件：
  `/Users/songxijun/workspace/modelops-platform-main/docs/1.2/architecture/BADCASE_REPAIR_LOOP_LORA_PATCH.md`
- 类型：修复思路总结
- 重点内容：
  - badcase 修复闭环
  - LoRA patch 方案
  - 适用范围和限制

## 推荐阅读顺序

1. 先看 `FINE_TUNING_ROOT_CAUSE_ANALYSIS.md`
2. 再看 `TASK23_ERROR_CASE_STUDY.md`
3. 然后看 `EVALUATION_ERROR_ANALYSIS.md`
4. 如果要看另一轮经验沉淀，再看 `FINE_TUNING_ROOT_CAUSE_ANALYSIS_TASK27.md`
5. 如果关注代码问题修复，再看 `PROMPT_FORMAT_UNIFICATION.md`

## 备注

- 如果你要找“最像 `FINE_TUNING_ROOT_CAUSE_ANALYSIS.docx` 的文档”，优先看：
  `FINE_TUNING_ROOT_CAUSE_ANALYSIS.md`
- 如果你要找“模型微调过程中的经验沉淀”，核心仍然集中在：
  `/Users/songxijun/workspace/modelops-platform-main/docs/1.1/modelops/technical`
