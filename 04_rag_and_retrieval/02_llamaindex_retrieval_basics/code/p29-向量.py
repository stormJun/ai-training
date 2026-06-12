# -*- coding: utf-8 -*-
# Converted from p29-向量.ipynb

# %%
from dotenv import load_dotenv
load_dotenv()

# %%
import numpy as np

def cosine_similarity(a, b):
    """余弦相似度"""
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))

# 示例向量
a = np.array([0.2, 0.8])
b = np.array([0.3, 0.7])
c = np.array([0.8, 0.2])

print(f"A 与 B 的余弦相似度: {cosine_similarity(a, b)}")
print(f"B 与 C 的余弦相似度: {cosine_similarity(b, c)}")
