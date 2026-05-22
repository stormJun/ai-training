"""
MASSIVE 数据集训练脚本

这个脚本用于在 MASSIVE 数据集上训练自然语言理解（NLU）模型。
支持意图分类（Intent Classification）和槽位填充（Slot Filling）任务。

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").
You may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse  # 命令行参数解析
import datetime  # 日期时间处理
import logging  # 日志记录
import os  # 操作系统接口
import sys  # 系统相关参数和函数

import datasets  # HuggingFace 数据集库
from massive import (
    MASSIVETrainer,  # MASSIVE 标准训练器（用于 JointBERT 等模型）
    MASSIVESeq2SeqTrainer,  # MASSIVE 序列到序列训练器（用于 mT5 等生成式模型）
    MASSIVETrainingArguments,  # 训练参数配置类
    create_compute_metrics,  # 创建评估指标计算函数
    init_model,  # 初始化模型
    init_tokenizer,  # 初始化分词器
    prepare_collator,  # 准备数据整理器（collator）
    prepare_train_dev_datasets,  # 准备训练集和验证集
    read_conf,  # 读取配置文件
)
import transformers  # HuggingFace Transformers 库
from ruamel.yaml import YAML  # YAML 配置文件解析

# 创建日志记录器
logger = logging.getLogger('massive_logger')

def main():
    """
    主训练函数

    功能：
    1. 解析命令行参数（配置文件路径、分布式训练参数等）
    2. 加载和配置训练参数
    3. 初始化模型、分词器、数据集
    4. 设置评估指标
    5. 执行训练流程
    """
    # ========== 步骤 1: 解析命令行参数 ==========
    parser = argparse.ArgumentParser(description="在 MASSIVE 数据集上训练 NLU 模型")
    parser.add_argument('-c', '--config', help='配置文件路径（YAML 格式）')
    parser.add_argument('--local_rank', help='分布式训练中当前进程的本地排名（可选）')
    args = parser.parse_args()

    # ========== 步骤 2: 加载配置文件 ==========
    # 从 YAML 配置文件中读取所有训练配置
    conf = read_conf(args.config)
    # 从配置中提取训练器参数（学习率、批次大小、训练轮数等）
    trainer_args = MASSIVETrainingArguments(**conf.get('train_val.trainer_args'))

    # 设置分布式训练的本地排名（用于多 GPU 训练）
    if args.local_rank:
        trainer_args.local_rank = int(args.local_rank)
    elif os.getenv('LOCAL_RANK'):  # 从环境变量中获取
        trainer_args.local_rank = int(os.environ['LOCAL_RANK'])

    # ========== 步骤 3: 配置日志系统 ==========
    logging.basicConfig(
        format="[%(levelname)s] %(asctime)s >> %(message)s",  # 日志格式：[级别] 时间 >> 消息
        datefmt="%H:%M",  # 时间格式：小时:分钟
        handlers=[logging.StreamHandler(sys.stdout)],  # 输出到标准输出
    )
    # 根据训练参数设置日志级别（INFO、DEBUG 等）
    log_level = trainer_args.get_process_log_level()
    logger.setLevel(log_level)
    # 设置 datasets 和 transformers 库的日志级别
    datasets.utils.logging.set_verbosity(log_level)
    transformers.utils.logging.set_verbosity(log_level)
    transformers.utils.logging.enable_default_handler()

    # 记录训练开始时间和使用的配置
    logger.info(f"训练开始时间: {datetime.datetime.now()}")
    yaml = YAML(typ='safe')
    logger.info(f"使用的配置: {yaml.load(open(args.config, 'r'))}")

    # ========== 步骤 4: 初始化训练所需的所有组件 ==========

    # 4.1 初始化分词器（例如 XLM-RoBERTa 或 mT5 的分词器）
    tokenizer = init_tokenizer(conf)

    # 4.2 准备训练集和验证集
    # 返回值：
    # - train_ds: 训练数据集
    # - dev_ds: 验证数据集
    # - intents: 意图标签列表（60 种意图）
    # - slots: 槽位标签列表（55 种槽位类型）
    train_ds, dev_ds, intents, slots = prepare_train_dev_datasets(conf, tokenizer)

    # 4.3 初始化模型（例如 XLM-R + JointBERT 或 mT5）
    model = init_model(conf, intents, slots)

    # 4.4 准备数据整理器（将批次数据转换为模型输入格式）
    collator = prepare_collator(conf, tokenizer, model)

    # 4.5 配置评估指标
    # 获取需要忽略的槽位标签（例如 'Other' 标签）
    slots_ignore = conf.get('train_val.slot_labels_ignore', default=[])
    # 获取需要计算的评估指标（默认计算所有指标）
    metrics = conf.get('train_val.eval_metrics', default='all')
    # 创建评估指标计算函数（计算意图准确率、槽位 F1 等）
    compute_metrics = create_compute_metrics(intents, slots, conf, tokenizer, slots_ignore,
                                             metrics)

    # ========== 步骤 5: 选择合适的训练器并开始训练 ==========

    # 根据配置选择训练器类型：
    # - 'massive s2s': 序列到序列训练器（用于 mT5 等生成式模型）
    # - 其他: 标准训练器（用于 XLM-R + JointBERT 等判别式模型）
    trainer_cls = MASSIVESeq2SeqTrainer \
                  if conf.get('train_val.trainer') == 'massive s2s' \
                  else MASSIVETrainer

    # 实例化训练器
    trainer = trainer_cls(
        model=model,  # 待训练的模型
        args=trainer_args,  # 训练参数（学习率、批次大小、训练轮数等）
        train_dataset=train_ds,  # 训练数据集
        eval_dataset=dev_ds,  # 验证数据集
        data_collator=collator,  # 数据整理器
        compute_metrics=compute_metrics,  # 评估指标计算函数
        tokenizer=tokenizer  # 分词器
    )

    # 开始训练！
    # 训练过程会自动：
    # 1. 在每个 epoch 后在验证集上评估模型
    # 2. 保存最佳模型检查点
    # 3. 记录训练日志和指标
    trainer.train()

# 程序入口点
if __name__ == "__main__":
    main()
