# MASSIVE 中文数据集说明文档

## 📋 数据集概述

本数据集是 MASSIVE (Multilingual Amazon Slu resource package) 项目的简体中文子集，用于自然语言理解（NLU）任务，特别是意图分类和槽位填充。

- **数据来源**: Amazon MASSIVE 1.1
- **语言**: 简体中文 (zh-CN)
- **数据格式**: JSONL (每行一个 JSON 对象)
- **文件大小**: 11MB
- **总样本数**: 16,520 条

## 📊 数据统计

### 数据集划分

| 数据集 | 样本数 | 占比 |
|--------|--------|------|
| 训练集 (train) | 11,514 | 69.7% |
| 验证集 (dev) | 2,033 | 12.3% |
| 测试集 (test) | 2,974 | 18.0% |

### 核心统计指标

- **场景数量**: 18 个不同的应用场景
- **意图数量**: 60 种不同的用户意图
- **槽位类型**: 55 种实体槽位类型
- **平均语句长度**: 10.5 字符

## 🎯 场景分布

按样本数量降序排列：

| 场景 | 训练集 | 验证集 | 测试集 | 总计 | 占比 |
|------|--------|--------|--------|------|------|
| calendar (日历) | 1,688 | 280 | 402 | 2,370 | 14.3% |
| play (播放) | 1,377 | 260 | 387 | 2,024 | 12.3% |
| qa (问答) | 1,183 | 214 | 288 | 1,685 | 10.2% |
| email (邮件) | 953 | 157 | 271 | 1,381 | 8.4% |
| iot (智能家居) | 769 | 118 | 220 | 1,107 | 6.7% |
| general (通用) | 652 | 122 | 189 | 963 | 5.8% |
| weather (天气) | 573 | 126 | 156 | 855 | 5.2% |
| transport (交通) | 571 | 110 | 124 | 805 | 4.9% |
| lists (列表) | 539 | 112 | 142 | 793 | 4.8% |
| news (新闻) | 503 | 82 | 124 | 709 | 4.3% |
| recommendation (推荐) | 433 | 69 | 94 | 596 | 3.6% |
| datetime (日期时间) | 402 | 73 | 103 | 578 | 3.5% |
| social (社交) | 391 | 68 | 106 | 565 | 3.4% |
| alarm (闹钟) | 390 | 64 | 96 | 550 | 3.3% |
| music (音乐) | 332 | 56 | 81 | 469 | 2.8% |
| audio (音频) | 290 | 35 | 62 | 387 | 2.3% |
| takeaway (外卖) | 257 | 44 | 57 | 358 | 2.2% |
| cooking (烹饪) | 211 | 43 | 72 | 326 | 2.0% |

## 🎪 Top 15 意图分布（训练集）

| 意图 | 样本数 | 描述 |
|------|--------|------|
| calendar_set | 810 | 设置日历事件 |
| play_music | 639 | 播放音乐 |
| weather_query | 573 | 查询天气 |
| calendar_query | 566 | 查询日历 |
| general_quirky | 555 | 通用闲聊 |
| qa_factoid | 544 | 事实问答 |
| news_query | 503 | 查询新闻 |
| email_query | 418 | 查询邮件 |
| email_sendemail | 354 | 发送邮件 |
| datetime_query | 350 | 查询日期时间 |
| calendar_remove | 312 | 删除日历事件 |
| social_post | 283 | 发布社交动态 |
| play_radio | 283 | 播放广播 |
| qa_definition | 267 | 定义查询 |
| transport_query | 227 | 查询交通 |

## 🏷️ Top 20 槽位类型分布

| 槽位类型 | 出现次数 | 描述 |
|----------|----------|------|
| date | 2,560 | 日期 |
| place_name | 1,568 | 地点名称 |
| event_name | 1,408 | 事件名称 |
| person | 1,211 | 人名 |
| time | 1,120 | 时间 |
| media_type | 703 | 媒体类型 |
| business_name | 533 | 商家名称 |
| weather_descriptor | 456 | 天气描述词 |
| transport_type | 436 | 交通方式 |
| food_type | 417 | 食物类型 |
| relation | 350 | 关系 |
| timeofday | 345 | 时段 |
| artist_name | 338 | 艺术家名称 |
| definition_word | 319 | 定义词 |
| device_type | 318 | 设备类型 |
| currency_name | 312 | 货币名称 |
| list_name | 287 | 列表名称 |
| house_place | 280 | 房间位置 |
| news_topic | 272 | 新闻主题 |
| music_genre | 267 | 音乐流派 |

## 📝 数据结构

每条数据是一个 JSON 对象，包含以下字段：

```json
{
  "id": "0",
  "locale": "zh-CN",
  "partition": "test",
  "scenario": "alarm",
  "intent": "alarm_set",
  "utt": "这周五点叫我起床",
  "annot_utt": "[date : 这周] [time : 五点] 叫我起床",
  "worker_id": "23",
  "slot_method": [
    {
      "slot": "time",
      "method": "translation"
    }
  ],
  "judgments": [
    {
      "worker_id": "33",
      "intent_score": 1,
      "slots_score": 1,
      "grammar_score": 4,
      "spelling_score": 2,
      "language_identification": "target"
    }
  ]
}
```

### 字段说明

| 字段 | 类型 | 说明 |
|------|------|------|
| id | string | 数据唯一标识符 |
| locale | string | 语言区域代码 (zh-CN) |
| partition | string | 数据集划分: train/dev/test |
| scenario | string | 应用场景类别 (18种) |
| intent | string | 用户意图类别 (60种) |
| utt | string | 原始用户语句 |
| annot_utt | string | 带槽位标注的语句，格式为 [槽位类型 : 槽位值] |
| worker_id | string | 标注工人ID |
| slot_method | array | 槽位标注方法列表 |
| judgments | array | 质量评审结果（每条数据有3个评审员） |

### 质量评分标准

**intent_score (意图匹配度)**
- 0: 不匹配
- 1: 完全匹配
- 2: 合理解释

**slots_score (槽位匹配度)**
- 0: 不匹配
- 1: 完全匹配
- 2: 无槽位

**grammar_score (语法评分)**
- 0: 完全不自然（无意义）
- 1: 严重错误
- 2: 有些错误
- 3: 足够好
- 4: 完美

**spelling_score (拼写评分)**
- 0: 超过2个拼写错误
- 1: 1-2个拼写错误
- 2: 无拼写错误

## 💡 数据示例

### 示例 1: 日历场景 - 设置日历事件

```json
{
  "scenario": "calendar",
  "intent": "calendar_set",
  "utt": "今天下午三点提醒我开会",
  "annot_utt": "[date : 今天] [timeofday : 下午] [time : 三点] 提醒我 [event_name : 开会]"
}
```

### 示例 2: 音乐场景 - 播放音乐

```json
{
  "scenario": "music",
  "intent": "music_likeness",
  "utt": "我喜欢张杰的歌曲",
  "annot_utt": "我喜欢 [artist_name : 张杰] 的歌曲"
}
```

### 示例 3: 邮件场景 - 发送邮件

```json
{
  "scenario": "email",
  "intent": "email_sendemail",
  "utt": "给李先生发邮件说我准备在二零一七年二月一日下午五点在办公室与他会面",
  "annot_utt": "给 [person : 李先生] 发邮件说我准备在 [date : 二零一七年二月一日] [time : 下午五点] 在 [place_name : 办公室] [event_name : 与他会面]"
}
```

### 示例 4: 天气场景 - 查询天气

```json
{
  "scenario": "weather",
  "intent": "weather_query",
  "utt": "北京明天会下雨吗",
  "annot_utt": "[place_name : 北京] [date : 明天] 会 [weather_descriptor : 下雨] 吗"
}
```

### 示例 5: 智能家居场景 - 控制设备

```json
{
  "scenario": "iot",
  "intent": "iot_hue_lightchange",
  "utt": "把客厅的灯调暗一点",
  "annot_utt": "把 [house_place : 客厅] 的 [device_type : 灯] 调暗一点"
}
```

## 🎯 适用任务

### 1. 意图分类 (Intent Classification)
识别用户输入的意图类别（60类）

**输入**: "今天北京天气怎么样"
**输出**: weather_query

### 2. 槽位填充 (Slot Filling)
从用户输入中提取关键信息实体（55种槽位类型）

**输入**: "今天北京天气怎么样"
**输出**:
- date: 今天
- place_name: 北京

### 3. 场景分类 (Scenario Classification)
识别对话所属的应用场景（18类）

**输入**: "今天北京天气怎么样"
**输出**: weather

### 4. 联合任务 (Joint Training)
同时进行意图分类和槽位填充的多任务学习

## 📈 数据质量

- ✅ **高质量标注**: 每条数据经过3个独立标注员质量评审
- ✅ **真实场景**: 基于 SLURP 数据集本地化，贴近实际语音助手使用场景
- ✅ **平衡分布**: 涵盖18个不同场景，分布相对均衡
- ✅ **丰富标注**: 包含意图、槽位、场景等多维度标注
- ✅ **质量评分**: 提供语法、拼写、语言识别等质量指标

## 🚀 使用建议

### 数据加载示例

```python
import json

def load_massive_data(file_path, partition=None):
    """
    加载 MASSIVE 中文数据

    Args:
        file_path: zh-CN.jsonl 文件路径
        partition: 'train', 'dev', 'test' 或 None (加载全部)

    Returns:
        List of data samples
    """
    data = []
    with open(file_path, 'r', encoding='utf-8') as f:
        for line in f:
            sample = json.loads(line.strip())
            if partition is None or sample['partition'] == partition:
                data.append(sample)
    return data

# 加载训练集
train_data = load_massive_data('zh-CN.jsonl', partition='train')
print(f"训练集样本数: {len(train_data)}")

# 示例：提取意图和语句
for sample in train_data[:3]:
    print(f"语句: {sample['utt']}")
    print(f"意图: {sample['intent']}")
    print(f"场景: {sample['scenario']}")
    print()
```

### 槽位解析示例

```python
import re

def parse_slots(annot_utt):
    """
    从标注语句中解析槽位

    Args:
        annot_utt: 带槽位标注的语句

    Returns:
        List of (slot_type, slot_value) tuples
    """
    pattern = r'\[([^:]+)\s*:\s*([^\]]+)\]'
    slots = re.findall(pattern, annot_utt)
    return [(slot_type.strip(), slot_value.strip()) for slot_type, slot_value in slots]

# 示例
annot_utt = "给 [person : 李先生] 发邮件说我准备在 [date : 二零一七年二月一日] [time : 下午五点] 在 [place_name : 办公室] [event_name : 与他会面]"
slots = parse_slots(annot_utt)
print("槽位提取结果:")
for slot_type, slot_value in slots:
    print(f"  {slot_type}: {slot_value}")
```

### 数据预处理建议

1. **文本清洗**: 移除或标准化特殊字符
2. **槽位处理**:
   - 保留槽位标注用于序列标注任务
   - 移除槽位标注得到纯文本用于分类任务
3. **类别平衡**: 考虑对少数类进行过采样或使用类别权重
4. **数据增强**:
   - 同义词替换
   - 回译（中文→英文→中文）
   - 槽位值替换

## 📚 相关资源

- **论文**: [MASSIVE: A 1M-Example Multilingual Natural Language Understanding Dataset](https://arxiv.org/abs/2204.08582)
- **官方仓库**: [https://github.com/alexa/massive](https://github.com/alexa/massive)
- **数据来源**: Amazon MASSIVE 1.1
- **基准数据**: SLURP (Spoken Language Understanding Resource Package)

## 📄 引用

如果使用本数据集，请引用以下论文：

```bibtex
@misc{fitzgerald2022massive,
    title={MASSIVE: A 1M-Example Multilingual Natural Language Understanding Dataset with 51 Typologically-Diverse Languages},
    author={Jack FitzGerald and Christopher Hench and Charith Peris and Scott Mackie and Kay Rottmann and Ana Sanchez and Aaron Nash and Liam Urbach and Vishesh Kakarala and Richa Singh and Swetha Ranganath and Laurie Crist and Misha Britan and Wouter Leeuwis and Gokhan Tur and Prem Natarajan},
    year={2022},
    eprint={2204.08582},
    archivePrefix={arXiv},
    primaryClass={cs.CL}
}
```

## 📧 联系方式

如有问题或建议，请联系数据集维护者或提交 Issue。

---

**最后更新**: 2025-12-17
**数据版本**: MASSIVE 1.1
**语言**: 简体中文 (zh-CN)
