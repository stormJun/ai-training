#!/usr/bin/env python3
"""
从 MASSIVE 官方完整格式提取简化版中文数据
"""

import json
import argparse
from pathlib import Path
from collections import defaultdict

# 60种意图的中文翻译
INTENT_ZH = {
    "alarm_query": "闹钟查询",
    "alarm_remove": "移除闹钟",
    "alarm_set": "设置闹钟",
    "audio_volume_down": "降低音量",
    "audio_volume_mute": "静音",
    "audio_volume_up": "提高音量",
    "calendar_query": "日历查询",
    "calendar_remove": "删除日历",
    "calendar_set": "设置日历",
    "cooking_recipe": "烹饪食谱",
    "datetime_convert": "时间转换",
    "datetime_query": "时间查询",
    "email_addcontact": "添加邮件联系人",
    "email_query": "查询邮件",
    "email_querycontact": "查询邮件联系人",
    "email_sendemail": "发送邮件",
    "general_joke": "讲笑话",
    "general_quirky": "闲聊",
    "iot_cleaning": "智能清洁",
    "iot_coffee": "智能咖啡",
    "iot_hue_lightchange": "智能灯光变化",
    "iot_hue_lightdim": "调暗灯光",
    "iot_hue_lightoff": "关闭灯光",
    "iot_hue_lighton": "打开灯光",
    "iot_hue_lightup": "调亮灯光",
    "iot_wemo_off": "关闭智能插座",
    "iot_wemo_on": "打开智能插座",
    "lists_createoradd": "创建或添加列表",
    "lists_query": "查询列表",
    "lists_remove": "删除列表",
    "music_likeness": "音乐喜好",
    "music_query": "音乐查询",
    "music_settings": "音乐设置",
    "news_query": "新闻查询",
    "play_audiobook": "播放有声书",
    "play_game": "玩游戏",
    "play_music": "播放音乐",
    "play_podcasts": "播放播客",
    "play_radio": "播放广播",
    "qa_currency": "货币问答",
    "qa_definition": "定义问答",
    "qa_factoid": "事实问答",
    "qa_maths": "数学问答",
    "qa_stock": "股票问答",
    "recommendation_events": "活动推荐",
    "recommendation_locations": "地点推荐",
    "recommendation_movies": "电影推荐",
    "social_post": "发布动态",
    "social_query": "查询动态",
    "takeaway_order": "外卖订购",
    "takeaway_query": "外卖查询",
    "transport_query": "交通查询",
    "transport_taxi": "打车",
    "transport_ticket": "交通票务",
    "transport_traffic": "交通路况",
    "weather_query": "天气查询",
}


def extract_zh_data(official_file: str, output_dir: str):
    """
    从官方 zh-CN.jsonl 提取简化版数据

    Args:
        official_file: 官方数据文件 (例如: 1.0/data/zh-CN.jsonl)
        output_dir: 输出目录
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(exist_ok=True)

    # 按 partition 分组
    partitions = defaultdict(list)

    # 创建 intent 到数字的映射
    intent_to_num = {}

    print(f"📥 读取官方数据: {official_file}")
    with open(official_file, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue

            item = json.loads(line)

            # 构建 intent 映射
            intent = item['intent']
            if intent not in intent_to_num:
                intent_to_num[intent] = len(intent_to_num)

            # 转换为简化格式
            simplified = {
                "id": item['id'],
                "label": intent_to_num[intent],
                "text": item['utt'],
                "label_text": intent,
                "label_text_ch": INTENT_ZH.get(intent, intent)
            }

            # 分组
            partition = item['partition']
            partitions[partition].append(simplified)

    # 保存各个分区
    for partition, items in partitions.items():
        output_file = output_dir / f"{partition}.jsonl"
        with open(output_file, 'w', encoding='utf-8') as f:
            for item in items:
                f.write(json.dumps(item, ensure_ascii=False) + '\n')

        print(f"✅ {partition:12s}: {len(items):5d} 条 → {output_file}")

    # 保存 intent 映射
    mapping_file = output_dir / "intent_mapping.json"
    with open(mapping_file, 'w', encoding='utf-8') as f:
        json.dump({
            "intent_to_num": intent_to_num,
            "intent_to_zh": INTENT_ZH
        }, f, indent=2, ensure_ascii=False)

    print(f"\n💾 意图映射已保存: {mapping_file}")
    print(f"\n总意图数: {len(intent_to_num)}")


def main():
    parser = argparse.ArgumentParser(
        description="从 MASSIVE 官方格式提取简化版中文数据"
    )
    parser.add_argument(
        "--input",
        required=True,
        help="官方中文数据文件 (例如: 1.0/data/zh-CN.jsonl)"
    )
    parser.add_argument(
        "--output",
        default="amazon_massive_intent_zh-CN_extracted",
        help="输出目录"
    )

    args = parser.parse_args()
    extract_zh_data(args.input, args.output)


if __name__ == "__main__":
    main()
