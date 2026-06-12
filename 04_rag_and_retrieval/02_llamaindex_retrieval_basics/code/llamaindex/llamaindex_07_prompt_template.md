<!-- Converted from llamaindex_07_prompt_template.ipynb -->

```python
from dotenv import load_dotenv
load_dotenv()
```

```python
from llama_index.core import SummaryIndex, SimpleDirectoryReader

documents = SimpleDirectoryReader("data").load_data()

qe = SummaryIndex.from_documents(documents).as_query_engine()

prompts = qe.get_prompts()

print(prompts)

for k, p in prompts.items():
    print(f"prompt key: {k}")
    print("Text:")
    print(p.get_template())
    print("\n\n")
```

输出：

```text
{'response_synthesizer:text_qa_template': SelectorPromptTemplate(metadata={'prompt_type': <PromptType.QUESTION_ANSWER: 'text_qa'>}, template_vars=['context_str', 'query_str'], kwargs={}, output_parser=None, template_var_mappings={}, function_mappings={}, default_template=PromptTemplate(metadata={'prompt_type': <PromptType.QUESTION_ANSWER: 'text_qa'>}, template_vars=['context_str', 'query_str'], kwargs={}, output_parser=None, template_var_mappings=None, function_mappings=None, template='Context information is below.\n---------------------\n{context_str}\n---------------------\nGiven the context information and not prior knowledge, answer the query.\nQuery: {query_str}\nAnswer: '), conditionals=[(<function is_chat_model at 0x0000017DBF047740>, ChatPromptTemplate(metadata={'prompt_type': <PromptType.CUSTOM: 'custom'>}, template_vars=['context_str', 'query_str'], kwargs={}, output_parser=None, template_var_mappings=None, function_mappings=None, message_templates=[ChatMessage(role=<MessageRole.SYSTEM: 'system'>, additional_kwargs={}, blocks=[TextBlock(block_type='text', text="You are an expert Q&A system that is trusted around the world.\nAlways answer the query using the provided context information, and not prior knowledge.\nSome rules to follow:\n1. Never directly reference the given context in your answer.\n2. Avoid statements like 'Based on the context, ...' or 'The context information ...' or anything along those lines.")]), ChatMessage(role=<MessageRole.USER: 'user'>, additional_kwargs={}, blocks=[TextBlock(block_type='text', text='Context information is below.\n---------------------\n{context_str}\n---------------------\nGiven the context information and not prior knowledge, answer the query.\nQuery: {query_str}\nAnswer: ')])]))]), 'response_synthesizer:refine_template': SelectorPromptTemplate(metadata={'prompt_type': <PromptType.REFINE: 'refine'>}, template_vars=['query_str', 'existing_answer', 'context_msg'], kwargs={}, output_parser=None, template_var_mappings={}, function_mappings={}, default_template=PromptTemplate(metadata={'prompt_type': <PromptType.REFINE: 'refine'>}, template_vars=['query_str', 'existing_answer', 'context_msg'], kwargs={}, output_parser=None, template_var_mappings=None, function_mappings=None, template="The original query is as follows: {query_str}\nWe have provided an existing answer: {existing_answer}\nWe have the opportunity to refine the existing answer (only if needed) with some more context below.\n------------\n{context_msg}\n------------\nGiven the new context, refine the original answer to better answer the query. If the context isn't useful, return the original answer.\nRefined Answer: "), conditionals=[(<function is_chat_model at 0x0000017DBF047740>, ChatPromptTemplate(metadata={'prompt_type': <PromptType.CUSTOM: 'custom'>}, template_vars=['context_msg', 'query_str', 'existing_answer'], kwargs={}, output_parser=None, template_var_mappings=None, function_mappings=None, message_templates=[ChatMessage(role=<MessageRole.USER: 'user'>, additional_kwargs={}, blocks=[TextBlock(block_type='text', text="You are an expert Q&A system that strictly operates in two modes when refining existing answers:\n1. **Rewrite** an original answer using the new context.\n2. **Repeat** the original answer if the new context isn't useful.\nNever reference the original answer or context directly in your answer.\nWhen in doubt, just repeat the original answer.\nNew Context: {context_msg}\nQuery: {query_str}\nOriginal Answer: {existing_answer}\nNew Answer: ")])]))])}
prompt key: response_synthesizer:text_qa_template
Text:
Context information is below.
---------------------
{context_str}
---------------------
Given the context information and not prior knowledge, answer the query.
Query: {query_str}
Answer:



prompt key: response_synthesizer:refine_template
Text:
The original query is as follows: {query_str}
We have provided an existing answer: {existing_answer}
We have the opportunity to refine the existing answer (only if needed) with some more context below.
------------
{context_msg}
------------
Given the new context, refine the original answer to better answer the query. If the context isn't useful, return the original answer.
Refined Answer:



```

## 自定义提示词

```python
from llama_index.core import PromptTemplate

template = (
    "下面是上下文信息"
    "{context_str}"
    "根据这个信息，回答问题"
    "{query_str}"
)

qa_template = PromptTemplate(template=template)
prompt = qa_template.format(context_str="今天天气怎么样", query_str="今天天气怎么样")
```
