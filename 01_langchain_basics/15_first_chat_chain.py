"""First chat chain examples for LangChain basics."""

# 本文件把原 notebook 中的基础内容整理成脚本。
# 重点包括：
# 1. 语言模型
# 2. 提示词模板
# 3. 输出解析器
# 4. 使用 LCEL 把它们组合起来

from langchain_core.prompts import ChatPromptTemplate, PromptTemplate
from langchain_core.output_parsers import CommaSeparatedListOutputParser
from langchain_community.llms.tongyi import Tongyi


def demo_prompt_template() -> None:
    """PromptTemplate 最基础的变量填充示例。"""
    prompt = PromptTemplate.from_template(
        "Hello, I am a {model_name}. How can I help you today?"
    )
    print(prompt.format(model_name="chatbot"))


def demo_chat_prompt_template() -> None:
    """ChatPromptTemplate 示例。"""
    chat_prompt = ChatPromptTemplate.from_messages(
        [
            ("system", "You are a helpful AI assistant named {assistant_name}."),
            ("human", "Hello, my name is {user_name}. {question}"),
        ]
    )

    messages = chat_prompt.format_messages(
        assistant_name="Claude",
        user_name="Alice",
        question="What's the weather like today?",
    )

    for message in messages:
        print(f"{message.type}: {message.content}")


def demo_output_parser() -> None:
    """最简单的列表输出解析器示例。"""
    parser = CommaSeparatedListOutputParser()
    raw_output = "Python, Java, JavaScript, C++, Go"
    parsed_result = parser.parse(raw_output)
    print(parsed_result)


def demo_lcel_chain() -> None:
    """LCEL: prompt | llm | parser。"""
    parser = CommaSeparatedListOutputParser()
    format_instructions = parser.get_format_instructions()

    prompt = PromptTemplate(
        template="请列出5个{category}的例子。\n{format_instructions}",
        input_variables=["category"],
        partial_variables={"format_instructions": format_instructions},
    )

    llm = Tongyi(temperature=0)
    chain = prompt | llm | parser

    # 这条链体现了 LangChain 中最常见的组合方式：
    # PromptTemplate -> 模型 -> 输出解析器
    result = chain.invoke({"category": "水果"})
    print(result)


if __name__ == "__main__":
    demo_prompt_template()
    demo_chat_prompt_template()
    demo_output_parser()
    # 需要模型配置时再打开下面这行。
    # demo_lcel_chain()
