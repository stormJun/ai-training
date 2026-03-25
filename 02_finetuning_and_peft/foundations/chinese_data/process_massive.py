#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
MASSIVE 中文数据集处理脚本
功能：将原始数据转换为 LoRA 微调所需的格式
支持：标准指令格式 + 对话格式
"""

import json
import re
import argparse
from pathlib import Path
from collections import defaultdict, Counter
from typing import List, Dict, Tuple


def filter_samples(sample: dict) -> bool:
    """
    质量过滤规则

    Args:
        sample: 原始样本

    Returns:
        是否保留该样本
    """
    judgments = sample.get('judgments', [])

    if not judgments:
        return False

    # 规则1: 意图和槽位评分必须为1（完全匹配）或2（无槽位）
    intent_scores = [j.get('intent_score', 0) for j in judgments]
    slots_scores = [j.get('slots_score', 0) for j in judgments]

    if not all(s == 1 for s in intent_scores):
        return False
    if not all(s in [1, 2] for s in slots_scores):  # 2表示无槽位，也接受
        return False

    # 规则2: 语法评分≥3（足够好）
    grammar_scores = [j.get('grammar_score', 0) for j in judgments]
    if not all(s >= 3 for s in grammar_scores):
        return False

    # 规则3: 拼写评分≥2（无拼写错误）
    spelling_scores = [j.get('spelling_score', 0) for j in judgments]
    if not all(s >= 2 for s in spelling_scores):
        return False

    return True


def parse_slots(annot_utt: str, original_utt: str) -> List[dict]:
    """
    从标注语句中解析槽位

    Args:
        annot_utt: 带标注的语句，如 "[date : 今天] [timeofday : 下午] [time : 三点] 提醒我 [event_name : 开会]"
        original_utt: 原始语句，用于验证

    Returns:
        槽位列表，如 [{"type": "date", "value": "今天"}, ...]
    """
    pattern = r'\[([^:]+)\s*:\s*([^\]]+)\]'
    matches = re.findall(pattern, annot_utt)

    slots = []
    for slot_type, slot_value in matches:
        slot_type = slot_type.strip()
        slot_value = slot_value.strip()

        # 验证槽位值是否在原始语句中
        if slot_value in original_utt:
            slots.append({
                "type": slot_type,
                "value": slot_value
            })
        else:
            # 有些槽位值可能在原句中略有差异（如空格、标点等），也保留
            slots.append({
                "type": slot_type,
                "value": slot_value
            })

    return slots


def convert_to_instruction_format(sample: dict) -> dict:
    """
    转换为标准指令格式

    格式：
    {
        "instruction": "请识别用户意图并提取槽位信息，以JSON格式输出。",
        "input": "用户输入",
        "output": "JSON字符串",
        "meta": {...}
    }
    """
    # 解析槽位
    slots = parse_slots(sample['annot_utt'], sample['utt'])

    # 构造输出JSON
    output_dict = {
        "intent": sample['intent'],
        "slots": slots
    }

    # 转换为字符串（小模型友好）
    output_str = json.dumps(output_dict, ensure_ascii=False)

    return {
        "instruction": "请识别用户意图并提取槽位信息，以JSON格式输出。",
        "input": sample['utt'],
        "output": output_str,
        # 保留元信息，便于调试和分析
        "meta": {
            "id": sample['id'],
            "scenario": sample['scenario'],
            "partition": sample['partition']
        }
    }


def convert_to_chat_format(sample: dict) -> dict:
    """
    转换为对话格式

    格式：
    {
        "messages": [
            {"role": "system", "content": "..."},
            {"role": "user", "content": "..."},
            {"role": "assistant", "content": "..."}
        ],
        "meta": {...}
    }
    """
    # 解析槽位
    slots = parse_slots(sample['annot_utt'], sample['utt'])

    # 构造输出JSON
    output_dict = {
        "intent": sample['intent'],
        "slots": slots
    }
    output_str = json.dumps(output_dict, ensure_ascii=False)

    return {
        "messages": [
            {
                "role": "system",
                "content": "你是一个专业的意图识别和槽位抽取助手。用户输入一句话，你需要识别意图并提取槽位信息，以JSON格式回复。"
            },
            {
                "role": "user",
                "content": sample['utt']
            },
            {
                "role": "assistant",
                "content": output_str
            }
        ],
        "meta": {
            "id": sample['id'],
            "scenario": sample['scenario'],
            "partition": sample['partition']
        }
    }


def process_massive_data(
    input_file: str,
    output_dir: str,
    format_type: str = "instruction",
    enable_filter: bool = True,
    verbose: bool = True
) -> Dict:
    """
    完整数据加工流程

    Args:
        input_file: zh-CN.jsonl 路径
        output_dir: 输出目录
        format_type: 数据格式类型 ("instruction" 或 "chat")
        enable_filter: 是否启用质量过滤
        verbose: 是否输出详细信息

    Returns:
        统计信息字典
    """
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    if verbose:
        print(f"\n{'='*80}")
        print(f"📦 MASSIVE 中文数据处理")
        print(f"{'='*80}")
        print(f"输入文件: {input_file}")
        print(f"输出目录: {output_dir}")
        print(f"数据格式: {format_type}")
        print(f"质量过滤: {'启用' if enable_filter else '禁用'}")
        print(f"{'='*80}\n")

    # 统计信息
    stats = {
        'total': 0,
        'filtered': 0,
        'train': 0,
        'dev': 0,
        'test': 0,
        'intent_dist': Counter(),
        'scenario_dist': Counter(),
        'slot_type_dist': Counter(),
        'samples_with_slots': 0,
        'samples_without_slots': 0
    }

    # 按partition分组
    data_by_partition = defaultdict(list)

    # 读取和处理数据
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            stats['total'] += 1
            sample = json.loads(line.strip())

            # 质量过滤
            if enable_filter and not filter_samples(sample):
                stats['filtered'] += 1
                continue

            # 转换格式
            if format_type == "instruction":
                converted = convert_to_instruction_format(sample)
            elif format_type == "chat":
                converted = convert_to_chat_format(sample)
            else:
                raise ValueError(f"未知格式: {format_type}，仅支持 'instruction' 或 'chat'")

            # 分区存储
            partition = sample['partition']
            data_by_partition[partition].append(converted)

            # 更新统计
            stats[partition] += 1
            stats['intent_dist'][sample['intent']] += 1
            stats['scenario_dist'][sample['scenario']] += 1

            # 统计槽位类型
            slots = parse_slots(sample['annot_utt'], sample['utt'])
            if slots:
                stats['samples_with_slots'] += 1
                for slot in slots:
                    stats['slot_type_dist'][slot['type']] += 1
            else:
                stats['samples_without_slots'] += 1

    # 写入文件
    partition_mapping = {'train': 'train', 'dev': 'validation', 'test': 'test'}
    for partition, samples in data_by_partition.items():
        output_file = output_path / f"{partition_mapping[partition]}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for sample in samples:
                f.write(json.dumps(sample, ensure_ascii=False) + '\n')

        if verbose:
            print(f"✅ 已生成: {output_file.name:20s} ({len(samples):5d} 条)")

    # 输出统计信息
    if verbose:
        print(f"\n{'='*80}")
        print(f"📊 数据统计")
        print(f"{'='*80}")
        print(f"总样本数:     {stats['total']:6d}")
        print(f"过滤样本数:   {stats['filtered']:6d} ({stats['filtered']/stats['total']*100:5.2f}%)")
        print(f"保留样本数:   {stats['total']-stats['filtered']:6d} ({(stats['total']-stats['filtered'])/stats['total']*100:5.2f}%)")
        print(f"\n数据集划分:")
        print(f"  训练集:     {stats['train']:6d} 条")
        print(f"  验证集:     {stats['dev']:6d} 条")
        print(f"  测试集:     {stats['test']:6d} 条")
        print(f"\n标注统计:")
        print(f"  意图类别:   {len(stats['intent_dist']):6d} 种")
        print(f"  场景类别:   {len(stats['scenario_dist']):6d} 种")
        print(f"  槽位类型:   {len(stats['slot_type_dist']):6d} 种")
        print(f"\n槽位覆盖:")
        print(f"  有槽位样本: {stats['samples_with_slots']:6d} ({stats['samples_with_slots']/(stats['total']-stats['filtered'])*100:5.2f}%)")
        print(f"  无槽位样本: {stats['samples_without_slots']:6d} ({stats['samples_without_slots']/(stats['total']-stats['filtered'])*100:5.2f}%)")

        # Top 10 意图
        print(f"\n🎯 Top 10 意图分布:")
        for intent, count in stats['intent_dist'].most_common(10):
            print(f"  {intent:25s} {count:5d} 条")

        # Top 10 槽位类型
        print(f"\n🏷️  Top 10 槽位类型:")
        for slot_type, count in stats['slot_type_dist'].most_common(10):
            print(f"  {slot_type:25s} {count:5d} 次")

        print(f"\n{'='*80}\n")

    # 保存统计信息到JSON文件
    stats_file = output_path / "statistics.json"
    with open(stats_file, 'w', encoding='utf-8') as f:
        # 转换Counter为dict以便JSON序列化
        stats_export = {
            'total': stats['total'],
            'filtered': stats['filtered'],
            'retained': stats['total'] - stats['filtered'],
            'train': stats['train'],
            'dev': stats['dev'],
            'test': stats['test'],
            'intent_count': len(stats['intent_dist']),
            'scenario_count': len(stats['scenario_dist']),
            'slot_type_count': len(stats['slot_type_dist']),
            'samples_with_slots': stats['samples_with_slots'],
            'samples_without_slots': stats['samples_without_slots'],
            'intent_distribution': dict(stats['intent_dist']),
            'scenario_distribution': dict(stats['scenario_dist']),
            'slot_type_distribution': dict(stats['slot_type_dist'])
        }
        json.dump(stats_export, f, ensure_ascii=False, indent=2)

    if verbose:
        print(f"📈 统计信息已保存到: {stats_file.name}")

    return stats


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="MASSIVE 中文数据集处理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 生成标准指令格式
  python process_massive.py --format instruction

  # 生成对话格式
  python process_massive.py --format chat --output processed_chat

  # 禁用质量过滤
  python process_massive.py --format instruction --no-filter

  # 生成两种格式
  python process_massive.py --format instruction --output processed_instruction
  python process_massive.py --format chat --output processed_chat
        """
    )

    parser.add_argument(
        '--input',
        type=str,
        default='zh-CN.jsonl',
        help='输入文件路径 (默认: zh-CN.jsonl)'
    )

    parser.add_argument(
        '--output',
        type=str,
        default='processed_instruction',
        help='输出目录 (默认: processed_instruction)'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['instruction', 'chat'],
        default='instruction',
        help='数据格式类型 (默认: instruction)'
    )

    parser.add_argument(
        '--no-filter',
        action='store_true',
        help='禁用质量过滤'
    )

    parser.add_argument(
        '--quiet',
        action='store_true',
        help='静默模式，不输出详细信息'
    )

    args = parser.parse_args()

    # 处理数据
    process_massive_data(
        input_file=args.input,
        output_dir=args.output,
        format_type=args.format,
        enable_filter=not args.no_filter,
        verbose=not args.quiet
    )

    print("\n✅ 数据处理完成！\n")


if __name__ == "__main__":
    main()
