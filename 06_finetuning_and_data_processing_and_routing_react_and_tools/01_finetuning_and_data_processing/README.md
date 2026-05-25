# 微调与数据处理专题

本父目录合并了原来的 `01_finetuning_overview/`、`02_massive_dataset_processing/`、`03_lora_qlora_training/` 和 `04_local_finetuning_platform/`，目的是减少仓库顶层目录数量，同时保留各主题原本的工作区结构。

## 子目录

- `01_finetuning_overview/`
  - 微调概览、依赖锚点、入门说明
- `02_massive_dataset_processing/`
  - MASSIVE 数据抽取、转换、评估与中文数据说明
- `03_lora_qlora_training/`
  - LoRA / QLoRA 训练结果与 checkpoint 产物
- `04_local_finetuning_platform/`
  - 本地微调平台与界面化训练流程

## 建议学习顺序

1. 先看 `01_finetuning_overview/`
2. 再看 `02_massive_dataset_processing/`
3. 然后查看 `03_lora_qlora_training/`
4. 最后进入 `04_local_finetuning_platform/`

## 说明

- 该父目录只做聚合，不拆分各子主题内部结构。
- 子目录里的命令默认以仓库根目录或各自子目录为起点，具体以子目录 README 为准。
