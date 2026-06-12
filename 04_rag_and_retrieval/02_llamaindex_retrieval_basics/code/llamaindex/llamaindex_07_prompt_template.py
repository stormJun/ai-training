# -*- coding: utf-8 -*-
# Converted from llamaindex_07_prompt_template.ipynb

# %%
from dotenv import load_dotenv
load_dotenv()

# %%
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

# %% [markdown]
# ## 自定义提示词

# %%
from llama_index.core import PromptTemplate

template = (
    "下面是上下文信息"
    "{context_str}"
    "根据这个信息，回答问题"
    "{query_str}"
)

qa_template = PromptTemplate(template=template)
prompt = qa_template.format(context_str="今天天气怎么样", query_str="今天天气怎么样")
