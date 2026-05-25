"""
MASSIVE 数据集测试脚本

这个脚本用于在 MASSIVE 数据集的测试集上评估已训练好的模型。
支持意图分类（Intent Classification）和槽位填充（Slot Filling）任务的推理和评估。

主要功能：
1. 加载已训练的模型检查点
2. 在测试集上执行推理
3. 计算评估指标（意图准确率、槽位 F1 等）
4. 输出预测结果到文件（可选）

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
import pprint  # 美化打印（用于格式化输出评估指标）
import sys  # 系统相关参数和函数
import time  # 时间处理

import datasets  # HuggingFace 数据集库
from massive import (
    MASSIVETrainer,  # MASSIVE 标准训练器
    MASSIVESeq2SeqTrainer,  # MASSIVE 序列到序列训练器
    MASSIVETrainingArguments,  # 训练/测试参数配置类
    create_compute_metrics,  # 创建评估指标计算函数
    init_model,  # 初始化模型（从检查点加载）
    init_tokenizer,  # 初始化分词器
    output_predictions,  # 输出预测结果到文件
    prepare_collator,  # 准备数据整理器
    prepare_test_dataset,  # 准备测试数据集
    read_conf,  # 读取配置文件
)
from ruamel.yaml import YAML  # YAML 配置文件解析
import torch.distributed as dist  # PyTorch 分布式训练支持
import transformers  # HuggingFace Transformers 库

# 创建日志记录器
logger = logging.getLogger('massive_logger')

def main():
    """
    主测试函数

    功能：
    1. 解析命令行参数（配置文件路径、分布式训练参数等）
    2. 加载测试配置和模型检查点
    3. 在测试集上执行推理
    4. 计算并输出评估指标
    5. 可选：将预测结果保存到文件
    """
    # ========== 步骤 1: 解析命令行参数 ==========
    parser = argparse.ArgumentParser(description="在 MASSIVE 数据集上测试 NLU 模型")
    parser.add_argument('-c', '--config', help='配置文件路径（YAML 格式）')
    parser.add_argument('--local_rank', help='分布式训练中当前进程的本地排名（可选）')
    args = parser.parse_args()

    # ========== 步骤 2: 加载配置文件 ==========
    # 从 YAML 配置文件中读取所有测试配置
    conf = read_conf(args.config)
    # 从配置中提取测试器参数（包括模型检查点路径等）
    trainer_args = MASSIVETrainingArguments(**conf.get('test.trainer_args'))

    # 设置分布式训练的本地排名
    if args.local_rank:
        trainer_args.local_rank = int(args.local_rank)
    elif os.getenv('LOCAL_RANK'):
        trainer_args.local_rank = int(os.environ['LOCAL_RANK'])

    # ========== 步骤 3: 配置日志系统 ==========
    logging.basicConfig(
        format="[%(levelname)s] %(asctime)s >> %(message)s",  # 日志格式
        datefmt="%H:%M",  # 时间格式
        handlers=[logging.StreamHandler(sys.stdout)],  # 输出到标准输出
    )
    log_level = trainer_args.get_process_log_level()
    logger.setLevel(log_level)
    datasets.utils.logging.set_verbosity(log_level)
    transformers.utils.logging.set_verbosity(log_level)
    transformers.utils.logging.enable_default_handler()

    # 记录测试开始时间和使用的配置
    logger.info(f"测试开始时间: {datetime.datetime.now()}")
    yaml = YAML(typ='safe')
    logger.info(f"使用的配置: {yaml.load(open(args.config, 'r'))}")

    # ========== 步骤 4: 检查配置的正确性 ==========
    # 检查是否设置了预测结果输出文件
    if not conf.get('test.predictions_file'):
        logger.warning("警告：未设置 test.predictions_file，预测结果将不会被保存")

    # 如果要保存预测结果，必须使用 'all only' 评估策略
    # 这确保所有语言的预测结果都在同一个文件中
    if conf.get('test.predictions_file') and \
       (conf.get('test.trainer_args.locale_eval_strategy') != 'all only'):
        raise NotImplementedError("如果要保存预测结果（test.predictions_file），"
                                  "必须使用 'all only' 作为 locale_eval_strategy")

    # ========== 步骤 5: 初始化测试所需的所有组件 ==========

    # 5.1 初始化分词器
    tokenizer = init_tokenizer(conf)

    # 5.2 准备测试数据集
    # 返回值：
    # - test_ds: 测试数据集
    # - intents: 意图标签列表
    # - slots: 槽位标签列表
    test_ds, intents, slots = prepare_test_dataset(conf, tokenizer)

    # 5.3 初始化模型（从训练好的检查点加载）
    model = init_model(conf, intents, slots)

    # 5.4 准备数据整理器
    collator = prepare_collator(conf, tokenizer, model)

    # 5.5 配置评估指标
    slots_ignore = conf.get('test.slot_labels_ignore', default=[])
    metrics = conf.get('test.eval_metrics', default='all')
    compute_metrics = create_compute_metrics(intents, slots, conf, tokenizer, slots_ignore,
                                             metrics)

    # ========== 步骤 6: 选择合适的训练器类型 ==========
    trainer_cls = MASSIVESeq2SeqTrainer \
                  if conf.get('test.trainer') == 'massive s2s' \
                  else MASSIVETrainer

    # 实例化训练器（用于测试）
    trainer = trainer_cls(
        model=model,
        args=trainer_args,
        data_collator=collator,
        compute_metrics=compute_metrics,
        tokenizer=tokenizer
    )

    # 移除 TensorBoard 回调（测试时不需要）
    trainer.remove_callback(transformers.integrations.TensorBoardCallback)

    # ========== 步骤 7: 执行测试推理 ==========
    # 在测试集上运行模型推理
    outputs = trainer.predict(test_ds, tokenizer=tokenizer)

    # ========== 步骤 8: 输出评估结果 ==========
    # 获取当前进程的排名（用于分布式测试）
    rank = dist.get_rank() if dist.is_initialized() else 0

    # 只在主进程（rank 0）输出结果
    if rank == 0:
        time.sleep(3)  # 等待所有进程完成
        logger.info('注意：使用验证引擎的测试指标仅供参考。要获得"官方"指标，'
                    '请在配置中包含 test.predictions_file 并使用 eval.ai 排行榜')
        logger.info(f'验证引擎指标（计算机可读格式）: {outputs.metrics}')
        logger.info('验证引擎指标（美化格式）：')
        pp = pprint.PrettyPrinter(indent=2)
        pp.pprint(outputs.metrics)

        # 判断是否需要保存预测结果到文件
        save_to_file = True if conf.get('test.predictions_file') else False

        # 输出预测结果（保存到文件或仅打印）
        output_predictions(outputs, intents, slots, conf, tokenizer,
                           remove_slots=slots_ignore, save_to_file=save_to_file)

# 程序入口点
if __name__ == "__main__":
    main()
