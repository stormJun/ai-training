#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
评估脚本 - 意图识别 + 槽位填充
计算指标：意图准确率、槽位F1、联合准确率等
"""

import json
import re
import argparse
from typing import Dict, List, Tuple
from sklearn.metrics import accuracy_score, f1_score, classification_report
from collections import Counter


def parse_output_json(output_str: str) -> Dict:
    """
    解析模型输出的JSON字符串
    支持容错：处理格式不规范的输出

    Args:
        output_str: 模型输出的字符串

    Returns:
        解析后的字典 {"intent": "...", "slots": [...]}
    """
    try:
        # 尝试直接解析
        return json.loads(output_str)
    except:
        # 容错：使用正则提取
        intent_match = re.search(r'"intent"\s*:\s*"([^"]+)"', output_str)
        slots_match = re.findall(
            r'\{\s*"type"\s*:\s*"([^"]+)"\s*,\s*"value"\s*:\s*"([^"]+)"\s*\}',
            output_str
        )

        if intent_match:
            return {
                "intent": intent_match.group(1),
                "slots": [{"type": t, "value": v} for t, v in slots_match]
            }
        else:
            return {"intent": "", "slots": []}


def evaluate_predictions(
    pred_file: str,
    detailed_output: bool = True,
    save_errors: bool = True,
    error_file: str = None
) -> Dict:
    """
    评估预测结果

    Args:
        pred_file: 预测结果文件（每行包含output和ground_truth）
        detailed_output: 是否输出详细报告
        save_errors: 是否保存错误案例
        error_file: 错误案例保存路径

    Returns:
        评估指标字典
    """
    # 读取预测数据
    predictions = []
    with open(pred_file, 'r', encoding='utf-8') as f:
        for line in f:
            predictions.append(json.loads(line.strip()))

    # 解析预测和标准答案
    pred_intents = []
    gold_intents = []
    pred_slots_list = []
    gold_slots_list = []

    slot_exact_match = 0
    joint_correct = 0
    parse_errors = 0

    error_cases = []  # 记录错误案例

    for i, pred in enumerate(predictions):
        # 解析预测输出
        try:
            pred_output = parse_output_json(pred['output'])
            gold_output = json.loads(pred['ground_truth'])
        except Exception as e:
            parse_errors += 1
            if i < 5:  # 只打印前5个错误
                print(f"[错误 #{i}] 解析失败: {str(e)}")
                print(f"  输出: {pred['output'][:100]}")
            pred_output = {"intent": "", "slots": []}
            gold_output = json.loads(pred['ground_truth'])

        # 意图
        pred_intent = pred_output.get('intent', '')
        gold_intent = gold_output.get('intent', '')
        pred_intents.append(pred_intent)
        gold_intents.append(gold_intent)

        # 槽位（转为集合便于比较）
        pred_slots = set(
            (slot['type'], slot['value'])
            for slot in pred_output.get('slots', [])
        )
        gold_slots = set(
            (slot['type'], slot['value'])
            for slot in gold_output.get('slots', [])
        )

        pred_slots_list.append(pred_slots)
        gold_slots_list.append(gold_slots)

        # 槽位完全匹配
        if pred_slots == gold_slots:
            slot_exact_match += 1

        # 联合准确率
        intent_correct = pred_intent == gold_intent
        slots_correct = pred_slots == gold_slots

        if intent_correct and slots_correct:
            joint_correct += 1
        else:
            # 记录错误案例
            if save_errors:
                error_cases.append({
                    'id': pred.get('meta', {}).get('id', i),
                    'input': pred['input'],
                    'scenario': pred.get('meta', {}).get('scenario', ''),
                    'pred_intent': pred_intent,
                    'gold_intent': gold_intent,
                    'intent_correct': intent_correct,
                    'pred_slots': sorted(list(pred_slots)),
                    'gold_slots': sorted(list(gold_slots)),
                    'slots_correct': slots_correct,
                    'pred_output': pred['output'],
                    'gold_output': pred['ground_truth']
                })

    total = len(predictions)

    # ==================== 计算指标 ====================

    # 意图识别指标
    intent_acc = accuracy_score(gold_intents, pred_intents)
    intent_f1_macro = f1_score(gold_intents, pred_intents, average='macro', zero_division=0)
    intent_f1_weighted = f1_score(gold_intents, pred_intents, average='weighted', zero_division=0)

    # 槽位填充指标
    slot_em = slot_exact_match / total if total > 0 else 0

    # 计算槽位级别的 Precision、Recall、F1
    slot_tp = 0  # True Positive
    slot_fp = 0  # False Positive
    slot_fn = 0  # False Negative

    for pred_slots, gold_slots in zip(pred_slots_list, gold_slots_list):
        slot_tp += len(pred_slots & gold_slots)  # 交集
        slot_fp += len(pred_slots - gold_slots)  # 预测了但不在标准答案中
        slot_fn += len(gold_slots - pred_slots)  # 标准答案中有但没预测到

    slot_precision = slot_tp / (slot_tp + slot_fp) if (slot_tp + slot_fp) > 0 else 0
    slot_recall = slot_tp / (slot_tp + slot_fn) if (slot_tp + slot_fn) > 0 else 0
    slot_f1 = 2 * slot_precision * slot_recall / (slot_precision + slot_recall) if (
                slot_precision + slot_recall) > 0 else 0

    # 联合任务指标
    joint_acc = joint_correct / total if total > 0 else 0

    # ==================== 打印评估结果 ====================

    print("=" * 80)
    print("📊 意图识别 + 槽位填充 评估结果")
    print("=" * 80)

    # 基础信息
    print(f"\n📌 数据集信息:")
    print(f"  测试样本数:   {total:6d}")
    print(f"  解析错误数:   {parse_errors:6d} ({parse_errors / total * 100:5.2f}%)")

    # 意图识别指标
    print(f"\n🎯 意图识别:")
    print(f"  Accuracy:      {intent_acc:.4f} ({intent_acc * 100:6.2f}%)")
    print(f"  F1 (Macro):    {intent_f1_macro:.4f}")
    print(f"  F1 (Weighted): {intent_f1_weighted:.4f}")

    # 槽位填充指标
    print(f"\n🏷️  槽位填充:")
    print(f"  Exact Match:   {slot_em:.4f} ({slot_em * 100:6.2f}%)")
    print(f"  Precision:     {slot_precision:.4f}")
    print(f"  Recall:        {slot_recall:.4f}")
    print(f"  F1:            {slot_f1:.4f}")

    # 联合任务指标
    print(f"\n🔗 联合任务:")
    print(f"  Joint Accuracy: {joint_acc:.4f} ({joint_acc * 100:6.2f}%)")
    print(f"    （意图和所有槽位都正确的样本比例）")

    print("\n" + "=" * 80)

    # 详细报告
    if detailed_output:
        print("\n📋 意图分类详细报告:")
        print(classification_report(gold_intents, pred_intents, zero_division=0))

        # 错误分析统计
        if error_cases:
            intent_errors = sum(1 for e in error_cases if not e['intent_correct'])
            slots_errors = sum(1 for e in error_cases if not e['slots_correct'])
            both_errors = sum(1 for e in error_cases if not e['intent_correct'] and not e['slots_correct'])

            print(f"\n❌ 错误分析统计:")
            print(f"  总错误数:     {len(error_cases):6d}")
            print(f"  意图错误:     {intent_errors:6d} ({intent_errors / total * 100:5.2f}%)")
            print(f"  槽位错误:     {slots_errors:6d} ({slots_errors / total * 100:5.2f}%)")
            print(f"  两者都错:     {both_errors:6d} ({both_errors / total * 100:5.2f}%)")

            # 错误案例示例
            print(f"\n❌ 错误案例示例（前5个）:")
            for i, case in enumerate(error_cases[:5], 1):
                print(f"\n  案例 #{i}:")
                print(f"    输入: {case['input']}")
                print(f"    场景: {case['scenario']}")

                if not case['intent_correct']:
                    print(f"    ❌ 意图错误:")
                    print(f"       预测: {case['pred_intent']}")
                    print(f"       正确: {case['gold_intent']}")
                else:
                    print(f"    ✅ 意图正确: {case['gold_intent']}")

                if not case['slots_correct']:
                    print(f"    ❌ 槽位错误:")
                    print(f"       预测: {case['pred_slots']}")
                    print(f"       正确: {case['gold_slots']}")
                else:
                    print(f"    ✅ 槽位正确")

    # 保存错误案例
    if save_errors and error_cases:
        if error_file is None:
            error_file = pred_file.replace('.jsonl', '_errors.jsonl')

        with open(error_file, 'w', encoding='utf-8') as f:
            for error in error_cases:
                f.write(json.dumps(error, ensure_ascii=False) + '\n')

        print(f"\n💾 错误案例已保存到: {error_file}")
        print(f"   共 {len(error_cases)} 个错误案例")

    # 返回指标
    return {
        'total': total,
        'parse_errors': parse_errors,
        'intent_accuracy': intent_acc,
        'intent_f1_macro': intent_f1_macro,
        'intent_f1_weighted': intent_f1_weighted,
        'slot_exact_match': slot_em,
        'slot_precision': slot_precision,
        'slot_recall': slot_recall,
        'slot_f1': slot_f1,
        'joint_accuracy': joint_acc
    }


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="意图识别 + 槽位填充 评估工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 基本评估
  python evaluate.py --pred predictions.jsonl

  # 保存错误案例到指定文件
  python evaluate.py --pred predictions.jsonl --error-file errors.jsonl

  # 简化输出（不显示详细报告）
  python evaluate.py --pred predictions.jsonl --no-detail

  # 不保存错误案例
  python evaluate.py --pred predictions.jsonl --no-save-errors
        """
    )

    parser.add_argument(
        '--pred',
        type=str,
        required=True,
        help='预测结果文件路径（包含output和ground_truth字段）'
    )

    parser.add_argument(
        '--error-file',
        type=str,
        default=None,
        help='错误案例保存路径（默认：预测文件名_errors.jsonl）'
    )

    parser.add_argument(
        '--no-detail',
        action='store_true',
        help='不显示详细报告'
    )

    parser.add_argument(
        '--no-save-errors',
        action='store_true',
        help='不保存错误案例'
    )

    parser.add_argument(
        '--output',
        type=str,
        default=None,
        help='评估结果保存路径（JSON格式）'
    )

    args = parser.parse_args()

    # 评估
    results = evaluate_predictions(
        pred_file=args.pred,
        detailed_output=not args.no_detail,
        save_errors=not args.no_save_errors,
        error_file=args.error_file
    )

    # 保存评估结果
    if args.output:
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f"\n📊 评估结果已保存到: {args.output}")

    print("\n✅ 评估完成！\n")


if __name__ == "__main__":
    main()
