"""中文评测版 RAGAS 示例（中文 Prompt + 多指标组合）。

这个脚本的核心目标：
1. 将 RAGAS 默认英文评测提示词替换为中文版本
2. 一次性运行多个常用指标，适合上线前做离线质量评估
3. 为中文业务场景降低评分偏差（尤其是 Faithfulness/Relevancy 类指标）

注意：
- 本脚本更适合离线评估与回归，不建议放到在线请求链路实时调用
- 需在 `week03/code/ragas` 目录下运行（依赖本地 `ragas_chinese_prompts.py`）
"""

import os
from copy import deepcopy
from pathlib import Path

from datasets import Dataset
from dotenv import load_dotenv
from langchain_community.embeddings import DashScopeEmbeddings
from llama_index.llms.openai_like import OpenAILike
from ragas import evaluate as ragas_evaluate
from ragas.metrics import (
    answer_correctness,
    answer_relevancy,
    context_precision,
    context_recall,
    faithfulness,
)

from ragas_chinese_prompts import *

# 读取本目录或上级 code 目录下的 .env，方便直接运行脚本
script_dir = Path(__file__).resolve().parent
load_dotenv(script_dir / ".env", override=False)
load_dotenv(script_dir.parent / ".env", override=False)

# 先深拷贝指标对象，再覆盖 Prompt，避免污染全局单例指标。
# 这样本脚本的中文 Prompt 改动只在当前 zh_* 指标对象上生效。
zh_answer_relevancy = deepcopy(answer_relevancy)
zh_faithfulness = deepcopy(faithfulness)
zh_context_recall = deepcopy(context_recall)
zh_context_precision = deepcopy(context_precision)
zh_answer_correctness = deepcopy(answer_correctness)

def _apply_prompt(prompt_obj, prompt_data: dict) -> None:
    """将中文 Prompt 内容写入目标 Prompt 对象（兼容不同 ragas 版本字段）。"""
    if "instruction" in prompt_data and hasattr(prompt_obj, "instruction"):
        prompt_obj.instruction = prompt_data["instruction"]
    if "examples" in prompt_data and hasattr(prompt_obj, "examples"):
        prompt_obj.examples = prompt_data["examples"]
    if (
        "output_format_instruction" in prompt_data
        and hasattr(prompt_obj, "output_format_instruction")
    ):
        prompt_obj.output_format_instruction = prompt_data["output_format_instruction"]


# 适配到中文 Prompt（定义见 `week03/code/ragas/ragas_chinese_prompts.py`）
_apply_prompt(
    zh_answer_relevancy.question_generation,
    AnswerRelavency.question_generation_prompt,
)

# 兼容新版 ragas 字段名：nli_statements_prompt / statement_generator_prompt
_apply_prompt(
    zh_faithfulness.nli_statements_prompt,
    Faithfulness.nli_statements_message_prompt,
)
_apply_prompt(
    zh_faithfulness.statement_generator_prompt,
    Faithfulness.statement_prompt,
)

_apply_prompt(
    zh_context_recall.context_recall_prompt,
    ContextRecall.context_recall_prompt,
)
_apply_prompt(
    zh_context_precision.context_precision_prompt,
    ContextPrecision.context_precision_prompt,
)
_apply_prompt(
    zh_answer_correctness.correctness_prompt,
    AnswerCorrectness.correctness_prompt,
)

# 定义评测所需模型
# - llm: 用于各类 LLM 判分类指标（如 faithfulness / correctness）
# - embedding: 用于向量相似度相关计算
llm = OpenAILike(
    model="qwen-plus",
    api_base="https://dashscope.aliyuncs.com/compatible-mode/v1",
    api_key=os.getenv("DASHSCOPE_API_KEY"),
    is_chat_model=True
)
embedding = DashScopeEmbeddings(model="text-embedding-v3")


def evaluate(
    question: list[str],
    answer: list[str],
    contexts: list[list[str]],
    ground_truth: list[str],
):
    """对一批中文样本执行多指标评测并返回 DataFrame。

    参数约束：
    - 四个列表长度必须一致
    - `contexts` 是按样本组织的二维结构：`list[list[str]]`
    """
    # 1) 组装评测数据
    data_samples = {
        "question": question,
        "answer": answer,
        "contexts": contexts,
        "ground_truth": ground_truth,
    }

    # 2) 转换为 HuggingFace Dataset，供 ragas.evaluate 使用
    dataset = Dataset.from_dict(data_samples)

    # 3) 执行评测
    # 指标组合说明：
    # - answer_correctness: 回答正确性
    # - answer_relevancy: 回答与问题相关性
    # - context_recall / context_precision: 检索阶段质量
    # - faithfulness: 回答是否忠实于上下文（抗幻觉）
    score = ragas_evaluate(
        dataset=dataset,
        metrics=[
            zh_answer_correctness,
            zh_answer_relevancy,
            zh_context_recall,
            zh_context_precision,
            zh_faithfulness,
        ],
        embeddings=embedding,
        llm=llm,
    )

    # 4) 返回明细结果，便于进一步做均值、分位数、低分样本分析
    df = score.to_pandas()
    return df
