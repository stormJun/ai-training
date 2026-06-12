# -*- coding: utf-8 -*-
# Converted from test-agent.ipynb

# %%
from agent import graph

state = graph.invoke({"messages": [{"role": "user", "content": "Who won the euro 2024"}], "max_research_loops": 3, "initial_search_query_count": 3})

# %%
state

# %%
from IPython.display import Markdown

Markdown(state["messages"][-1].content)

# %%
state = graph.invoke({"messages": state["messages"] + [{"role": "user", "content": "How has the most titles? List the top 5"}]})

# %%
Markdown(state["messages"][-1].content)

# %%
