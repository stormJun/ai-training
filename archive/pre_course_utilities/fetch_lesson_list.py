#!/usr/bin/env python3
"""
自动获取课程列表并批量下载
使用缓存的 token 自动获取所有课程信息
"""
import json
import subprocess
import sys
from pathlib import Path

def get_cached_token():
    """从缓存读取 token"""
    script_dir = Path(__file__).parent
    token_manager = script_dir / 'token_manager.py'

    result = subprocess.run(
        ['python3', str(token_manager), 'get'],
        capture_output=True,
        text=True
    )

    if result.returncode != 0:
        print("❌ 没有缓存的 token，请先设置：", file=sys.stderr)
        print("   python token_manager.py set 'VTJ...'", file=sys.stderr)
        sys.exit(1)

    return result.stdout.strip()

def fetch_lesson_list(course_id=41):
    """使用 token 获取课程列表"""
    token = get_cached_token()

    curl_cmd = [
        'curl', '-s',
        '-H', 'Host: api.ixunke.cn',
        '-H', 'x-platform: mp',
        '-H', 'content-type: application/json',
        '-H', 'x-systemType: ios',
        '-H', 'User-Agent: Mozilla/5.0 (iPhone; CPU iPhone OS 18_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148 MicroMessenger/8.0.69(0x18004533) NetType/WIFI Language/zh_CN',
        '-H', 'Referer: https://servicewechat.com/wx613cd6930dab2d0a/2/page-frame.html',
        '--compressed',
        f'https://api.ixunke.cn/appni3brwoydrxr/api/lesson?courseId={course_id}&list=true&rewardedAd=1&app=true&token={token}'
    ]

    result = subprocess.run(curl_cmd, capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ 请求失败: {result.stderr}", file=sys.stderr)
        sys.exit(1)

    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError as e:
        print(f"❌ 响应不是有效的 JSON: {e}", file=sys.stderr)
        print(f"原始响应: {result.stdout[:500]}", file=sys.stderr)
        sys.exit(1)

    if data.get('errno') != 0:
        print(f"❌ API 返回错误: {data}", file=sys.stderr)
        if 'token' in str(data).lower() and 'invalid' in str(data).lower():
            print("\n💡 Token 可能已过期，请更新：", file=sys.stderr)
            print("   1. 在小程序中打开课程页面", file=sys.stderr)
            print("   2. 从 Charles 抓取新的 token", file=sys.stderr)
            print("   3. python token_manager.py set 'VTJ...'", file=sys.stderr)
        sys.exit(1)

    return data.get('data', [])

def main():
    course_id = sys.argv[1] if len(sys.argv) > 1 else 41

    print(f">> 获取课程 {course_id} 的课时列表...")
    lessons = fetch_lesson_list(course_id)

    if not lessons:
        print("❌ 没有获取到课时数据")
        sys.exit(1)

    print(f"✓ 获取到 {len(lessons)} 个课时\n")

    # 输出课时信息
    for lesson in lessons:
        lesson_id = lesson['id']
        title = lesson['title']
        room_id = lesson.get('relateRoomId', 'N/A')
        duration = lesson.get('mediaTime', 0)
        duration_min = duration // 60

        print(f"  [{lesson_id}] {title}")
        print(f"      Room ID: {room_id}, 时长: {duration_min} 分钟")

    # 保存为 JSON 供脚本使用
    output_file = Path(__file__).parent / 'lesson_list.json'
    output_file.write_text(json.dumps(lessons, indent=2, ensure_ascii=False))
    print(f"\n✓ 课时列表已保存到: {output_file}")

    # 提示下载命令
    print("\n💡 批量下载所有课程：")
    print(f"   bash fetch_course_to_mp4.sh")
    print("\n💡 下载单个课程：")
    print(f"   ONLY_LESSON_ID={lessons[0]['id']} bash fetch_course_to_mp4.sh")

if __name__ == '__main__':
    main()
