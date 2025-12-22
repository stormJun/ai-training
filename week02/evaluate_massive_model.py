#!/usr/bin/env python3
"""
MASSIVE 意图分类模型评估脚本
"""

import json
import argparse
from pathlib import Path
from typing import Dict, List, Tuple
from tqdm import tqdm
from collections import defaultdict

try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    import torch
except ImportError:
    print("❌ 缺少依赖: pip install transformers torch")
    exit(1)


class IntentClassifierEvaluator:
    """意图分类模型评估器"""

    def __init__(self, model_path: str, device: str = "auto"):
        """
        初始化评估器

        Args:
            model_path: 模型路径
            device: 设备 (cuda/cpu/auto)
        """
        print(f"🔧 加载模型: {model_path}")

        # 自动选择设备
        if device == "auto":
            device = "cuda" if torch.cuda.is_available() else "cpu"

        self.device = device
        print(f"   设备: {device}")

        # 加载模型和分词器
        self.tokenizer = AutoTokenizer.from_pretrained(model_path, trust_remote_code=True)
        self.model = AutoModelForCausalLM.from_pretrained(
            model_path,
            trust_remote_code=True,
            torch_dtype=torch.float16 if device == "cuda" else torch.float32
        ).to(device)

        self.model.eval()
        print("✅ 模型加载完成")

    def predict_intent(self, text: str, instruction: str = None) -> str:
        """
        预测意图

        Args:
            text: 用户输入文本
            instruction: 指令（可选）

        Returns:
            预测的意图
        """
        if instruction is None:
            instruction = "请识别以下用户语句的意图分类"

        # 构建 prompt
        prompt = f"{instruction}\n{text}"

        # Tokenize
        inputs = self.tokenizer(
            prompt,
            return_tensors="pt",
            truncation=True,
            max_length=512
        ).to(self.device)

        # 生成
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=50,
                do_sample=False,
                temperature=1.0,
                top_p=1.0
            )

        # 解码
        result = self.tokenizer.decode(outputs[0], skip_special_tokens=True)

        # 提取意图部分（去掉prompt）
        if prompt in result:
            result = result.replace(prompt, "").strip()

        return result

    def evaluate(self, test_file: str, limit: int = None) -> Dict:
        """
        评估模型性能

        Args:
            test_file: 测试文件路径
            limit: 限制评估数量（可选）

        Returns:
            评估结果字典
        """
        print(f"\n📊 开始评估: {test_file}")

        # 加载测试数据
        test_data = []
        with open(test_file, 'r', encoding='utf-8') as f:
            for i, line in enumerate(f):
                if limit and i >= limit:
                    break
                if line.strip():
                    test_data.append(json.loads(line))

        print(f"   测试样本数: {len(test_data)}")

        # 评估
        correct = 0
        total = 0
        intent_stats = defaultdict(lambda: {"total": 0, "correct": 0})
        errors = []

        for item in tqdm(test_data, desc="评估中"):
            text = item["input"]
            ground_truth = item["output"]
            instruction = item.get("instruction")

            # 预测
            prediction = self.predict_intent(text, instruction)

            # 判断正确性（宽松匹配：只要包含正确意图即可）
            is_correct = ground_truth in prediction

            if is_correct:
                correct += 1

            total += 1

            # 统计各意图准确率
            intent_label = ground_truth.split("(")[0] if "(" in ground_truth else ground_truth
            intent_stats[intent_label]["total"] += 1
            if is_correct:
                intent_stats[intent_label]["correct"] += 1

            # 记录错误样本
            if not is_correct:
                errors.append({
                    "input": text,
                    "ground_truth": ground_truth,
                    "prediction": prediction
                })

        # 计算总体准确率
        accuracy = correct / total * 100

        # 计算各意图准确率
        intent_accuracy = {}
        for intent, stats in intent_stats.items():
            intent_accuracy[intent] = stats["correct"] / stats["total"] * 100

        results = {
            "total": total,
            "correct": correct,
            "accuracy": accuracy,
            "intent_accuracy": dict(sorted(intent_accuracy.items(), key=lambda x: x[1], reverse=True)),
            "errors": errors[:10]  # 只保留前10个错误样本
        }

        return results

    def print_results(self, results: Dict):
        """打印评估结果"""
        print("\n" + "=" * 60)
        print("📊 评估结果")
        print("=" * 60)
        print(f"\n总体准确率: {results['accuracy']:.2f}%")
        print(f"正确数量: {results['correct']}/{results['total']}")

        print("\n各意图准确率 (Top 10):")
        print("-" * 60)
        for i, (intent, acc) in enumerate(list(results['intent_accuracy'].items())[:10]):
            print(f"{i+1:2d}. {intent:20s} {acc:6.2f}%")

        if results['errors']:
            print("\n错误样本示例:")
            print("-" * 60)
            for i, error in enumerate(results['errors'][:5]):
                print(f"\n示例 {i+1}:")
                print(f"  输入: {error['input']}")
                print(f"  正确: {error['ground_truth']}")
                print(f"  预测: {error['prediction']}")

        print("\n" + "=" * 60)

    def save_results(self, results: Dict, output_file: str):
        """保存评估结果"""
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, indent=2, ensure_ascii=False)

        print(f"\n💾 结果已保存: {output_file}")


def main():
    parser = argparse.ArgumentParser(description="MASSIVE 意图分类模型评估")
    parser.add_argument(
        "--model",
        required=True,
        help="模型路径"
    )
    parser.add_argument(
        "--test_file",
        default="amazon_massive_intent_zh-CN/test_converted.jsonl",
        help="测试文件路径"
    )
    parser.add_argument(
        "--device",
        default="auto",
        choices=["auto", "cuda", "cpu"],
        help="运行设备"
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="限制评估样本数量（用于快速测试）"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="结果保存路径"
    )

    args = parser.parse_args()

    # 创建评估器
    evaluator = IntentClassifierEvaluator(args.model, args.device)

    # 评估
    results = evaluator.evaluate(args.test_file, args.limit)

    # 打印结果
    evaluator.print_results(results)

    # 保存结果
    if args.output:
        evaluator.save_results(results, args.output)
    else:
        # 默认保存路径
        model_name = Path(args.model).name
        output_file = f"evaluation_results_{model_name}.json"
        evaluator.save_results(results, output_file)


if __name__ == "__main__":
    main()
