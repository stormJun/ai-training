#!/usr/bin/env python3
"""
MASSIVE 数据集格式转换工具
将 Amazon MASSIVE 意图分类数据集转换为微调平台所需格式
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict

def convert_massive_to_training_format(
    input_file: str,
    output_file: str,
    instruction_template: str = "请识别以下用户语句的意图分类"
) -> None:
    """
    转换 MASSIVE 数据集格式

    Args:
        input_file: MASSIVE 原始数据文件路径
        output_file: 输出的训练数据文件路径
        instruction_template: 指令模板
    """

    converted_data = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue

            original = json.loads(line)

            # 转换为训练格式
            converted = {
                "instruction": instruction_template,
                "input": original["text"],
                "output": f"{original['label_text_ch']}({original['label_text']})"
            }

            converted_data.append(converted)

    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in converted_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"✅ 转换完成！")
    print(f"   输入文件: {input_file}")
    print(f"   输出文件: {output_file}")
    print(f"   转换条数: {len(converted_data)}")


def convert_to_chat_format(
    input_file: str,
    output_file: str,
    system_prompt: str = "你是一个意图识别助手，能够准确识别用户语句的意图。"
) -> None:
    """
    转换为对话格式（适用于聊天模型）

    Args:
        input_file: MASSIVE 原始数据文件路径
        output_file: 输出文件路径
        system_prompt: 系统提示词
    """

    converted_data = []

    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue

            original = json.loads(line)

            # 转换为对话格式
            converted = {
                "messages": [
                    {
                        "role": "system",
                        "content": system_prompt
                    },
                    {
                        "role": "user",
                        "content": f"请识别意图: {original['text']}"
                    },
                    {
                        "role": "assistant",
                        "content": f"意图分类: {original['label_text_ch']}({original['label_text']})"
                    }
                ]
            }

            converted_data.append(converted)

    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for item in converted_data:
            f.write(json.dumps(item, ensure_ascii=False) + '\n')

    print(f"✅ 转换完成！")
    print(f"   输入文件: {input_file}")
    print(f"   输出文件: {output_file}")
    print(f"   转换条数: {len(converted_data)}")


def show_sample(file_path: str, num_samples: int = 3) -> None:
    """显示数据样本"""
    print(f"\n📋 数据样本预览 ({file_path}):\n")

    with open(file_path, 'r', encoding='utf-8') as f:
        for i, line in enumerate(f):
            if i >= num_samples:
                break

            data = json.loads(line)
            print(f"样本 {i+1}:")
            print(json.dumps(data, indent=2, ensure_ascii=False))
            print("-" * 60)


def main():
    parser = argparse.ArgumentParser(
        description="MASSIVE 数据集格式转换工具"
    )
    parser.add_argument(
        "--input",
        default="amazon_massive_intent_zh-CN/train.jsonl",
        help="输入文件路径"
    )
    parser.add_argument(
        "--output",
        default="amazon_massive_intent_zh-CN/train_converted.jsonl",
        help="输出文件路径"
    )
    parser.add_argument(
        "--format",
        choices=["instruction", "chat"],
        default="instruction",
        help="输出格式: instruction (指令格式) 或 chat (对话格式)"
    )
    parser.add_argument(
        "--preview",
        action="store_true",
        help="转换后预览数据样本"
    )

    args = parser.parse_args()

    # 执行转换
    if args.format == "instruction":
        convert_massive_to_training_format(args.input, args.output)
    else:
        convert_to_chat_format(args.input, args.output)

    # 预览
    if args.preview:
        show_sample(args.output)


if __name__ == "__main__":
    main()
