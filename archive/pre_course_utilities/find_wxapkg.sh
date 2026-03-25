#!/bin/bash
# 查找微信小程序包
# AppID: wx613cd6930dab2d0a

echo "🔍 查找微信小程序包..."
echo ""

# macOS 微信路径
WECHAT_PATH="$HOME/Library/Containers/com.tencent.xinWeChat/Data/Library/Application Support/com.tencent.xinWeChat"

if [ ! -d "$WECHAT_PATH" ]; then
    echo "❌ 未找到微信目录"
    echo "请确认："
    echo "1. 已安装 macOS 版微信"
    echo "2. 已在手机上打开过该小程序"
    exit 1
fi

echo "✓ 找到微信目录: $WECHAT_PATH"
echo ""

# 查找小程序目录
echo ">> 查找小程序 wx613cd6930dab2d0a..."
APP_DIRS=$(find "$WECHAT_PATH" -type d -name "*wx613cd6930dab2d0a*" 2>/dev/null)

if [ -z "$APP_DIRS" ]; then
    echo "❌ 未找到该小程序"
    echo "💡 请先在手机微信中打开该小程序，确保缓存存在"
    exit 1
fi

echo "✓ 找到小程序目录:"
echo "$APP_DIRS"
echo ""

# 查找 .wxapkg 文件
echo ">> 查找 .wxapkg 文件..."
WXAPKG_FILES=$(find "$WECHAT_PATH" -name "*.wxapkg" -path "*wx613cd6930dab2d0a*" 2>/dev/null)

if [ -z "$WXAPKG_FILES" ]; then
    echo "❌ 未找到 .wxapkg 文件"
    echo "💡 小程序可能未完全加载，请："
    echo "   1. 手机微信打开小程序"
    echo "   2. 浏览所有页面"
    echo "   3. 重新运行此脚本"
    exit 1
fi

echo "✓ 找到 .wxapkg 文件:"
echo "$WXAPKG_FILES"
echo ""

# 复制到桌面
OUT_DIR="$HOME/Desktop/wxapkg_extracted"
mkdir -p "$OUT_DIR"

echo ">> 复制文件到: $OUT_DIR"
while IFS= read -r file; do
    filename=$(basename "$file")
    cp "$file" "$OUT_DIR/$filename"
    echo "   ✓ $filename"
done <<< "$WXAPKG_FILES"

echo ""
echo "✅ 完成！文件已复制到:"
echo "   $OUT_DIR"
echo ""
echo "💡 下一步："
echo "   1. 安装反编译工具: git clone https://github.com/xuedingmiaojun/wxappUnpacker"
echo "   2. 运行反编译: node wuWxapkg.js $OUT_DIR/*.wxapkg"
