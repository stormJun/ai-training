"""
MASSIVE 数据集转换脚本

这个脚本将 MASSIVE 数据集从 JSONL 格式转换为 HuggingFace Datasets 的 Apache Arrow 格式。

主要功能：
1. 读取 JSONL 格式的 MASSIVE 数据文件
2. 解析意图和槽位标注
3. 处理中日韩（CJK）语言的字符级分词
4. 创建数值化的标签（意图和槽位映射到整数 ID）
5. 生成 train/dev/test/hidden_eval 数据集分割
6. 保存为 HuggingFace Datasets 格式（Apache Arrow）

数据集列：
- id: 样本唯一标识符
- locale: 语言区域代码（如 zh-CN、en-US）
- utt: 原始语句文本（分词后的 token 列表）
- annot_utt: 带槽位标注的语句字符串
- domain: 应用场景/领域（如 calendar、weather）
- intent_str: 意图标签字符串
- intent_num: 意图标签数值 ID
- slots_str: 槽位标签字符串列表
- slots_num: 槽位标签数值 ID 列表

Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.

Licensed under the Apache License, Version 2.0 (the "License").
You may not use this file except in compliance with the License.
You may obtain a copy of the License at

  http://www.apache.org/licenses/LICENSE-2.0

Unless required by applicable law or agreed to in writing, software
distributed under the License is distributed on an "AS IS" BASIS,
WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
See the License for the specific language governing permissions and
limitations under the License.
"""

import argparse  # 命令行参数解析
import json  # JSON 数据处理
import os  # 操作系统接口

import datasets  # HuggingFace Datasets 库
from datasets import Dataset  # 单个数据集类

class DatasetCreator:
    """
    数据集创建器类

    用于从 MASSIVE 的 JSONL 格式文件创建 HuggingFace Datasets 格式的数据集。

    主要方法：
    - create_datasets(): 从 JSONL 文件创建数据集分割
    - add_numeric_labels(): 为意图和槽位创建数值标签
    - investigate_datasets(): 打印数据集样本作为检查
    - save_label_dicts(): 保存标签到 ID 的映射字典
    - save_datasets(): 保存数据集到磁盘

    属性：
    - train: 训练集
    - dev: 验证集
    - test: 测试集
    - hidden_eval: 隐藏评估集（用于竞赛）
    - slot_dict: 槽位标签到 ID 的映射
    - intent_dict: 意图标签到 ID 的映射
    """

    def __init__(self):
        """初始化数据集创建器"""
        self.train = None  # 训练集
        self.dev = None  # 验证集
        self.test = None  # 测试集
        self.hidden_eval = None  # 隐藏评估集
        self.slot_dict = None  # 槽位标签映射字典
        self.intent_dict = None  # 意图标签映射字典

    def create_datasets(self, data_paths, char_split_locales=None):
        """
        从 JSONL 文件加载并创建数据集

        参数：
        - data_paths: MASSIVE 数据集路径（可以是字符串或列表）
        - char_split_locales: 需要字符级分词的语言列表（默认：['ja-JP', 'zh-CN', 'zh-TW']）

        处理流程：
        1. 扫描指定路径下的所有 JSONL 文件
        2. 逐行读取 JSON 数据
        3. 根据语言类型进行分词（CJK 语言使用字符级分词）
        4. 解析意图和槽位标注
        5. 将数据按 partition 字段分配到不同的数据集分割中
        """

        # 默认对中日韩语言进行字符级分词
        char_split_locales = ['ja-JP', 'zh-CN', 'zh-TW'] if not char_split_locales \
                                                         else char_split_locales

        # 查找所有数据文件
        files = []
        data_paths = [data_paths] if type(data_paths) == str else data_paths
        for path in data_paths:
            flist = [os.path.join(path,f) \
                     for f in os.listdir(path) \
                     if os.path.isfile(os.path.join(path,f))]
            files = files + flist

        # 逐个文件处理
        for file in files:
            print(f'正在读取数据：{file}')
            massive_raw = []
            # 读取 JSONL 文件（每行一个 JSON 对象）
            with open(file, 'r') as f:
                for line in f:
                    massive_raw.append(json.loads(line))

            # 解析每一行数据，构建内存中的字典结构
            train, dev, test, hid = self._build_in_mem_dicts(
                massive_raw,
                char_split_locales
            )

            # 将新数据与现有数据集合并
            # 如果是第一次添加数据，创建新的 Dataset；否则连接到现有数据集
            if self.train is None and train['id']:
                self.train = Dataset.from_dict(train)
            elif train['id']:
                self.train = datasets.concatenate_datasets([self.train,
                                                            Dataset.from_dict(train)])
            if self.dev is None and dev['id']:
                self.dev = Dataset.from_dict(dev)
            elif dev['id']:
                self.dev = datasets.concatenate_datasets([self.dev, Dataset.from_dict(dev)])
            if self.test is None and test['id']:
                self.test = Dataset.from_dict(test)
            elif test['id']:
                self.test = datasets.concatenate_datasets([self.test, Dataset.from_dict(test)])
            if self.hidden_eval is None and hid['id']:
                self.hidden_eval = Dataset.from_dict(hid)
            elif hid['id']:
                self.hidden_eval = datasets.concatenate_datasets([self.hidden_eval,
                                                                 Dataset.from_dict(hid)])

    @staticmethod
    def _build_in_mem_dicts(massive_data, char_split=None):
        """
        将 JSON 数据解析为扁平的键值对格式

        参数：
        - massive_data: 原始 MASSIVE JSON 数据列表
        - char_split: 需要字符级分词的语言列表

        返回：
        - train, dev, test, hid_eval: 四个字典，每个对应一个数据集分割

        处理逻辑：
        1. 对于 CJK 语言（中日韩），将句子拆分为字符级 token
        2. 对于其他语言，使用空格分词
        3. 解析槽位标注：[slot_type : slot_value] -> BIO 标注格式
        4. 将每个样本分配到对应的数据集分割中
        """

        char_split = ['ja-JP', 'zh-CN', 'zh-TW'] if not char_split else char_split

        # 定义数据集的列名
        cols = ['id', 'locale', 'domain', 'intent_str', 'annot_utt', 'utt',
                'slots_str']
        # 为四个数据集分割初始化空字典
        train, dev = {k: [] for k in cols}, {k: [] for k in cols}
        test, hid_eval = {k: [] for k in cols}, {k: [] for k in cols}

        # 逐行处理原始数据
        for row in massive_data:
            eyed, locale, split, utt = row['id'], row['locale'], row['partition'], row['utt']
            domain = row['scenario'] if 'scenario' in row else ''
            intent = row['intent'] if 'intent' in row else ''
            annot_utt = row['annot_utt'] if 'annot_utt' in row else ''

            # ========== 对中日韩语言进行字符级分词 ==========
            if locale in char_split:
                tokens, labels = [], []
                label = 'Other'  # 默认槽位标签为 'Other'（非实体）
                skip_colon = False
                if annot_utt:
                    # 解析带标注的语句，例如："[date : 今天] 天气"
                    for chunk in annot_utt.split():
                        if chunk.startswith('['):  # 槽位类型开始
                            label = chunk.lstrip('[')
                            skip_colon = True
                            continue
                        if chunk == ':' and skip_colon is True:  # 跳过冒号
                            skip_colon = False
                            continue
                        # keep latin chars together in cases of code switching
                        if isascii(chunk):  # 拉丁字符保持完整（代码切换情况）
                            tokens.append(chunk.strip().rstrip(']'))
                            labels.append(label)
                        else:  # 中日韩字符逐个拆分
                            chars = list(chunk.strip())
                            for char in chars:
                                if char == ']':  # 槽位结束
                                    label = 'Other'
                                else:
                                    tokens.append(char)
                                    labels.append(label)
                # if no annot_utt, then make assumption latin words are space sep already
                else:  # 如果没有标注，假设拉丁词已经用空格分隔
                    for chunk in utt.split():
                        if isascii(chunk):
                            tokens.append(chunk.strip())
                        else:
                            chars = list(chunk.strip())
                            for char in chars:
                                tokens.append(char)

            else:  # ========== 对其他语言使用空格分词 ==========
                # Create the tokens and labels by working left to right of annotated utt
                tokens = utt.split()  # 使用空格分词
                labels = []
                label = 'Other'
                split_annot_utt = annot_utt.split()
                idx = 0
                # 从左到右解析标注语句
                while idx < len(split_annot_utt):
                    if split_annot_utt[idx].startswith('['):  # 槽位开始
                        label = split_annot_utt[idx].lstrip('[')
                        idx += 2  # 跳过 '[slot_type' 和 ':'
                    elif split_annot_utt[idx].endswith(']'):  # 槽位结束
                        labels.append(label)
                        label = 'Other'
                        idx += 1
                    else:  # 槽位值内部
                        labels.append(label)
                        idx += 1

            # 验证 token 和标签数量匹配
            if len(tokens) != len(labels) and labels:
                raise ValueError(f"Token 数量 {tokens} 与标签数量 {labels} 不匹配，"
                                 f"样本 ID: {eyed}，标注语句: {annot_utt}")

            # ========== 根据 partition 字段选择目标数据集 ==========
            if split == 'train':
                dict_view = train  # 训练集
            elif split == 'dev':
                dict_view = dev  # 验证集
            elif split == 'test':
                dict_view = test  # 测试集
            elif split == 'MMNLU-22':
                dict_view = hid_eval  # 隐藏评估集（竞赛用）
            else:
                raise ValueError(f"未知的数据集分割: {split}")

            # 将当前样本的值添加到对应的数据集中
            dict_view['id'].append(eyed)
            dict_view['locale'].append(locale)
            dict_view['domain'].append(domain)
            dict_view['intent_str'].append(intent)
            dict_view['annot_utt'].append(annot_utt)
            dict_view['utt'].append(tokens)
            dict_view['slots_str'].append(labels)

        return train, dev, test, hid_eval

    def investigate_datasets(self):
        """打印每个数据集的第7个样本作为完整性检查"""
        for dataset in [self.train, self.dev, self.test, self.hidden_eval]:
            if dataset:
                print(f"数据集: {dataset}")
                print(f"第7行样本: {dataset[7]}")

    def add_numeric_labels(self):
        """
        为意图和槽位标签创建数值映射

        处理流程：
        1. 收集所有唯一的意图和槽位标签
        2. 创建标签到整数 ID 的映射字典
        3. 为数据集中的每个样本添加 intent_num 和 slots_num 字段

        这个数值映射对于模型训练是必需的（神经网络需要数值输入）。
        """

        if not self.intent_dict:
            # 收集所有唯一的意图标签
            unique_intents = set([])
            for split in [self.train, self.dev, self.test, self.hidden_eval]:
                if split:
                    unique_intents.update([i for i in split['intent_str']])
            # 创建意图标签到 ID 的映射
            self.intent_dict = {k: v for v, k in enumerate(unique_intents)}
            print('检测到的意图标签: ', self.intent_dict)
        else:
            # 如果已有映射，交换键值（从 ID->标签 变为 标签->ID）
            self.intent_dict = {v: int(k) for k, v in self.intent_dict.items()}

        if not self.slot_dict:
            # 收集所有唯一的槽位标签
            unique_slots = set()
            for split in [self.train, self.dev, self.test, self.hidden_eval]:
                if split:
                    for ex_slots in split:
                        unique_slots.update(ex_slots['slots_str'])
            # 创建槽位标签到 ID 的映射
            self.slot_dict = {k: v for v, k in enumerate(unique_slots)}
            print('检测到的槽位标签: ', self.slot_dict)
        else:
            # 交换键值
            self.slot_dict = {v: int(k) for k, v in self.slot_dict.items()}

        # 定义函数：为每个样本创建数值标签
        def create_numeric_labels(example):
            example['slots_num'] = [self.slot_dict[x] for x in example['slots_str']]
            example['intent_num'] = self.intent_dict[example['intent_str']]
            return example

        # 使用 map 方法为所有数据集添加数值标签字段
        print('正在为数据集添加数值意图和槽位标签')
        self.train = self.train.map(create_numeric_labels) if self.train else None
        self.dev = self.dev.map(create_numeric_labels) if self.dev else None
        self.test = self.test.map(create_numeric_labels) if self.test else None
        if self.hidden_eval is not None and self.hidden_eval[0]['intent_str']:
            self.hidden_eval = self.hidden_eval.map(create_numeric_labels)

    def save_label_dicts(self, output_prefix):
        """
        保存标签映射字典到文件

        参数：
        - output_prefix: 输出文件的路径和前缀

        输出文件：
        - {output_prefix}.intents: 意图 ID 到标签的映射
        - {output_prefix}.slots: 槽位 ID 到标签的映射
        """
        with open(output_prefix+'.intents', "w") as i, open(output_prefix+'.slots', "w") as s:
            # 交换键值：从标签->ID 变为 ID->标签
            json.dump({v: k for k, v in self.intent_dict.items()}, i)
            json.dump({v: k for k, v in self.slot_dict.items()}, s)

    def save_datasets(self, output_prefix):
        """
        保存数据集分割到磁盘

        参数：
        - output_prefix: 输出路径和文件前缀

        输出文件：
        - {output_prefix}.train: 训练集
        - {output_prefix}.dev: 验证集
        - {output_prefix}.test: 测试集
        - {output_prefix}.mmnlu22: 隐藏评估集
        """
        for (ds, suf) in [
            (self.train, '.train'),
            (self.dev, '.dev'),
            (self.test, '.test'),
            (self.hidden_eval, '.mmnlu22')
        ]:
            if ds:
                ds.save_to_disk(output_prefix+suf)


def isascii(s):
    """检查字符串是否仅包含 ASCII 字符"""
    try:
        return s.isascii()
    except AttributeError:
        return all([ord(c) < 128 for c in s])


def main():
    """主函数：解析命令行参数并执行数据集转换"""
    parser = argparse.ArgumentParser(description="从 MASSIVE 创建 HuggingFace 数据集")
    parser.add_argument('-d', '--massive-data-paths', nargs='+', help='MASSIVE 数据集路径（可多个）')
    parser.add_argument('-o', '--out-prefix', help='输出路径和文件前缀')
    parser.add_argument('--intent-map', nargs='?', default={},
                        help='可选：已有的意图数值映射文件', required=False)
    parser.add_argument('--slot-map', nargs='?', default={},
                        help='可选：已有的槽位数值映射文件', required=False)
    args = parser.parse_args()

    # 如果提供了已有的映射文件，加载它们
    if args.intent_map:
        with open(args.intent_map, 'r') as f:
            intent_dict = json.load(f)
    else:
        intent_dict = None

    if args.slot_map:
        with open(args.slot_map, 'r') as f:
            slot_dict = json.load(f)
    else:
        slot_dict = None

    # 创建数据集
    ds_creator = DatasetCreator()
    ds_creator.create_datasets(args.massive_data_paths)
    ds_creator.intent_dict = intent_dict
    ds_creator.slot_dict = slot_dict
    ds_creator.add_numeric_labels()
    ds_creator.investigate_datasets()
    ds_creator.save_datasets(args.out_prefix)
    ds_creator.save_label_dicts(args.out_prefix)

# 程序入口点
if __name__ == "__main__":
    main()
