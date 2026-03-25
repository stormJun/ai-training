#!/bin/bash
# Android 小程序包查找脚本 - 详细诊断版

echo "🔍 Android 微信小程序包诊断工具"
echo "=================================="
echo ""

# 检查 adb 连接
echo ">> 步骤 1: 检查 adb 连接"
adb devices -l
if [ $? -ne 0 ]; then
    echo "❌ adb 未安装或未找到"
    echo "请先安装: brew install android-platform-tools"
    exit 1
fi

device_count=$(adb devices | grep -v "List" | grep "device" | wc -l)
if [ $device_count -eq 0 ]; then
    echo "❌ 没有检测到设备"
    echo "请确保："
    echo "  1. 手机已用 USB 连接电脑"
    echo "  2. 手机已开启 USB 调试"
    echo "  3. 手机上点击了 '允许 USB 调试'"
    exit 1
fi

echo "✓ 设备已连接"
echo ""

# 检查权限
echo ">> 步骤 2: 检查权限"
adb shell "ls /data/data/com.tencent.mm 2>&1" | head -3
if echo "$?" | grep -q "Permission denied\|not permitted"; then
    echo "⚠️  权限被拒绝"
    echo ""
    echo "这个目录需要 ROOT 权限才能访问！"
    echo ""
    echo "解决方案："
    echo "  方案 A: 使用备份方式提取（不需要 root）"
    echo "  方案 B: 手机获取 root 权限（复杂）"
    echo "  方案 C: 使用微信开发者工具（推荐）"
    echo ""
    echo "继续执行方案 A（备份提取）？[y/n]"
    read -r answer
    if [ "$answer" = "y" ]; then
        echo ""
        echo ">> 尝试备份方式..."
        echo "运行以下命令："
        echo "  adb backup -f wxbackup.ab com.tencent.mm"
        exit 0
    else
        exit 1
    fi
fi

echo "✓ 有访问权限（或手机已 root）"
echo ""

# 查找微信目录
echo ">> 步骤 3: 查找微信数据目录"
wechat_dirs=$(adb shell "ls -d /data/data/com.tencent.mm/MicroMsg/*/ 2>/dev/null" | grep -v "^$")

if [ -z "$wechat_dirs" ]; then
    echo "❌ 未找到微信数据目录"
    echo "可能原因："
    echo "  1. 微信未安装"
    echo "  2. 没有登录微信"
    echo "  3. 需要 root 权限"
    exit 1
fi

echo "✓ 找到微信数据目录："
echo "$wechat_dirs" | head -5
echo ""

# 查找 appbrand 目录
echo ">> 步骤 4: 查找小程序目录"
for dir in $wechat_dirs; do
    appbrand_dir="${dir}appbrand/pkg/"
    echo "检查: $appbrand_dir"
    adb shell "ls $appbrand_dir 2>/dev/null" | head -3
done
echo ""

# 查找 .wxapkg 文件
echo ">> 步骤 5: 查找小程序包文件"
echo "这可能需要几秒钟..."
wxapkg_files=$(adb shell "find /data/data/com.tencent.mm/MicroMsg -name '*.wxapkg' 2>/dev/null")

if [ -z "$wxapkg_files" ]; then
    echo "❌ 未找到任何 .wxapkg 文件"
    echo ""
    echo "可能原因："
    echo "  1. 小程序缓存已清理"
    echo "  2. 未在微信中打开过任何小程序"
    echo "  3. 微信版本太新，存储位置改变"
    echo "  4. 需要 root 权限"
    echo ""
    echo "💡 解决方法："
    echo "  1. 在手机微信中打开目标小程序"
    echo "  2. 浏览小程序的所有页面"
    echo "  3. 等待 1-2 分钟让缓存完成"
    echo "  4. 重新运行此脚本"
    exit 1
fi

echo "✓ 找到 .wxapkg 文件："
echo "$wxapkg_files"
echo ""

# 查找目标小程序
echo ">> 步骤 6: 查找目标小程序 (wx613cd6930dab2d0a)"
target_files=$(echo "$wxapkg_files" | grep "wx613cd6930dab2d0a")

if [ -z "$target_files" ]; then
    echo "❌ 未找到目标小程序包"
    echo ""
    echo "找到的其他小程序："
    echo "$wxapkg_files" | grep -o "wx[a-z0-9]*" | sort -u | head -10
    echo ""
    echo "💡 请确保："
    echo "  1. 在手机微信中打开了该小程序"
    echo "  2. AppID 是 wx613cd6930dab2d0a"
    echo "  3. 小程序已完全加载"
    exit 1
fi

echo "✓ 找到目标小程序！"
echo "$target_files"
echo ""

# 提取文件
echo ">> 步骤 7: 提取小程序包到电脑"
output_dir="$HOME/Desktop/wxapkg_extracted"
mkdir -p "$output_dir"

while IFS= read -r file; do
    if [ -n "$file" ]; then
        filename=$(basename "$file")
        echo "提取: $filename"
        adb pull "$file" "$output_dir/$filename"
    fi
done <<< "$target_files"

echo ""
echo "✅ 完成！文件已保存到:"
echo "   $output_dir"
echo ""
echo "💡 下一步："
echo "   1. 安装反编译工具: git clone https://github.com/xuedingmiaojun/wxappUnpacker"
echo "   2. cd wxappUnpacker && npm install"
echo "   3. node wuWxapkg.js $output_dir/*.wxapkg"
