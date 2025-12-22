# CLIP 图像搜索系统完全指南

## 目录

- [第一部分：系统概述](#第一部分系统概述)
  - [1.1 CLIP 简介](#11-clip-简介)
  - [1.2 系统架构](#12-系统架构)
  - [1.3 核心特性](#13-核心特性)
  - [1.4 应用场景](#14-应用场景)
- [第二部分：技术原理](#第二部分技术原理)
  - [2.1 CLIP 模型原理](#21-clip-模型原理)
  - [2.2 向量数据库 Milvus](#22-向量数据库-milvus)
  - [2.3 相似度检索算法](#23-相似度检索算法)
- [第三部分：环境搭建](#第三部分环境搭建)
  - [3.1 系统要求](#31-系统要求)
  - [3.2 依赖安装](#32-依赖安装)
  - [3.3 配置说明](#33-配置说明)
- [第四部分：核心模块详解](#第四部分核心模块详解)
  - [4.1 CLIP 编码器模块](#41-clip-编码器模块)
  - [4.2 Milvus 数据库管理模块](#42-milvus-数据库管理模块)
  - [4.3 图像处理模块](#43-图像处理模块)
  - [4.4 搜索系统主模块](#44-搜索系统主模块)
- [第五部分：快速开始](#第五部分快速开始)
  - [5.1 基础使用流程](#51-基础使用流程)
  - [5.2 文本搜索图像](#52-文本搜索图像)
  - [5.3 以图搜图](#53-以图搜图)
- [第六部分：高级功能](#第六部分高级功能)
  - [6.1 批量图像索引](#61-批量图像索引)
  - [6.2 增量索引更新](#62-增量索引更新)
  - [6.3 搜索结果可视化](#63-搜索结果可视化)
- [第七部分：实战案例](#第七部分实战案例)
  - [7.1 电商图片搜索](#71-电商图片搜索)
  - [7.2 素材库管理](#72-素材库管理)
  - [7.3 图像去重](#73-图像去重)
  - [7.4 商标检索](#74-商标检索)
- [第八部分：性能优化](#第八部分性能优化)
- [第九部分：问题排查与调试](#第九部分问题排查与调试)

---

# 第一部分：系统概述

## 1.1 CLIP 简介

### 什么是 CLIP？

**CLIP (Contrastive Language-Image Pre-Training)**: OpenAI 推出的多模态深度学习模型，能够理解图像和文本之间的语义关联。

```
传统图像搜索:
  - 基于关键词标签 (人工标注)
  - 基于图像特征 (颜色、纹理等)
  - 局限性: 无法理解语义

CLIP 图像搜索:
  - 基于自然语言描述
  - 理解图像��语义内容
  - 支持跨模态检索 (文本 → 图像, 图像 → 图像)
```

---

### CLIP 核心能力

```python
# CLIP 的三大核心能力

1. 图像编码 (Image Encoding)
   - 将图像转换为 512 维特征向量
   - 捕捉图像的语义信息
   - 归一化表示，支持余弦相似度计算

2. 文本编码 (Text Encoding)
   - 将自然语言文本转换为 512 维特征向量
   - 与图像在同一向量空间
   - 支持零样本分类

3. 跨模态匹配 (Cross-Modal Matching)
   - 文本查询图像
   - 图像查询相似图像
   - 语义相似度计算
```

---

### CLIP vs 传统方法对比

| 特性 | 传统图像搜索 | CLIP 图像搜索 |
|------|------------|--------------|
| **搜索方式** | 关键词标签 | 自然语言描述 |
| **标注成本** | 需要大量人工标注 | 无需标注 |
| **语义理解** | ✗ | ✓ |
| **跨模态检索** | ✗ | ✓ |
| **零样本能力** | ✗ | ✓ |
| **搜索精度** | 依赖标签质量 | 语义级别匹配 |

**示例对比**:
```
查询: "a photo of a cat wearing sunglasses"

传统方法:
  - 需要标签: ["cat", "sunglasses"]
  - 可能匹配: 猫 + 太阳镜 (即使不在一起)

CLIP:
  - 理解语义: "戴着太阳镜的猫"
  - 精确匹配: 猫戴太阳镜的照片
```

---

## 1.2 系统架构

### 整体架构图

```
┌─────────────────────────────────────────────────────────┐
│                   应用层                                 │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐  │
│  │  Web 界面    │  │  API 服务    │  │  命令行工具  │  │
│  └──────────────┘  └──────────────┘  └──────────────┘  │
└─────────────────────────────────────────────────────────┘
                           ↓
┌─────────────────────────────────────────────────────────┐
│              CLIP 图像搜索系统 (核心层)                  │
│                                                          │
│  ┌──────────────────────────────────────────────────┐  │
│  │        CLIPImageSearchSystem                      │  │
│  │  - setup_database()    设置数据库                 │  │
│  │  - index_images()      索引图像                   │  │
│  │  - search_by_text()    文本搜索                   │  │
│  │  - search_by_image()   以图搜图                   │  │
│  └──────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
            ↓                  ↓                  ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  CLIP 编码器    │  │  Milvus 管理器  │  │  图像处理器     │
│                 │  │                 │  │                 │
│ - encode_image  │  │ - create_coll   │  │ - get_paths     │
│ - encode_text   │  │ - insert_data   │  │ - filter_valid  │
│ - batch_encode  │  │ - search        │  │ - display       │
└─────────────────┘  └─────────────────┘  └─────────────────┘
         ↓                    ↓                    ↓
┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐
│  CLIP 模型      │  │  Milvus 数据库  │  │  图像文件       │
│  (PyTorch)      │  │  (向量存储)     │  │  (本地/云端)    │
└─────────────────┘  └─────────────────┘  └─────────────────┘
```

---

### 数据流程图

```
图像索引流程:
┌──────────────┐
│  图像目录     │
└──────┬───────┘
       │ 1. 扫描图像文件
       ▼
┌──────────────────┐
│  图像路径列表     │
└──────┬───────────┘
       │ 2. 过滤有效图像
       ▼
┌──────────────────┐
│  有效图像列表     │
└──────┬───────────┘
       │ 3. CLIP 编码
       ▼
┌──────────────────┐
│  512 维向量列表  │
└──────┬───────────┘
       │ 4. 插入 Milvus
       ▼
┌──────────────────┐
│  向量数据库      │
└──────────────────┘

搜索流程:
┌──────────────┐
│  查询输入     │
│ (文本/图像)   │
└──────┬───────┘
       │ 1. CLIP 编码
       ▼
┌──────────────────┐
│  查询向量        │
│  (512 维)        │
└──────┬───────────┘
       │ 2. 向量检索 (HNSW)
       ▼
┌──────────────────┐
│  相似度排序      │
│  Top-K 结果      │
└──────┬───────────┘
       │ 3. 结果展示
       ▼
┌──────────────────┐
│  相似图像列表    │
└──────────────────┘
```

---

## 1.3 核心特性

### 1. 零样本搜索

```python
# 无需训练，直接搜索
search_system.search_by_text("red sports car")
# 即使从未见过这个描述，也能准确匹配
```

**优势**:
- 无需标注数据
- 无需模型微调
- 支持任意自然语言查询

---

### 2. 跨模态检索

```python
# 文本 → 图像
search_system.search_by_text("sunset over the ocean")

# 图像 → 图像
search_system.search_by_image("reference_image.jpg")
```

**应用场景**:
- 电商: "红色连衣裙" → 商品图
- 版权: 上传图片 → 找相似图
- 社交: 描述场景 → 找照片

---

### 3. 高性能向量检索

```python
# Milvus HNSW 索引
索引参数:
  - index_type: "HNSW"
  - metric_type: "COSINE"
  - M: 8              # 邻居数
  - efConstruction: 64 # 构建时搜索深度

性能指标:
  - 百万级数据: < 100ms
  - 准确率: > 95%
  - 支持分布式扩展
```

---

### 4. 增量索引

```python
# 自动检测已索引图像
search_system.index_images(skip_existing=True)

# 只索引新增图像，提升效率
```

---

## 1.4 应用场景

### 电商场景

```
以图搜图购物:
  1. 用户上传喜欢的商品图片
  2. 系统查找相似商品
  3. 展示推荐结果

自然语言搜索:
  用户输入: "蓝色牛仔裤"
  系统返回: 所有蓝色牛仔裤商品图

效果:
  - 搜索准确率: +40%
  - 用户转化率: +25%
```

---

### 设计素材管理

```
素材库搜索:
  场景 1: "minimalist logo design"
         → 极简风格的 Logo 设计

  场景 2: "vibrant poster with typography"
         → 有文字的鲜艳海报

  场景 3: 上传参考图
         → 找相似风格的设计

效果:
  - 设计师查找时间: 30分钟 → 2分钟
  - 素材复用率: +60%
```

---

### 内容审核

```
违规图像检测:
  1. 索引已知违规图像库
  2. 新上传图片自动检索
  3. 相似度 > 阈值 → 标记审核

效果:
  - 审核效率: +80%
  - 误报率: < 2%
```

---

### 版权保护

```
图像版权检测:
  1. 版权方上传原图
  2. 系统检索互联网图库
  3. 发现相似图像 (盗图)

效果:
  - 检测准确率: 98%
  - 检测速度: 10万张/分钟
```

---

# 第二部分：技术原理

## 2.1 CLIP 模型原理

### CLIP 训练方式

```
对比学习 (Contrastive Learning):

数据集:
  - 4亿 (图像, 文本) 对
  - 从互联网收集
  - 覆盖海量概念

训练目标:
  - 匹配的 (图像, 文本) 对: 相似度最大化
  - 不匹配的对: 相似度最小化

┌──────────────┐      ┌──────────────┐
│  图像编码器   │      │  文本编码器   │
│ (Vision      │      │ (Transformer) │
│  Transformer)│      │              │
└──────┬───────┘      └──────┬───────┘
       │                     │
       ▼                     ▼
  ┌─────────┐          ┌─────────┐
  │ 图像向量 │          │ 文本向量 │
  │ (512维) │          │ (512维) │
  └────┬────┘          └────┬────┘
       │                     │
       └──────────┬──────────┘
                  ▼
          ┌───────────────┐
          │  余弦相似度    │
          │  Cosine       │
          │  Similarity   │
          └───────────────┘
```

---

### 特征向量归一化

```python
# CLIP 编码过程
def encode_image(image):
    # 1. 图像预处理 (Resize, Normalize)
    image_tensor = preprocess(image)

    # 2. 提取特征
    features = model.encode_image(image_tensor)
    # 输出: [batch_size, 512]

    # 3. L2 归一化 (关键步骤!)
    features = features / features.norm(dim=-1, keepdim=True)
    # 归一化后的向量长度为 1

    return features

# 为什么要归一化?
# 1. 使用余弦相似度代替欧氏距离
# 2. 相似度范围固定: [-1, 1]
# 3. 提升检索准确性
```

---

### CLIP 模型变体

| 模型名称 | 参数量 | 特征维度 | 速度 | 精度 | 推荐场景 |
|---------|--------|---------|------|------|---------|
| **ViT-B/32** | 151M | 512 | ★★★★ | ★★★ | 通用场景 (默认) |
| **ViT-B/16** | 149M | 512 | ★★★ | ★★★★ | 高精度需求 |
| **ViT-L/14** | 427M | 768 | ★★ | ★★★★★ | 最高精度 |
| **RN50** | 102M | 1024 | ★★★★★ | ★★ | 速度优先 |

**选择建议**:
```python
# 本项目默认使用 ViT-B/32
config.clip.model_name = "ViT-B/32"
config.clip.feature_dimension = 512

# 高精度场景
config.clip.model_name = "ViT-L/14"
config.clip.feature_dimension = 768
```

---

## 2.2 向量数据库 Milvus

### 什么是向量数据库？

传统数据库存储**结构化数据** (数字、文本)，向量数据库存储**高维向量** (嵌入向量)。

```
传统数据库:
  SELECT * FROM products WHERE name = 'iPhone';

向量数据库:
  SELECT * FROM images
  ORDER BY cosine_similarity(vector, query_vector)
  LIMIT 10;
```

---

### Milvus 核心概念

```python
# 1. 集合 (Collection)
类似于传统数据库的"表"
存储向量和元数据

collection = {
    "name": "image_collection",
    "schema": {
        "id": "int64",           # 主键
        "vector": "float[512]",  # 向量字段
        "filepath": "string"     # 元数据
    }
}

# 2. 索引 (Index)
加速向量检索的数据结构

index = {
    "type": "HNSW",         # 层次可导航小世界图
    "metric": "COSINE",     # 余弦相似度
    "params": {
        "M": 8,             # 每层最多邻居数
        "efConstruction": 64 # 构建时搜索深度
    }
}

# 3. 分区 (Partition) - 可选
逻辑分组，提升查询效率

partitions = ["2024-01", "2024-02", ...]
```

---

### HNSW 索引原理

**HNSW (Hierarchical Navigable Small World)**: 层次化图结构索引

```
层次结构:
Layer 2:  A ─────────────── Z  (稀疏层, 长距离跳跃)
           │                 │
Layer 1:  A ─── B ─── C ─── Z  (中等密度)
           │    │    │    │
Layer 0:  A─B─C─D─E─F─...─Z   (稠密层, 精确搜索)

搜索过程:
  1. 从顶层开始
  2. 贪心向目标靠近
  3. 逐层下降
  4. 在底层精确搜索

时间复杂度: O(log N)
准确率: > 95%
```

---

### Milvus vs 其他向量库

| 特性 | Milvus | FAISS | Qdrant | Weaviate |
|------|--------|-------|--------|----------|
| **分布式** | ✓ | ✗ | ✓ | ✓ |
| **实时更新** | ✓ | ✗ | ✓ | ✓ |
| **多种索引** | ✓ | ✓ | ✗ | ✗ |
| **GPU 加速** | ✓ | ✓ | ✗ | ✗ |
| **云原生** | ✓ | ✗ | ✓ | ✓ |
| **易用性** | ★★★★ | ★★ | ★★★★★ | ★★★★ |

**选择 Milvus 的理由**:
- 生产级性能 (百万级数据 < 100ms)
- 支持多种索引算法
- 完善的 Python SDK
- 活跃的社区支持

---

## 2.3 相似度检索算法

### 余弦相似度

```python
# 数学公式
cosine_similarity(A, B) = (A · B) / (||A|| × ||B||)

# 归一化向量的简化
# 当 ||A|| = ||B|| = 1 时:
cosine_similarity(A, B) = A · B  (内积)

# 实现示例
import numpy as np

def cosine_similarity(vec1, vec2):
    """计算两个向量的余弦相似度"""
    # 向量已归一化,直接计算内积
    return np.dot(vec1, vec2)

# 相似度范围: [-1, 1]
# 1: 完全相同
# 0: 正交 (无关)
# -1: 完全相反
```

---

### Top-K 检索

```python
# 检索最相似的 K 个结果
def search_top_k(query_vector, database_vectors, k=10):
    """
    query_vector: 查询向量 (512,)
    database_vectors: 数据库向量 (N, 512)
    k: 返回数量
    """
    # 1. 计算所有相似度
    similarities = database_vectors @ query_vector
    # shape: (N,)

    # 2. 排序并取 Top-K
    top_k_indices = np.argsort(similarities)[-k:][::-1]
    top_k_scores = similarities[top_k_indices]

    return top_k_indices, top_k_scores

# Milvus 内部优化:
# - 使用 HNSW 索引,无需遍历所有向量
# - 近似最近邻 (ANN) 算法
# - 速度提升 100-1000 倍
```

---

### 检索精度与召回率

```
精度 (Precision):
  检索结果中真正相关的比例
  Precision = 相关结果数 / 总结果数

召回率 (Recall):
  所有相关结果中被检索到的比例
  Recall = 检索到的相关数 / 实际相关总数

权衡:
  ┌─────────────────────────────────┐
  │  提升精度 ←→ 提升召回            │
  │  (返回少但准) (返回多但全)       │
  └─────────────────────────────────┘

HNSW 参数调优:
  - M ↑: 精度 ↑, 速度 ↓
  - efConstruction ↑: 精度 ↑, 索引时间 ↓
  - efSearch ↑: 召回 ↑, 查询速度 ↓
```

---

# 第三部分:环境搭建

## 3.1 系统要求

### 硬件要求

```
最低配置:
  - CPU: 4 核心
  - 内存: 8 GB
  - 存储: 20 GB
  - GPU: 无 (可用 CPU 运行)

推荐配置:
  - CPU: 8 核心+
  - 内存: 16 GB+
  - 存储: SSD 100 GB+
  - GPU: NVIDIA GPU (4GB+ 显存)

生产环境:
  - CPU: 16 核心+
  - 内存: 32 GB+
  - 存储: SSD 500 GB+
  - GPU: NVIDIA GPU (8GB+ 显存)
  - Milvus 分布式集群
```

---

### 软件要求

```
操作系统:
  - macOS 10.15+
  - Ubuntu 18.04+
  - Windows 10+

Python:
  - Python 3.8+
  - 推荐: Python 3.11

依赖服务:
  - Milvus (可选, 支持 Lite 模式)
  - Docker (可选, 用于部署 Milvus)
```

---

## 3.2 依赖安装

### 步骤 1: 安装 Python 依赖

```bash
cd week07/standalone_projects/p25-CLIP

# 安装核心依赖
pip install -r requirements.txt

# requirements.txt 内容:
# pymilvus>=2.3.0        # Milvus Python SDK
# pillow>=9.0.0          # 图像处理
# torch>=1.12.0          # PyTorch
# torchvision>=0.13.0    # 计算机视觉
# matplotlib>=3.5.0      # 可视化
# numpy>=1.21.0          # 数值计算
# pyyaml>=6.0            # 配置文件

# 安装 CLIP 模型
pip install git+https://github.com/openai/CLIP.git
```

---

### 步骤 2: 安装 Milvus (可选)

**方式 1: Milvus Lite (推荐新手)**
```python
# 无需额外安装, pymilvus 自带
# 数据存储在本地文件
# 适合: 开发、测试、小规模应用

from pymilvus import MilvusClient
client = MilvusClient()  # 自动使用 Lite 模式
```

**方式 2: Milvus Standalone (推荐生产)**
```bash
# 使用 Docker Compose 部署
wget https://github.com/milvus-io/milvus/releases/download/v2.3.0/milvus-standalone-docker-compose.yml -O docker-compose.yml

# 启动 Milvus
docker-compose up -d

# 检查状态
docker-compose ps

# 连接 Milvus
from pymilvus import MilvusClient
client = MilvusClient(uri="http://localhost:19530")
```

**方式 3: Milvus 分布式集群**
```bash
# 使用 Helm 部署到 Kubernetes
# 详见官方文档: https://milvus.io/docs/install_cluster-helm.md
```

---

### 步骤 3: 验证安装

```python
# test_installation.py

import torch
import clip
from pymilvus import MilvusClient

def test_clip():
    """测试 CLIP 模型"""
    print("测试 CLIP 模型...")
    model, preprocess = clip.load("ViT-B/32")
    print(f"✓ CLIP 模型加载成功")
    print(f"  设备: {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    return True

def test_milvus():
    """测试 Milvus 连接"""
    print("\n测试 Milvus 连接...")
    client = MilvusClient()
    collections = client.list_collections()
    print(f"✓ Milvus 连接成功")
    print(f"  现有集合: {collections}")
    return True

if __name__ == "__main__":
    test_clip()
    test_milvus()
    print("\n所有组件安装成功! 🎉")
```

运行测试:
```bash
python test_installation.py
```

---

## 3.3 配置说明

### 配置文件结构

```python
# config.py

from dataclasses import dataclass
from typing import Dict, Any

@dataclass
class CLIPConfig:
    """CLIP 模型配置"""
    model_name: str = "ViT-B/32"        # 模型名称
    feature_dimension: int = 512        # 特征维度

@dataclass
class MilvusConfig:
    """Milvus 数据库配置"""
    collection_name: str = "image_collection"  # 集合名称
    index_name: str = "hnsw_index"            # 索引名称
    index_type: str = "HNSW"                  # 索引类型
    metric_type: str = "COSINE"               # 相似度度量
    index_params: Dict[str, Any] = None       # 索引参数

    def __post_init__(self):
        if self.index_params is None:
            self.index_params = {
                "M": 8,                # HNSW 参数: 邻居数
                "efConstruction": 64   # HNSW 参数: 构建时搜索深度
            }

@dataclass
class ImageConfig:
    """图像处理配置"""
    image_directory: str = "./reverse_image_search/train"  # 图像目录
    image_extensions: tuple = ("*.JPEG", "*.jpg", "*.png", "*.bmp")  # 支持格式
    thumbnail_size: tuple = (150, 150)  # 缩略图大小
    grid_columns: int = 5               # 网格列数
    grid_rows: int = 2                  # 网格行数

@dataclass
class SearchConfig:
    """搜索配置"""
    default_limit: int = 10             # 默认返回结果数
    output_fields: list = None          # 输出字段

    def __post_init__(self):
        if self.output_fields is None:
            self.output_fields = ["filepath"]

class Config:
    """主配置类"""
    def __init__(self):
        self.clip = CLIPConfig()
        self.milvus = MilvusConfig()
        self.image = ImageConfig()
        self.search = SearchConfig()

# 全局配置实例
config = Config()
```

---

### 配置项详解

#### CLIP 配置

```python
# 修改 CLIP 模型
config.clip.model_name = "ViT-L/14"  # 使用更大的模型
config.clip.feature_dimension = 768  # 对应的维度

# 可选模型:
# - ViT-B/32: 512 维 (默认, 速度快)
# - ViT-B/16: 512 维 (更准确)
# - ViT-L/14: 768 维 (最准确, 但慢)
# - RN50: 1024 维 (ResNet 骨干)
```

#### Milvus 配置

```python
# 集合名称
config.milvus.collection_name = "my_images"

# 索引类型选择
config.milvus.index_type = "HNSW"  # 推荐
# 其他选项: "IVF_FLAT", "IVF_SQ8", "IVF_PQ"

# 相似度度量
config.milvus.metric_type = "COSINE"  # 余弦相似度
# 其他选项: "L2" (欧氏距离), "IP" (内积)

# HNSW 参数调优
config.milvus.index_params = {
    "M": 16,               # 增大 M: 精度 ↑, 内存 ↑
    "efConstruction": 128  # 增大 ef: 精度 ↑, 索引时间 ↑
}
```

#### 图像配置

```python
# 图像目录
config.image.image_directory = "/path/to/images"

# 支持的图像格式
config.image.image_extensions = (
    "*.JPEG", "*.jpg", "*.JPG",
    "*.png", "*.PNG",
    "*.bmp", "*.BMP"
)

# 可视化参数
config.image.thumbnail_size = (200, 200)  # 缩略图大小
config.image.grid_columns = 5             # 每行显示 5 张
config.image.grid_rows = 2                # 显示 2 行
```

---

# 第四部分：核心模块详解

## 4.1 CLIP 编码器模块

### 模块概述

```python
# clip_encoder.py

class CLIPEncoder:
    """CLIP 特征编码器

    职责:
      1. 加载 CLIP 模型
      2. 编码图像为向量
      3. 编码文本为向量
      4. 批量处理
    """
```

---

### 初始化与模型加载

```python
def __init__(self, model_name: str = None):
    """初始化 CLIP 编码器

    Args:
        model_name: CLIP 模型名称
    """
    self.model_name = model_name or config.clip.model_name
    self.model = None
    self.preprocess = None

    # 自动选择设备
    self.device = "cuda" if torch.cuda.is_available() else "cpu"

    # 加载模型
    self._load_model()

def _load_model(self) -> None:
    """加载 CLIP 模型"""
    try:
        logging.info(f"正在加载 CLIP 模型: {self.model_name}")

        # 加载模型和预处理函数
        self.model, self.preprocess = clip.load(
            self.model_name,
            device=self.device
        )

        # 设置为评估模式 (关闭 Dropout 等)
        self.model.eval()

        logging.info(f"CLIP 模型加载成功，使用设备: {self.device}")

    except Exception as e:
        logging.error(f"CLIP 模型加载失败: {e}")
        raise
```

**关键点**:
- `clip.load()`: 自动下载模型权重到 `~/.cache/clip/`
- `.eval()`: 必须调用，确保推理模式
- GPU 自动检测: 优先使用 CUDA

---

### 图像编码

```python
def encode_image(self, image_path: str) -> List[float]:
    """编码单张图像

    Args:
        image_path: 图像文件路径

    Returns:
        归一化的图像特征向量列表 (512,)
    """
    try:
        # 1. 加载图像
        image = Image.open(image_path).convert('RGB')

        # 2. 预处理 (Resize, Normalize)
        image_tensor = self.preprocess(image).unsqueeze(0).to(self.device)
        # shape: (1, 3, 224, 224)

        # 3. 提取特征
        with torch.no_grad():  # 禁用梯度计算
            image_features = self.model.encode_image(image_tensor)
            # shape: (1, 512)

            # 4. L2 归一化 (关键!)
            image_features = image_features / image_features.norm(
                dim=-1, keepdim=True
            )

        # 5. 转换为 Python 列表
        return image_features.squeeze().cpu().tolist()

    except FileNotFoundError:
        logging.error(f"图像文件不存在: {image_path}")
        raise
    except Exception as e:
        logging.error(f"图像编码失败 {image_path}: {e}")
        raise
```

**流程详解**:
```
原始图像 (任意尺寸)
    ↓ Image.open()
PIL Image (RGB)
    ↓ preprocess()
Tensor (3, 224, 224)
    ↓ encode_image()
特征向量 (512,)
    ↓ L2 归一化
归一化向量 (512,)
```

---

### 批量图像编码

```python
def encode_images_batch(self,
                       image_paths: List[str],
                       batch_size: int = 32) -> List[List[float]]:
    """批量编码图像

    Args:
        image_paths: 图像文件路径列表
        batch_size: 批处理大小

    Returns:
        图像特征向量列表
    """
    features = []
    total_images = len(image_paths)

    # 分批处理
    for i in range(0, total_images, batch_size):
        batch_paths = image_paths[i:i + batch_size]
        batch_images = []

        # 预处理批次图像
        for path in batch_paths:
            try:
                image = Image.open(path).convert('RGB')
                image_tensor = self.preprocess(image)
                batch_images.append(image_tensor)
            except Exception as e:
                logging.warning(f"跳过无效图像 {path}: {e}")
                continue

        if not batch_images:
            continue

        # 批量编码
        try:
            # 堆叠为批次
            batch_tensor = torch.stack(batch_images).to(self.device)
            # shape: (batch_size, 3, 224, 224)

            with torch.no_grad():
                batch_features = self.model.encode_image(batch_tensor)
                # shape: (batch_size, 512)

                # 归一化
                batch_features = batch_features / batch_features.norm(
                    dim=-1, keepdim=True
                )

            features.extend(batch_features.cpu().tolist())

            logging.info(
                f"已处理 {min(i + batch_size, total_images)}/{total_images} 张图像"
            )

        except Exception as e:
            logging.error(f"批量编码失败: {e}")
            continue

    return features
```

**性能优化**:
- GPU 批处理: 10-20 倍加速
- 错误处理: 跳过无效图像，继续处理
- 进度日志: 实时反馈

---

### 文本编码

```python
def encode_text(self,
               text: Union[str, List[str]]) -> Union[List[float], List[List[float]]]:
    """编码文本

    Args:
        text: 单个文本字符串或文本列表

    Returns:
        归一化的文本特征向量或向量列表
    """
    try:
        # 处理单个文本
        if isinstance(text, str):
            # Tokenize 文本
            text_tokens = clip.tokenize([text]).to(self.device)
            # shape: (1, 77)  # CLIP 最大 token 长度 77

            with torch.no_grad():
                text_features = self.model.encode_text(text_tokens)
                # shape: (1, 512)

                text_features = text_features / text_features.norm(
                    dim=-1, keepdim=True
                )

            return text_features.squeeze().cpu().tolist()

        # 处理文本列表
        else:
            text_tokens = clip.tokenize(text).to(self.device)
            # shape: (N, 77)

            with torch.no_grad():
                text_features = self.model.encode_text(text_tokens)
                # shape: (N, 512)

                text_features = text_features / text_features.norm(
                    dim=-1, keepdim=True
                )

            return text_features.cpu().tolist()

    except Exception as e:
        logging.error(f"文本编码失败: {e}")
        raise
```

**文本处理流程**:
```
原始文本: "a photo of a cat"
    ↓ clip.tokenize()
Token IDs: [49406, 320, 1125, 539, 320, 2368, 49407, 0, 0, ...]
    ↓ encode_text()
文本特征: [0.12, -0.34, 0.56, ...]  (512 维)
```

---

## 4.2 Milvus 数据库管理模块

### 模块概述

```python
# milvus_manager.py

class MilvusManager:
    """Milvus 向量数据库管理器

    职责:
      1. 连接 Milvus 服务
      2. 创建和管理集合
      3. 创建向量索引
      4. 插入向量数据
      5. 向量相似度搜索
      6. 查询和统计
    """
```

---

### 连接 Milvus

```python
def __init__(self, uri: str = None):
    """初始化 Milvus 管理器

    Args:
        uri: Milvus 服务器 URI
            - None: 使用 Milvus Lite (本地文件)
            - "http://localhost:19530": Standalone 模式
            - "http://ip:port": 远程服务器
    """
    self.uri = uri
    self.client = None
    self.collection_name = config.milvus.collection_name
    self._connect()

def _connect(self) -> None:
    """连接到 Milvus 服务器"""
    try:
        if self.uri:
            self.client = MilvusClient(uri=self.uri)
            logging.info(f"已连接到 Milvus 服务器: {self.uri}")
        else:
            # Lite 模式: 数据存储在 ./milvus_lite.db
            self.client = MilvusClient()
            logging.info("已连接到 Milvus Lite 本地模式")
    except Exception as e:
        logging.error(f"Milvus 连接失败: {e}")
        raise
```

---

### 创建集合

```python
def create_collection(self,
                     collection_name: str = None,
                     dimension: int = None,
                     drop_existing: bool = True) -> bool:
    """创建向量集合

    Args:
        collection_name: 集合名称
        dimension: 向量维度
        drop_existing: 是否删除已存在的集合

    Returns:
        创建是否成功
    """
    collection_name = collection_name or self.collection_name
    dimension = dimension or config.clip.feature_dimension

    try:
        # 检查集合是否存在
        if self.client.has_collection(collection_name):
            if drop_existing:
                logging.info(f"删除已存在的集合: {collection_name}")
                self.client.drop_collection(collection_name)
            else:
                logging.info(f"集合已存在: {collection_name}")
                return True

        # 创建集合
        self.client.create_collection(
            collection_name=collection_name,
            dimension=dimension,
            auto_id=True,              # 自动生成 ID
            enable_dynamic_field=True  # 支持动态字段
        )

        logging.info(f"成功创建集合: {collection_name}, 维度: {dimension}")
        return True

    except Exception as e:
        logging.error(f"创建集合失败: {e}")
        return False
```

**集合 Schema**:
```python
# 自动生成的 Schema
{
    "fields": [
        {
            "name": "id",
            "type": "INT64",
            "is_primary": True,
            "auto_id": True
        },
        {
            "name": "vector",
            "type": "FLOAT_VECTOR",
            "dim": 512
        },
        {
            "name": "filepath",  # 动态字段
            "type": "VARCHAR"
        }
    ]
}
```

---

### 创建索引

```python
def create_index(self,
                collection_name: str = None,
                field_name: str = None) -> bool:
    """创建向量索引

    Args:
        collection_name: 集合名称
        field_name: 字段名称

    Returns:
        索引创建是否成功
    """
    collection_name = collection_name or self.collection_name
    field_name = field_name or "vector"

    try:
        # 检查索引是否已存在
        existing_indexes = self.client.list_indexes(
            collection_name=collection_name
        )
        if field_name in existing_indexes:
            logging.info(f"索引已存在，字段: {field_name}")
            return True

        # 准备索引参数
        index_params = self.client.prepare_index_params()

        # 添加向量字段的索引
        index_params.add_index(
            field_name=field_name,
            index_type=config.milvus.index_type,      # "HNSW"
            metric_type=config.milvus.metric_type,    # "COSINE"
            params=config.milvus.index_params         # {"M": 8, ...}
        )

        # 创建索引
        self.client.create_index(
            collection_name=collection_name,
            index_params=index_params
        )

        logging.info(f"成功创建索引，字段: {field_name}")
        return True

    except Exception as e:
        logging.error(f"创建索引失败: {e}")
        return False
```

**索引参数说明**:
```python
index_params = {
    "M": 8,                # HNSW 每层最大边数
                           # 增大: 精度 ↑, 内存 ↑, 速度 ↓

    "efConstruction": 64   # HNSW 构建时搜索深度
                           # 增大: 精度 ↑, 索引时间 ↓
}
```

---

### 插入数据

```python
def insert_data(self,
               data: List[Dict[str, Any]],
               collection_name: str = None) -> Optional[Dict[str, Any]]:
    """插入向量数据

    Args:
        data: 要插入的数据列表
            [
                {
                    "vector": [0.1, 0.2, ...],  # 512 维向量
                    "filepath": "/path/to/image.jpg"
                },
                ...
            ]
        collection_name: 集合名称

    Returns:
        插入结果信息
    """
    collection_name = collection_name or self.collection_name

    try:
        result = self.client.insert(
            collection_name=collection_name,
            data=data
        )

        insert_count = result.get('insert_count', 0)
        logging.info(f"成功插入 {insert_count} 条数据")
        return result

    except Exception as e:
        logging.error(f"数据插入失败: {e}")
        return None
```

---

### 向量搜索

```python
def search(self,
          query_vectors: List[List[float]],
          collection_name: str = None,
          limit: int = None,
          output_fields: List[str] = None,
          search_params: Dict[str, Any] = None) -> Optional[List[List[Dict]]]:
    """向量相似性搜索

    Args:
        query_vectors: 查询向量列表 [[v1], [v2], ...]
        collection_name: 集合名称
        limit: 返回结果数量限制
        output_fields: 需要返回的字段列表
        search_params: 搜索参数

    Returns:
        搜索结果列表
        [
            [  # 第一个查询的结果
                {
                    "id": 123,
                    "distance": 0.95,  # 相似度
                    "entity": {
                        "filepath": "/path/to/image.jpg"
                    }
                },
                ...
            ]
        ]
    """
    collection_name = collection_name or self.collection_name
    limit = limit or config.search.default_limit
    output_fields = output_fields or config.search.output_fields

    if search_params is None:
        search_params = {"metric_type": config.milvus.metric_type}

    try:
        results = self.client.search(
            collection_name=collection_name,
            data=query_vectors,
            limit=limit,
            output_fields=output_fields,
            search_params=search_params
        )

        logging.info(f"搜索完成，返回 {len(results)} 组结果")
        return results

    except Exception as e:
        logging.error(f"向量搜索失败: {e}")
        return None
```

**搜索参数调优**:
```python
search_params = {
    "metric_type": "COSINE",  # 相似度度量
    "params": {
        "ef": 64              # HNSW 搜索深度
                              # 增大: 召回 ↑, 速度 ↓
    }
}
```

---

### 批量检查图像是否存在

```python
def batch_check_images_exist(self,
                            filepaths: List[str],
                            collection_name: str = None) -> Dict[str, bool]:
    """批量检查图片是否已存在于数据库中

    Args:
        filepaths: 图片文件路径列表
        collection_name: 集合名称

    Returns:
        文件路径到存在状态的映射字典
        {
            "/path/to/img1.jpg": True,
            "/path/to/img2.jpg": False,
            ...
        }
    """
    collection_name = collection_name or self.collection_name
    result = {}

    try:
        # 检查集合是否存在
        if not self.client.has_collection(collection_name):
            return {path: False for path in filepaths}

        # 批量查询所有已存在的文件路径
        if filepaths:
            # 构建查询条件 (OR 连接)
            filepath_conditions = [
                f'filepath == "{path}"' for path in filepaths
            ]
            filter_expr = " or ".join(filepath_conditions)

            # 执行查询
            existing_results = self.client.query(
                collection_name=collection_name,
                filter=filter_expr,
                output_fields=["filepath"],
                limit=len(filepaths)
            )

            # 提取已存在的文件路径
            existing_paths = {
                result["filepath"] for result in existing_results
            }

            # 构建结果字典
            for path in filepaths:
                result[path] = path in existing_paths

        return result

    except Exception as e:
        logging.error(f"批量检查图片失败: {e}")
        return {path: False for path in filepaths}
```

**用途**: 增量索引时跳过已存在的图像

---

## 4.3 图像处理模块

### 模块概述

```python
# image_processor.py

class ImageProcessor:
    """图像处理器

    职责:
      1. 扫描图像目录
      2. 验证图像有效性
      3. 准备数据格式
      4. 显示搜索结果
    """
```

---

### 获取图像路径

```python
def get_image_paths(self, directory: str = None) -> List[str]:
    """获取目录下所有图像路径

    Args:
        directory: 图像目录

    Returns:
        图像文件路径列表
    """
    directory = directory or self.image_directory
    image_paths = []

    # 遍历所有支持的扩展名
    for extension in self.image_extensions:
        paths = glob.glob(
            os.path.join(directory, "**", extension),
            recursive=True
        )
        image_paths.extend(paths)

    logging.info(f"找到 {len(image_paths)} 张图像")
    return image_paths
```

---

### 验证图像有效性

```python
def filter_valid_images(self, image_paths: List[str]) -> List[str]:
    """过滤有效的图像文件

    Args:
        image_paths: 图像路径列表

    Returns:
        有效图像路径列表
    """
    valid_paths = []

    for path in image_paths:
        try:
            # 尝试打开图像
            with Image.open(path) as img:
                img.verify()  # 验证图像完整性
            valid_paths.append(path)
        except Exception as e:
            logging.warning(f"跳过无效图像 {path}: {e}")

    logging.info(f"有效图像: {len(valid_paths)}/{len(image_paths)}")
    return valid_paths
```

---

### 准备数据格式

```python
def prepare_image_data(self,
                      image_paths: List[str],
                      features: List[List[float]]) -> List[Dict[str, Any]]:
    """准备插入 Milvus 的数据格式

    Args:
        image_paths: 图像路径列表
        features: 特征向量列表

    Returns:
        格式化的数据列表
        [
            {
                "vector": [0.1, 0.2, ...],
                "filepath": "/path/to/image.jpg"
            },
            ...
        ]
    """
    data = []
    for path, feature in zip(image_paths, features):
        data.append({
            "vector": feature,
            "filepath": path
        })

    return data
```

---

### 显示搜索结果

```python
def display_results(self,
                   search_results: List[List[Dict]],
                   query_text: str = "",
                   save_path: str = None) -> None:
    """可视化搜索结果

    Args:
        search_results: Milvus 搜索结果
        query_text: 查询文本 (用于标题)
        save_path: 保存路径 (可选)
    """
    import matplotlib.pyplot as plt

    # 提取第一组结果
    results = search_results[0]

    # 计算网格布局
    cols = min(config.image.grid_columns, len(results))
    rows = (len(results) + cols - 1) // cols

    # 创建图形
    fig, axes = plt.subplots(rows, cols, figsize=(15, rows * 3))
    fig.suptitle(f'搜索结果: "{query_text}"', fontsize=16)

    # 展平 axes 数组
    if rows == 1:
        axes = [axes] if cols == 1 else axes
    else:
        axes = axes.flatten()

    # 显示每张图像
    for idx, result in enumerate(results):
        filepath = result['entity']['filepath']
        distance = result['distance']

        # 加载图像
        img = Image.open(filepath)

        # 显示
        axes[idx].imshow(img)
        axes[idx].set_title(
            f"相似度: {distance:.3f}\n{os.path.basename(filepath)}",
            fontsize=10
        )
        axes[idx].axis('off')

    # 隐藏多余的子图
    for idx in range(len(results), len(axes)):
        axes[idx].axis('off')

    plt.tight_layout()

    # 保存或显示
    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=150)
        logging.info(f"结果已保存到: {save_path}")
    else:
        plt.show()
```

---

## 4.4 搜索系统主模块

### 系统初始化

```python
# clip_image_search.py

class CLIPImageSearchSystem:
    """CLIP 图像搜索系统主类"""

    def __init__(self, log_level: str = "INFO"):
        """初始化搜索系统"""
        # 设置日志
        self.logger = get_logger("CLIPImageSearchSystem", log_level)
        self.logger.info("初始化 CLIP 图像搜索系统")

        # 初始化组件
        self.encoder = None
        self.db_manager = None
        self.image_processor = None

        self._initialize_components()

    def _initialize_components(self) -> None:
        """初始化系统组件"""
        try:
            # 验证配置
            config.validate()

            # 初始化 CLIP 编码器
            self.encoder = CLIPEncoder()

            # 初始化 Milvus 管理器
            self.db_manager = MilvusManager()

            # 初始化图像处理器
            self.image_processor = ImageProcessor()

            self.logger.info("所有组件初始化完成")

        except Exception as e:
            self.logger.error(f"组件初始化失败: {e}")
            raise
```

---

### 设置数据库

```python
def setup_database(self, drop_existing: bool = True) -> bool:
    """设置数据库集合和索引

    Args:
        drop_existing: 是否删除已存在的集合

    Returns:
        设置是否成功
    """
    try:
        self.logger.info("开始设置数据库...")

        # 创建集合
        success = self.db_manager.create_collection(
            drop_existing=drop_existing
        )
        if not success:
            return False

        # 创建索引
        success = self.db_manager.create_index()
        if not success:
            return False

        self.logger.info("数据库设置完成")
        return True

    except Exception as e:
        self.logger.error(f"数据库设置失败: {e}")
        return False
```

---

### 索引图像

```python
def index_images(self,
                batch_size: int = 32,
                validate_images: bool = True,
                skip_existing: bool = True) -> bool:
    """索引图像到数据库

    Args:
        batch_size: 批处理大小
        validate_images: 是否验证图像有效性
        skip_existing: 是否跳过已存在的图像

    Returns:
        索引是否成功
    """
    try:
        self.logger.info("开始索引图像...")

        # 1. 获取图像路径
        image_paths = self.image_processor.get_image_paths()
        if not image_paths:
            self.logger.warning("未找到图像文件")
            return False

        # 2. 验证图像 (可选)
        if validate_images:
            image_paths = self.image_processor.filter_valid_images(
                image_paths
            )

        # 3. 跳过已存在的图像 (可选)
        if skip_existing:
            existing_status = self.db_manager.batch_check_images_exist(
                image_paths
            )
            new_image_paths = [
                path for path, exists in existing_status.items()
                if not exists
            ]

            existing_count = len(image_paths) - len(new_image_paths)
            if existing_count > 0:
                self.logger.info(f"跳过 {existing_count} 张已存在的图像")

            if not new_image_paths:
                self.logger.info("所有图像都已存在")
                return True

            image_paths = new_image_paths

        # 4. 批量编码图像
        self.logger.info(f"开始编码 {len(image_paths)} 张图像...")
        features = self.encoder.encode_images_batch(
            image_paths, batch_size
        )

        # 5. 准备数据
        data = self.image_processor.prepare_image_data(
            image_paths, features
        )

        # 6. 插入数据库
        self.logger.info("插入数据到 Milvus...")
        result = self.db_manager.insert_data(data)

        if result:
            self.logger.info(f"成功索引 {result['insert_count']} 张图像")
            return True
        else:
            return False

    except Exception as e:
        self.logger.error(f"图像索引失败: {e}")
        return False
```

---

### 文本搜索图像

```python
def search_by_text(self,
                  query_text: str,
                  limit: int = None,
                  display_results: bool = True,
                  save_results: str = None) -> Optional[List[List[Dict]]]:
    """根据文本搜索相似图像

    Args:
        query_text: 查询文本
        limit: 返回结果数量
        display_results: 是否显示结果
        save_results: 结果保存路径

    Returns:
        搜索结果列表
    """
    try:
        self.logger.info(f"文本搜索: '{query_text}'")

        # 1. 编码查询文本
        query_embedding = self.encoder.encode_text(query_text)

        # 2. 执行搜索
        search_results = self.db_manager.search(
            query_vectors=[query_embedding],
            limit=limit
        )

        if not search_results:
            self.logger.warning("搜索未返回结果")
            return None

        # 3. 显示结果 (可选)
        if display_results:
            self.image_processor.display_results(
                search_results,
                query_text,
                save_results
            )

        self.logger.info(f"找到 {len(search_results[0])} 个结果")
        return search_results

    except Exception as e:
        self.logger.error(f"文本搜索失败: {e}")
        return None
```

---

### 以图搜图

```python
def search_by_image(self,
                   image_path: str,
                   limit: int = None,
                   display_results: bool = True,
                   save_results: str = None) -> Optional[List[List[Dict]]]:
    """根据图像搜索相似图像

    Args:
        image_path: 查询图像路径
        limit: 返回结果数量
        display_results: 是否显示结果
        save_results: 结果保存路径

    Returns:
        搜索结果列表
    """
    try:
        self.logger.info(f"图像搜索: {image_path}")

        # 1. 编码查询图像
        query_embedding = self.encoder.encode_image(image_path)

        # 2. 执行搜索
        search_results = self.db_manager.search(
            query_vectors=[query_embedding],
            limit=limit
        )

        if not search_results:
            self.logger.warning("搜索未返回结果")
            return None

        # 3. 显示结果 (可选)
        if display_results:
            query_text = f"相似图像搜索: {image_path}"
            self.image_processor.display_results(
                search_results,
                query_text,
                save_results
            )

        self.logger.info(f"找到 {len(search_results[0])} 个结果")
        return search_results

    except Exception as e:
        self.logger.error(f"图像搜索失败: {e}")
        return None
```

---

# 第五部分：快速开始

## 5.1 基础使用流程

### 完整示例

```python
# main.py

from clip_image_search import CLIPImageSearchSystem

# 创建搜索系统 (使用上下文管理器)
with CLIPImageSearchSystem(log_level="INFO") as search_system:

    # 步骤 1: 设置数据库
    print("步骤 1: 设置数据库...")
    if not search_system.setup_database():
        print("数据库设置失败")
        exit(1)

    # 步骤 2: 索引图像
    print("\n步骤 2: 索引图像...")
    if not search_system.index_images(batch_size=16, skip_existing=True):
        print("图像索引失败")
        exit(1)

    # 步骤 3: 文本搜索
    print("\n步骤 3: 文本搜索...")
    results = search_system.search_by_text("red goldfish", limit=10)

    if results:
        print(f"找到 {len(results[0])} 个相似图像")

    # 步骤 4: 查看系统信息
    print("\n步骤 4: 系统信息")
    info = search_system.get_system_info()
    print(f"集合数量: {len(info['database_collections'])}")
    print(f"CLIP 模型: {info['config']['clip_model']}")
```

---

### 运行示例

```bash
cd week07/standalone_projects/p25-CLIP

# 首次运行: 完整流程
python main.py

# 输出:
# 步骤 1: 设置数据库...
# [INFO] 正在加载 CLIP 模型: ViT-B/32
# [INFO] CLIP 模型加载成功，使用设备: cuda
# [INFO] 已连接到 Milvus Lite 本地模式
# [INFO] 成功创建集合: image_collection, 维度: 512
# [INFO] 成功创建索引，字段: vector
#
# 步骤 2: 索引图像...
# [INFO] 找到 1000 张图像
# [INFO] 有效图像: 1000/1000
# [INFO] 已处理 16/1000 张图像
# [INFO] 已处理 32/1000 张图像
# ...
# [INFO] 成功插入 1000 条数据
#
# 步骤 3: 文本搜索...
# [INFO] 文本搜索: 'red goldfish'
# [INFO] 搜索完成，返回 10 组结果
# 找到 10 个相似图像
#
# 步骤 4: 系统信息
# 集合数量: 1
# CLIP 模型: ViT-B/32
```

---

## 5.2 文本搜索图像

### 基础用法

```python
# 搜索猫的图片
results = search_system.search_by_text("a photo of a cat")

# 搜索日落场景
results = search_system.search_by_text("sunset over the ocean")

# 搜索特定风格
results = search_system.search_by_text("minimalist design logo")
```

---

### 高级查询技巧

```python
# 1. 组合多个属性
search_system.search_by_text("red sports car on highway")

# 2. 指定艺术风格
search_system.search_by_text("impressionist painting of flowers")

# 3. 描述场景
search_system.search_by_text(
    "people walking in a park on a sunny day"
)

# 4. 指定视角
search_system.search_by_text("bird's eye view of city")

# 5. 颜色 + 对象
search_system.search_by_text("blue dress with floral pattern")
```

---

### 调整返回数量

```python
# 返回 Top-5 结果
results = search_system.search_by_text("cat", limit=5)

# 返回 Top-20 结果
results = search_system.search_by_text("cat", limit=20)

# 不显示可视化结果
results = search_system.search_by_text(
    "cat",
    display_results=False
)

# 保存结果到文件
results = search_system.search_by_text(
    "cat",
    save_results="output/search_results.png"
)
```

---

### 解析搜索结果

```python
results = search_system.search_by_text("red car", limit=5)

# 结果结构
for idx, result in enumerate(results[0]):
    print(f"结果 {idx + 1}:")
    print(f"  相似度: {result['distance']}")
    print(f"  图像路径: {result['entity']['filepath']}")
    print(f"  数据库 ID: {result['id']}")
    print()

# 输出:
# 结果 1:
#   相似度: 0.923
#   图像路径: /path/to/red_car_001.jpg
#   数据库 ID: 12345
#
# 结果 2:
#   相似度: 0.891
#   图像路径: /path/to/red_sports_car.jpg
#   数据库 ID: 12346
```

---

## 5.3 以图搜图

### 基础用法

```python
# 上传参考图片,查找相似图片
results = search_system.search_by_image(
    "reference_images/sample.jpg",
    limit=10
)
```

---

### 应用场景

```python
# 场景 1: 找相似产品
search_system.search_by_image(
    "user_upload/product_photo.jpg",
    limit=20
)

# 场景 2: 版权检测
search_system.search_by_image(
    "suspected_duplicate.jpg",
    limit=100  # 大量结果,找出所有相似图
)

# 场景 3: 图像去重
all_images = image_processor.get_image_paths()

for img_path in all_images:
    results = search_system.search_by_image(
        img_path,
        limit=2  # 返回自身 + 最相似的图
    )

    # 如果有高度相似的图 (非自身)
    if len(results[0]) > 1 and results[0][1]['distance'] > 0.99:
        print(f"发现重复图像: {img_path}")
        print(f"  相似图: {results[0][1]['entity']['filepath']}")
```

---

# 第六部分:高级功能

## 6.1 批量图像索引

### 大规模数据集处理

```python
# 索引 10 万张图像
search_system.index_images(
    batch_size=64,          # 增大批次提升速度
    validate_images=False,  # 跳过验证节省时间
    skip_existing=True      # 增量索引
)

# 性能估算:
# - GPU (RTX 3090): ~500 张/秒
# - CPU (16 核): ~50 张/秒
#
# 10 万张图像:
#   GPU: ~3 分钟
#   CPU: ~33 分钟
```

---

### 多目录索引

```python
# 索引多个目录
directories = [
    "/data/images/2024-01",
    "/data/images/2024-02",
    "/data/images/2024-03"
]

for directory in directories:
    # 临时修改配置
    config.image.image_directory = directory

    # 索引当前目录
    search_system.index_images(skip_existing=True)

    print(f"完成目录: {directory}")
```

---

## 6.2 增量索引更新

### 定时增量更新

```python
import schedule
import time

def incremental_index():
    """增量索引任务"""
    print(f"[{datetime.now()}] 开始增量索引...")

    # 只索引新增图像
    search_system.index_images(skip_existing=True)

    print(f"[{datetime.now()}] 增量索引完成")

# 每小时执行一次
schedule.every(1).hours.do(incremental_index)

# 运行调度器
while True:
    schedule.run_pending()
    time.sleep(60)
```

---

### 监听目录变化

```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

class ImageIndexHandler(FileSystemEventHandler):
    """监听新图像并自动索引"""

    def __init__(self, search_system):
        self.search_system = search_system

    def on_created(self, event):
        """文件创建事件"""
        if event.is_directory:
            return

        # 检查是否为图像文件
        if event.src_path.lower().endswith(('.jpg', '.jpeg', '.png')):
            print(f"检测到新图像: {event.src_path}")

            # 索引单张图像
            try:
                # 编码图像
                feature = self.search_system.encoder.encode_image(
                    event.src_path
                )

                # 插入���据库
                data = [{
                    "vector": feature,
                    "filepath": event.src_path
                }]
                self.search_system.db_manager.insert_data(data)

                print(f"✓ 索引成功: {event.src_path}")

            except Exception as e:
                print(f"✗ 索引失败: {e}")

# 使用示例
handler = ImageIndexHandler(search_system)
observer = Observer()
observer.schedule(
    handler,
    path=config.image.image_directory,
    recursive=True
)
observer.start()

print(f"监听目录: {config.image.image_directory}")
print("按 Ctrl+C 停止...")

try:
    while True:
        time.sleep(1)
except KeyboardInterrupt:
    observer.stop()
observer.join()
```

---

## 6.3 搜索结果可视化

### 自定义可视化样式

```python
import matplotlib.pyplot as plt
from PIL import Image

def custom_display(search_results, query_text, save_path=None):
    """自定义可视化函数"""
    results = search_results[0]

    # 创建大图
    fig = plt.figure(figsize=(20, 10))
    fig.suptitle(
        f'搜索: "{query_text}"',
        fontsize=20,
        fontweight='bold'
    )

    for idx, result in enumerate(results):
        filepath = result['entity']['filepath']
        distance = result['distance']

        # 加载图像
        img = Image.open(filepath)

        # 创建子图
        ax = fig.add_subplot(2, 5, idx + 1)
        ax.imshow(img)

        # 设置标题 (带颜色编码)
        color = 'green' if distance > 0.9 else 'orange' if distance > 0.7 else 'red'
        ax.set_title(
            f"#{idx+1} | 相似度: {distance:.3f}",
            fontsize=12,
            color=color,
            fontweight='bold'
        )
        ax.axis('off')

    plt.tight_layout()

    if save_path:
        plt.savefig(save_path, bbox_inches='tight', dpi=200)
    else:
        plt.show()

# 使用自定义可视化
results = search_system.search_by_text(
    "red car",
    display_results=False
)
custom_display(results, "red car", "output/custom_results.png")
```

---

### 生成 HTML 报告

```python
def generate_html_report(search_results, query_text, output_file="report.html"):
    """生成 HTML 搜索报告"""
    results = search_results[0]

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>��索结果: {query_text}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 20px; }}
            h1 {{ color: #333; }}
            .result {{
                display: inline-block;
                margin: 10px;
                text-align: center;
                width: 200px;
            }}
            .result img {{
                width: 200px;
                height: 200px;
                object-fit: cover;
                border: 2px solid #ddd;
            }}
            .score {{
                font-weight: bold;
                color: #0066cc;
            }}
        </style>
    </head>
    <body>
        <h1>搜索: "{query_text}"</h1>
        <p>找到 {len(results)} 个结果</p>
    """

    for idx, result in enumerate(results):
        filepath = result['entity']['filepath']
        distance = result['distance']

        html += f"""
        <div class="result">
            <img src="file://{filepath}" alt="Result {idx+1}">
            <p>#{idx+1}</p>
            <p class="score">相似度: {distance:.3f}</p>
            <p><small>{os.path.basename(filepath)}</small></p>
        </div>
        """

    html += """
    </body>
    </html>
    """

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(html)

    print(f"报告已生成: {output_file}")

# 使用示例
results = search_system.search_by_text("cat", display_results=False)
generate_html_report(results, "cat", "output/search_report.html")
```

---

# 第七部分：实战案例

## 7.1 电商图片搜索

### 场景描述

用户上传喜欢的商品图片,系统推荐相似商品

---

### 实现代码

```python
class EcommerceImageSearch:
    """电商图片搜索系统"""

    def __init__(self, search_system):
        self.search_system = search_system

    def recommend_products(self, uploaded_image_path, top_k=10):
        """根据上传图片推荐商品

        Args:
            uploaded_image_path: 用户上传的图片路径
            top_k: 推荐商品数量

        Returns:
            推荐商品列表
        """
        # 1. 以图搜图
        results = self.search_system.search_by_image(
            uploaded_image_path,
            limit=top_k,
            display_results=False
        )

        if not results:
            return []

        # 2. 提取商品信息
        recommendations = []
        for result in results[0]:
            filepath = result['entity']['filepath']
            similarity = result['distance']

            # 从文件路径提取商品 ID (假设路径格式: /products/category/product_id.jpg)
            product_id = os.path.splitext(os.path.basename(filepath))[0]

            # 查询商品详情 (伪代码)
            product_info = {
                "product_id": product_id,
                "image_path": filepath,
                "similarity": similarity,
                # 从数据库查询其他信息
                # "name": db.query(product_id).name,
                # "price": db.query(product_id).price,
                # ...
            }

            recommendations.append(product_info)

        return recommendations

    def search_by_description(self, description, top_k=10):
        """根据描述搜索商品

        Args:
            description: 用户描述 (如: "红色连衣裙")
            top_k: 返回商品数量

        Returns:
            商品列表
        """
        results = self.search_system.search_by_text(
            description,
            limit=top_k,
            display_results=False
        )

        # 提取商品信息 (同上)
        return self._extract_products(results)

# 使用示例
ecommerce_search = EcommerceImageSearch(search_system)

# 场景 1: 以图搜图
user_upload = "uploads/user_photo_123.jpg"
recommendations = ecommerce_search.recommend_products(
    user_upload,
    top_k=20
)

print(f"为您推荐 {len(recommendations)} 件商品:")
for idx, product in enumerate(recommendations):
    print(f"{idx+1}. 商品ID: {product['product_id']}, "
          f"相似度: {product['similarity']:.3f}")

# 场景 2: 文本搜索
results = ecommerce_search.search_by_description(
    "蓝色牛仔裤",
    top_k=15
)
```

---

## 7.2 素材库管理

### 场景描述

设计师快速找到所需风格的设计素材

---

### 实现代码

```python
class DesignAssetLibrary:
    """设计素材库管理系统"""

    def __init__(self, search_system):
        self.search_system = search_system

        # 预定义的风格标签
        self.style_tags = {
            "极简": "minimalist design",
            "复古": "vintage retro style",
            "现代": "modern contemporary",
            "日系": "japanese aesthetic",
            "赛博朋克": "cyberpunk neon",
            "扁平化": "flat design",
            "立体": "3D isometric",
        }

    def search_by_style(self, style, asset_type="", top_k=20):
        """根据风格搜索素材

        Args:
            style: 风格名称 (如: "极简")
            asset_type: 素材类型 (如: "logo", "poster", "icon")
            top_k: 返回数量

        Returns:
            素材列表
        """
        # 构建查询
        style_query = self.style_tags.get(style, style)

        if asset_type:
            query = f"{style_query} {asset_type}"
        else:
            query = style_query

        print(f"搜索查询: {query}")

        # 执行搜索
        results = self.search_system.search_by_text(
            query,
            limit=top_k,
            save_results=f"output/{style}_{asset_type}_results.png"
        )

        return results

    def find_similar_design(self, reference_path, exclude_self=True):
        """找到相似设计 (用于灵感参考)

        Args:
            reference_path: 参考设计路径
            exclude_self: 是否排除自身

        Returns:
            相似设计列表
        """
        results = self.search_system.search_by_image(
            reference_path,
            limit=11 if exclude_self else 10,
            display_results=False
        )

        # 排除第一个结果 (自身)
        if exclude_self and results:
            results[0] = results[0][1:]

        return results

# 使用示例
asset_library = DesignAssetLibrary(search_system)

# 场景 1: 找极简风格的 Logo
asset_library.search_by_style("极简", "logo", top_k=20)

# 场景 2: 找日系风格的海报
asset_library.search_by_style("日系", "poster", top_k=15)

# 场景 3: 找相似设计
similar = asset_library.find_similar_design(
    "my_design/draft_v1.png",
    exclude_self=True
)
```

---

## 7.3 图像去重

### 场景描述

检测并清理图片库中的重复图像

---

### 实现代码

```python
class ImageDuplicateDetector:
    """图像去重检测器"""

    def __init__(self, search_system):
        self.search_system = search_system

    def find_duplicates(self,
                       similarity_threshold=0.95,
                       top_k=5):
        """检测重复图像

        Args:
            similarity_threshold: 相似度阈值
            top_k: 检查相似图数量

        Returns:
            重复图像组列表
        """
        # 获取所有图像
        all_images = self.search_system.image_processor.get_image_paths()

        duplicates = []
        processed = set()

        print(f"开始检测 {len(all_images)} 张图像的重复...")

        for idx, img_path in enumerate(all_images):
            if img_path in processed:
                continue

            # 搜索相似图像
            try:
                results = self.search_system.search_by_image(
                    img_path,
                    limit=top_k,
                    display_results=False
                )

                if not results:
                    continue

                # 查找高度相似的图像
                similar_group = []
                for result in results[0]:
                    filepath = result['entity']['filepath']
                    similarity = result['distance']

                    # 跳过自身
                    if filepath == img_path:
                        continue

                    # 相似度超过阈值
                    if similarity >= similarity_threshold:
                        similar_group.append({
                            "filepath": filepath,
                            "similarity": similarity
                        })
                        processed.add(filepath)

                # 如果有重复
                if similar_group:
                    duplicates.append({
                        "original": img_path,
                        "duplicates": similar_group
                    })
                    processed.add(img_path)

                if (idx + 1) % 100 == 0:
                    print(f"已检测 {idx + 1}/{len(all_images)} 张图像")

            except Exception as e:
                print(f"跳过图像 {img_path}: {e}")

        return duplicates

    def generate_duplicate_report(self, duplicates, output_file="duplicates.txt"):
        """生成去重报告

        Args:
            duplicates: 重复图像列表
            output_file: 报告文件路径
        """
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(f"图像去重报告\n")
            f.write(f"=" * 60 + "\n\n")
            f.write(f"发现 {len(duplicates)} 组重复图像\n\n")

            for idx, group in enumerate(duplicates):
                f.write(f"组 {idx + 1}:\n")
                f.write(f"  原始图像: {group['original']}\n")
                f.write(f"  重复图像:\n")

                for dup in group['duplicates']:
                    f.write(f"    - {dup['filepath']} "
                           f"(相似度: {dup['similarity']:.4f})\n")

                f.write("\n")

        print(f"报告已保存: {output_file}")

    def auto_delete_duplicates(self, duplicates, keep="original"):
        """自动删除重复图像

        Args:
            duplicates: 重复图像列表
            keep: 保留策略 ("original" 或 "highest_quality")
        """
        deleted_count = 0

        for group in duplicates:
            if keep == "original":
                # 删除所有重复,保留原始
                for dup in group['duplicates']:
                    try:
                        os.remove(dup['filepath'])
                        deleted_count += 1
                        print(f"已删除: {dup['filepath']}")
                    except Exception as e:
                        print(f"删除失败 {dup['filepath']}: {e}")

        print(f"\n总计删除 {deleted_count} 张重复图像")

# 使用示例
detector = ImageDuplicateDetector(search_system)

# 检测重复
duplicates = detector.find_duplicates(
    similarity_threshold=0.95,
    top_k=10
)

print(f"\n发现 {len(duplicates)} 组重复图像")

# 生成报告
detector.generate_duplicate_report(duplicates, "output/duplicates_report.txt")

# 自动删除 (谨慎使用!)
# detector.auto_delete_duplicates(duplicates, keep="original")
```

---

## 7.4 商标检索

### 场景描述

企业上传新商标设计,检索是否存在相似已注册商标

---

### 实现代码

```python
class TrademarkSearch:
    """商标检索系统"""

    def __init__(self, search_system):
        self.search_system = search_system

    def check_trademark_similarity(self,
                                  new_trademark_path,
                                  similarity_threshold=0.85,
                                  top_k=50):
        """检查商标相似性

        Args:
            new_trademark_path: 新商标图片路径
            similarity_threshold: 相似度阈值
            top_k: 检索数量

        Returns:
            相似商标列表
        """
        print(f"检索商标: {new_trademark_path}")

        # 搜索相似商标
        results = self.search_system.search_by_image(
            new_trademark_path,
            limit=top_k,
            display_results=False
        )

        if not results:
            print("未找到相似商标")
            return []

        # 过滤高相似度结果
        similar_trademarks = []
        for result in results[0]:
            similarity = result['distance']

            if similarity >= similarity_threshold:
                similar_trademarks.append({
                    "filepath": result['entity']['filepath'],
                    "similarity": similarity,
                    # 从数据库查询商标信息
                    # "trademark_id": ...,
                    # "owner": ...,
                    # "registration_date": ...,
                })

        return similar_trademarks

    def generate_risk_report(self,
                            new_trademark_path,
                            similar_trademarks,
                            output_file="trademark_risk_report.pdf"):
        """生成风险报告

        Args:
            new_trademark_path: 新商标路径
            similar_trademarks: 相似商标列表
            output_file: 报告文件路径
        """
        # 评估风险级别
        if not similar_trademarks:
            risk_level = "低"
            risk_color = "green"
        elif similar_trademarks[0]['similarity'] > 0.95:
            risk_level = "高"
            risk_color = "red"
        elif similar_trademarks[0]['similarity'] > 0.90:
            risk_level = "中"
            risk_color = "orange"
        else:
            risk_level = "低"
            risk_color = "green"

        # 生成报告 (简化版,实际应使用 PDF 库)
        print("\n" + "=" * 60)
        print("商标相似性风险报告")
        print("=" * 60)
        print(f"\n新商标: {new_trademark_path}")
        print(f"风险级别: {risk_level}")
        print(f"\n发现 {len(similar_trademarks)} 个相似已注册商标:\n")

        for idx, tm in enumerate(similar_trademarks[:5]):
            print(f"{idx + 1}. 相似度: {tm['similarity']:.4f}")
            print(f"   文件: {tm['filepath']}")
            print()

        print("=" * 60)

        # 显示可视化对比
        self._visualize_comparison(
            new_trademark_path,
            similar_trademarks[:5]
        )

    def _visualize_comparison(self, new_tm_path, similar_tms):
        """可视化对比"""
        import matplotlib.pyplot as plt
        from PIL import Image

        fig, axes = plt.subplots(1, len(similar_tms) + 1, figsize=(15, 3))
        fig.suptitle("商标相似性对比", fontsize=16)

        # 显示新商标
        new_img = Image.open(new_tm_path)
        axes[0].imshow(new_img)
        axes[0].set_title("新商标", fontweight='bold', color='blue')
        axes[0].axis('off')

        # 显示相似商标
        for idx, tm in enumerate(similar_tms):
            img = Image.open(tm['filepath'])
            axes[idx + 1].imshow(img)
            axes[idx + 1].set_title(
                f"相似度: {tm['similarity']:.3f}",
                color='red' if tm['similarity'] > 0.95 else 'orange'
            )
            axes[idx + 1].axis('off')

        plt.tight_layout()
        plt.show()

# 使用示例
trademark_search = TrademarkSearch(search_system)

# 检查新商标
new_logo = "uploads/new_company_logo.png"
similar = trademark_search.check_trademark_similarity(
    new_logo,
    similarity_threshold=0.85,
    top_k=100
)

if similar:
    print(f"⚠️  警告: 发现 {len(similar)} 个相似商标!")

    # 生成风险报告
    trademark_search.generate_risk_report(new_logo, similar)
else:
    print("✓ 未发现高度相似的已注册商标")
```

---

# 第八部分：性能优化

## GPU 加速

```python
# 检查 GPU 可用性
import torch

if torch.cuda.is_available():
    print(f"GPU: {torch.cuda.get_device_name(0)}")
    print(f"显存: {torch.cuda.get_device_properties(0).total_memory / 1e9:.2f} GB")
else:
    print("使用 CPU 模式")

# GPU 性能优化建议:
# 1. 增大 batch_size (充分利用 GPU)
search_system.index_images(batch_size=64)  # CPU: 16, GPU: 64-128

# 2. 使用混合精度 (减少显存占用)
# 需要修改 CLIPEncoder 代码,使用 torch.cuda.amp

# 3. 固定 CUDA 内存分配
torch.cuda.empty_cache()
```

---

## Milvus 索引优化

```python
# 1. 调整 HNSW 参数
config.milvus.index_params = {
    "M": 16,               # 增大: 精度 ↑, 内存 ↑
    "efConstruction": 128  # 增大: 精度 ↑, 索引时间 ↑
}

# 2. 搜索时调整 ef 参数
search_params = {
    "metric_type": "COSINE",
    "params": {
        "ef": 128  # 增大: 召回 ↑, 速度 ↓
    }
}

results = search_system.db_manager.search(
    query_vectors=[query_vector],
    search_params=search_params
)

# 3. 使用 GPU 索引 (需要 GPU 版本 Milvus)
config.milvus.index_type = "GPU_IVF_FLAT"
```

---

## 缓存策略

```python
from functools import lru_cache

class CachedCLIPEncoder(CLIPEncoder):
    """带缓存的 CLIP 编码器"""

    @lru_cache(maxsize=1000)
    def encode_text(self, text: str):
        """缓存文本编码结果"""
        return super().encode_text(text)

# 使用缓存编码器
search_system.encoder = CachedCLIPEncoder()

# 重复查询会直接从缓存返回
search_system.search_by_text("cat")  # 第一次: 编码
search_system.search_by_text("cat")  # 第二次: 缓存命中
```

---

# 第九部分：问题排查与调试

## 常见问题

### 1. CLIP 模型加载失败

```
错误: OSError: Can't load tokenizer...

解决:
  1. 检查网络连接 (需要下载模型)
  2. 手动下载模型到 ~/.cache/clip/
  3. 使用镜像源:
     pip install git+https://gitee.com/...
```

---

### 2. Milvus 连接失败

```
错误: MilvusException: <MilvusClient> can not be connected

解决:
  1. 检查 Milvus 服务是否启动:
     docker-compose ps

  2. 检查端口是否开放:
     netstat -an | grep 19530

  3. 使用 Lite 模式 (无需服务):
     client = MilvusClient()  # 自动使用 Lite
```

---

### 3. 搜索结果不准确

```
问题: 搜索 "cat" 返回狗的图片

排查:
  1. 检查图像是否正确索引
  2. 检查相似度阈值
  3. 检查查询文本是否准确
  4. 尝试更大的 CLIP 模型

优化:
  # 使用更大的模型
  config.clip.model_name = "ViT-L/14"

  # 调整搜索参数
  config.milvus.index_params = {"M": 16, "efConstruction": 128}
```

---

### 4. 内存不足

```
错误: CUDA out of memory

解决:
  1. 减小 batch_size:
     search_system.index_images(batch_size=8)

  2. 使用 CPU 模式:
     export CUDA_VISIBLE_DEVICES=""

  3. 增加系统内存/显存
```

---

## 调试技巧

### 启用详细日志

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)

# 查看 CLIP 编码日志
# 查看 Milvus 操作日志
# 查看图像处理日志
```

---

### 性能分析

```python
import cProfile
import pstats

# 分析索引性能
profiler = cProfile.Profile()
profiler.enable()

search_system.index_images(batch_size=32)

profiler.disable()
stats = pstats.Stats(profiler)
stats.sort_stats('cumulative')
stats.print_stats(20)  # 打印 Top 20 最耗时函数
```

---

## 总结

本文档提供了 CLIP 图像搜索系统的完整指南,涵盖:

1. **技术原理**: CLIP 模型、Milvus 向量库、相似度检索
2. **环境搭建**: 依赖安装、配置说明
3. **核心模块**: 编码器、数据库管理、图像处理、搜索系统
4. **快速开始**: 基础用法、文本搜索、以图搜图
5. **高级功能**: 批量索引、增量更新、结果可视化
6. **实战案例**: 电商、设计素材、图像去重、商标检索
7. **性能优化**: GPU 加速、索引优化、缓存策略
8. **问题排查**: 常见错误、调试技巧

---

**文档版本**: v1.0
**最后更新**: 2025-12-16
**维护者**: AI Engineering Training Team
**基于项目**: week07/standalone_projects/p25-CLIP
