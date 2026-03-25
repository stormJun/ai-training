"""RAGAS 全指标示例（检索阶段 + 生成阶段）。

这个脚本演示了如何在 03_rag_and_retrieval/llamaindex_and_ragas 中一次性运行 RAGAS 的核心指标：
1. 检索阶段指标：context_precision、context_recall
2. 生成阶段指标：faithfulness、answer_correctness、answer_similarity、answer_relevancy

运行前准备：
1. 在 03_rag_and_retrieval/llamaindex_and_ragas 目录执行 `uv sync --locked`
2. 确保 `03_rag_and_retrieval/llamaindex_and_ragas/code/.env` 中已配置真实的 `DASHSCOPE_API_KEY`

运行命令：
    cd 03_rag_and_retrieval/llamaindex_and_ragas
    source .venv/bin/activate
    python code/ragas/ragas_full_metrics_demo.py
"""

from __future__ import annotations

import os
from copy import deepcopy
from pathlib import Path

# HuggingFace Dataset，用来构造 evaluate() 所需数据集对象
from datasets import Dataset
# 从 .env 文件加载环境变量
from dotenv import load_dotenv
# 通义千问 Embedding 模型封装（用于语义相似度/相关性类指标）
from langchain_community.embeddings import DashScopeEmbeddings
# 通义千问 LLM 封装（用于 LLM 判分类指标）
from langchain_community.llms.tongyi import Tongyi
# RAGAS 主评测入口
from ragas import evaluate
# 本示例用到的 6 个核心指标
from ragas.metrics import (
    answer_correctness,
    answer_relevancy,
    answer_similarity,
    context_precision,
    context_recall,
    faithfulness,
)
from ragas_chinese_prompts import (
    AnswerCorrectness,
    AnswerRelavency,
    ContextPrecision,
    ContextRecall,
    Faithfulness,
)

# 关闭 GitPython 刷新提示，避免终端输出干扰
os.environ["GIT_PYTHON_REFRESH"] = "quiet"

# 先深拷贝指标对象，再用于评测，避免直接使用全局单例指标。
# 这样即使后续要做 prompt 定制，也不会污染其它脚本/任务中的默认指标。
eval_context_precision = deepcopy(context_precision)
eval_context_recall = deepcopy(context_recall)
eval_faithfulness = deepcopy(faithfulness)
eval_answer_correctness = deepcopy(answer_correctness)
eval_answer_similarity = deepcopy(answer_similarity)
eval_answer_relevancy = deepcopy(answer_relevancy)

def _apply_prompt(prompt_obj, prompt_data: dict) -> None:
    """将中文 Prompt 内容写入指标 Prompt 对象（兼容不同 ragas 版本字段）。"""
    if "instruction" in prompt_data and hasattr(prompt_obj, "instruction"):
        prompt_obj.instruction = prompt_data["instruction"]
    if "examples" in prompt_data and hasattr(prompt_obj, "examples"):
        prompt_obj.examples = prompt_data["examples"]
    if (
        "output_format_instruction" in prompt_data
        and hasattr(prompt_obj, "output_format_instruction")
    ):
        prompt_obj.output_format_instruction = prompt_data["output_format_instruction"]


# 适配中文 Prompt：只改当前脚本使用的深拷贝指标对象，不污染全局默认指标。
_apply_prompt(
    eval_answer_relevancy.question_generation,
    AnswerRelavency.question_generation_prompt,
)
_apply_prompt(
    eval_faithfulness.nli_statements_prompt,
    Faithfulness.nli_statements_message_prompt,
)
_apply_prompt(
    eval_faithfulness.statement_generator_prompt,
    Faithfulness.statement_prompt,
)
_apply_prompt(
    eval_context_recall.context_recall_prompt,
    ContextRecall.context_recall_prompt,
)
_apply_prompt(
    eval_context_precision.context_precision_prompt,
    ContextPrecision.context_precision_prompt,
)
_apply_prompt(
    eval_answer_correctness.correctness_prompt,
    AnswerCorrectness.correctness_prompt,
)


def build_dataset() -> Dataset:
    """构造演示用评测数据集。

    字段说明：
    - question: 用户问题
    - answer: 模型回答（待评测对象）
    - ground_truth: 参考标准答案
    - contexts: 检索到的上下文（每个问题对应一个 list[str]）
    """
    data_samples = {
        "question": [
            "杭州最值得去的景点有哪些？",
            "去成都旅游的话，有哪些特色美食推荐？",
            "在西安游览时，参观兵马俑需要提前预约吗？",
        ],
        "answer": [
            "杭州西湖、灵隐寺和千岛湖是比较受欢迎的景点。",
            "成都有很多好吃的，比如火锅、串串香和担担面。",
            "参观兵马俑不需要预约，现场买票就可以进去。",
        ],
        "ground_truth": [
            "杭州必游景点包括西湖、灵隐寺、雷峰塔、千岛湖和宋城，其中西湖是国家5A级景区，建议清晨游览以避开人流。",
            "成都作为美食之都，推荐品尝火锅、串串香、担担面、龙抄手和钟水饺，宽窄巷子和锦里是集中体验地道小吃的好去处。",
            "参观秦始皇兵马俑博物馆必须通过官方平台提前实名预约购票，旺季时需至少提前3天预约，现场不保证有票。",
        ],
        "contexts": [
            [
                "西湖是杭州的核心景区，国家5A级旅游景点，以湖光山色和历史文化闻名。",
                "灵隐寺是中国著名的佛教古刹，位于杭州西湖区。",
                "千岛湖以湖泊和岛屿景观著称，适合度假与户外活动。",
            ],
            [
                "成都被誉为“美食之都”，火锅是其代表性饮食，麻辣鲜香。",
                "串串香起源于四川街头，食材丰富，可自选。",
                "担担面是川菜经典面食，以红油和肉末调味。",
            ],
            [
                "秦始皇兵马俑位于陕西省西安市临潼区，是世界文化遗产。",
                "兵马俑博物馆实行实名制预约购票制度，建议提前在官网或官方公众号预约。",
                "旺季参观需至少提前3天预约，避免现场无票。",
            ],
        ],
    }
    # 将 dict 转为 HuggingFace Dataset，供 ragas.evaluate 使用
    return Dataset.from_dict(data_samples)


def main() -> None:
    """执行完整评测流程。"""
    # 优先读取当前目录 .env；若不存在，再读取上级 code/.env。
    # 这样脚本迁移到 code/ragas 后，仍可复用 03_rag_and_retrieval/llamaindex_and_ragas/code/.env。
    script_dir = Path(__file__).resolve().parent
    load_dotenv(script_dir / ".env", override=False)
    load_dotenv(script_dir.parent / ".env", override=False)

    # 读取通义千问 Key
    api_key = os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        raise EnvironmentError(
            "未检测到 DASHSCOPE_API_KEY。请先在 03_rag_and_retrieval/llamaindex_and_ragas/code/.env 中配置后再运行。"
        )
    # 防止占位符或明显错误的 key 被误用，导致整批评测结果都是 NaN
    if (
        api_key == "YOUR_API_KEY_HERE"
        or "your" in api_key.lower()
        or not api_key.startswith("sk-")
    ):
        raise EnvironmentError(
            "DASHSCOPE_API_KEY 看起来是占位值或格式错误。"
            "请使用真实的 sk- 开头密钥，并确认环境变量名是 DASHSCOPE_API_KEY。"
        )

    # 1) 准备评测数据
    dataset = build_dataset()

    # 2) 初始化评测所需模型
    # temperature=0 用于降低评估随机性，便于结果复现
    llm = Tongyi(model_name="qwen-plus", temperature=0)
    embeddings = DashScopeEmbeddings(model="text-embedding-v3")

    # 3) 指标分组（便于理解和扩展）
    # 检索阶段：评估“找得准不准、全不全”
    retrieval_metrics = [eval_context_precision, eval_context_recall]
    # 生成阶段：评估“答案真实、正确、相似、相关”
    generation_metrics = [
        eval_faithfulness,
        eval_answer_correctness,
        eval_answer_similarity,
        eval_answer_relevancy,
    ]

    # 4) 执行评测
    # raise_exceptions=True 表示只要某个任务失败就立即抛错，避免静默 NaN
    result = evaluate(
        dataset=dataset,
        metrics=retrieval_metrics + generation_metrics,
        llm=llm,
        embeddings=embeddings,
        raise_exceptions=True,
    )

    # 5) 结果分析
    # to_pandas() 返回逐样本分数明细，便于定位低分样本
    df = result.to_pandas()
    print("评估明细：")
    print(df)
    # numeric_only=True 仅对数值列求均值，输出指标总体表现
    print("\n各指标均值：")
    print(df.mean(numeric_only=True))


if __name__ == "__main__":
    # 脚本入口
    main()
