#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
推理脚本 - 使用微调后的模型进行预测
支持：批量推理、LoRA模型加载
"""

import json
import argparse
import torch
from pathlib import Path
from typing import List, Dict
from tqdm import tqdm


def load_model_and_tokenizer(base_model_path: str, lora_path: str = None, device: str = "auto"):
    """
    加载基础模型和LoRA权重

    Args:
        base_model_path: 基础模型路径
        lora_path: LoRA权重路径（可选）
        device: 设备类型

    Returns:
        model, tokenizer
    """
    try:
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import PeftModel
    except ImportError:
        print("❌ 请先安装依赖: pip install transformers peft")
        exit(1)

    print(f"\n📦 加载模型...")
    print(f"  基础模型: {base_model_path}")

    # 加载tokenizer
    tokenizer = AutoTokenizer.from_pretrained(
        base_model_path,
        trust_remote_code=True,
        padding_side='left'
    )

    # 设置pad_token
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # 加载模型
    model = AutoModelForCausalLM.from_pretrained(
        base_model_path,
        torch_dtype=torch.float16,
        device_map=device,
        trust_remote_code=True
    )

    # 加载LoRA权重
    if lora_path:
        print(f"  LoRA权重: {lora_path}")
        model = PeftModel.from_pretrained(model, lora_path)
        model = model.merge_and_unload()  # 合并LoRA权重

    model.eval()
    print(f"✅ 模型加载完成！")

    return model, tokenizer


def predict_batch(
    model,
    tokenizer,
    test_file: str,
    output_file: str,
    batch_size: int = 8,
    max_new_tokens: int = 256,
    temperature: float = 0.1,
    format_type: str = "instruction"
) -> List[Dict]:
    """
    批量预测

    Args:
        model: 模型
        tokenizer: tokenizer
        test_file: 测试文件路径
        output_file: 输出文件路径
        batch_size: 批次大小
        max_new_tokens: 最大生成长度
        temperature: 温度参数
        format_type: 数据格式类型

    Returns:
        预测结果列表
    """
    print(f"\n🚀 开始推理...")
    print(f"  测试文件: {test_file}")
    print(f"  输出文件: {output_file}")
    print(f"  批次大小: {batch_size}")
    print(f"  最大生成: {max_new_tokens} tokens")
    print(f"  温度参数: {temperature}")

    # 读取测试数据
    test_data = []
    with open(test_file, 'r', encoding='utf-8') as f:
        for line in f:
            test_data.append(json.loads(line.strip()))

    print(f"  样本总数: {len(test_data)}\n")

    predictions = []

    with torch.no_grad():
        # 使用tqdm显示进度
        for i in tqdm(range(0, len(test_data), batch_size), desc="推理进度"):
            batch = test_data[i:i + batch_size]

            # 构造prompt
            prompts = []
            for sample in batch:
                if format_type == "instruction":
                    # 标准指令格式
                    prompt = f"{sample['instruction']}\n输入：{sample['input']}\n输出："
                elif format_type == "chat":
                    # 对话格式（需要使用模型的chat template）
                    messages = sample['messages'][:2]  # 只取system和user
                    prompt = tokenizer.apply_chat_template(
                        messages,
                        tokenize=False,
                        add_generation_prompt=True
                    )
                else:
                    raise ValueError(f"未知格式: {format_type}")

                prompts.append(prompt)

            # Tokenize
            inputs = tokenizer(
                prompts,
                return_tensors="pt",
                padding=True,
                truncation=True,
                max_length=512
            ).to(model.device)

            # 生成
            outputs = model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if temperature > 0 else None,
                do_sample=temperature > 0,  # 温度为0时使用贪心解码
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id
            )

            # 解码
            for j, output in enumerate(outputs):
                # 只保留生成的部分（去掉输入prompt）
                input_length = inputs['input_ids'][j].shape[0]
                generated = output[input_length:]
                predicted_text = tokenizer.decode(generated, skip_special_tokens=True)

                # 保存预测结果
                prediction = {
                    "instruction": batch[j]['instruction'] if format_type == "instruction" else
                    batch[j]['messages'][1]['content'],
                    "input": batch[j]['input'] if format_type == "instruction" else batch[j]['messages'][1]['content'],
                    "output": predicted_text.strip(),  # 模型预测的输出
                    "ground_truth": batch[j]['output'] if format_type == "instruction" else batch[j]['messages'][2][
                        'content'],  # 标准答案
                    "meta": batch[j].get('meta', {})
                }
                predictions.append(prediction)

    # 保存预测结果
    with open(output_file, 'w', encoding='utf-8') as f:
        for pred in predictions:
            f.write(json.dumps(pred, ensure_ascii=False) + '\n')

    print(f"\n✅ 推理完成！结果已保存到: {output_file}")
    print(f"   共预测 {len(predictions)} 个样本\n")

    return predictions


def main():
    """命令行入口"""
    parser = argparse.ArgumentParser(
        description="意图识别 + 槽位填充 推理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例用法:
  # 使用基础模型（未微调）
  python inference.py \\
    --base-model Qwen/Qwen2.5-1.5B-Instruct \\
    --test-file processed_instruction/test.jsonl \\
    --output predictions.jsonl

  # 使用LoRA微调后的模型
  python inference.py \\
    --base-model Qwen/Qwen2.5-1.5B-Instruct \\
    --lora-path ./outputs/checkpoint-best \\
    --test-file processed_instruction/test.jsonl \\
    --output predictions.jsonl

  # 调整推理参数
  python inference.py \\
    --base-model Qwen/Qwen2.5-1.5B-Instruct \\
    --lora-path ./outputs/checkpoint-best \\
    --test-file processed_instruction/test.jsonl \\
    --output predictions.jsonl \\
    --batch-size 16 \\
    --temperature 0.1 \\
    --max-new-tokens 256
        """
    )

    parser.add_argument(
        '--base-model',
        type=str,
        required=True,
        help='基础模型路径（HuggingFace模型名或本地路径）'
    )

    parser.add_argument(
        '--lora-path',
        type=str,
        default=None,
        help='LoRA权重路径（可选）'
    )

    parser.add_argument(
        '--test-file',
        type=str,
        required=True,
        help='测试文件路径'
    )

    parser.add_argument(
        '--output',
        type=str,
        required=True,
        help='输出文件路径'
    )

    parser.add_argument(
        '--batch-size',
        type=int,
        default=8,
        help='批次大小（默认：8）'
    )

    parser.add_argument(
        '--max-new-tokens',
        type=int,
        default=256,
        help='最大生成长度（默认：256）'
    )

    parser.add_argument(
        '--temperature',
        type=float,
        default=0.1,
        help='温度参数，0表示贪心解码（默认：0.1）'
    )

    parser.add_argument(
        '--format',
        type=str,
        choices=['instruction', 'chat'],
        default='instruction',
        help='数据格式类型（默认：instruction）'
    )

    parser.add_argument(
        '--device',
        type=str,
        default='auto',
        help='设备类型（默认：auto）'
    )

    args = parser.parse_args()

    # 加载模型
    model, tokenizer = load_model_and_tokenizer(
        base_model_path=args.base_model,
        lora_path=args.lora_path,
        device=args.device
    )

    # 批量预测
    predictions = predict_batch(
        model=model,
        tokenizer=tokenizer,
        test_file=args.test_file,
        output_file=args.output,
        batch_size=args.batch_size,
        max_new_tokens=args.max_new_tokens,
        temperature=args.temperature,
        format_type=args.format
    )

    print("✅ 全部完成！")
    print(f"\n💡 接下来可以运行评估:")
    print(f"   python evaluate.py --pred {args.output}\n")


if __name__ == "__main__":
    main()
