#!/bin/bash
# 微调与 PEFT 环境快速安装脚本

set -e  # 遇到错误立即退出

echo "=========================================="
echo "🔧 微调与 PEFT 环境安装脚本"
echo "=========================================="
echo ""

# 检测操作系统和芯片
OS_TYPE=$(uname -s)
ARCH=$(uname -m)

echo "📋 系统信息:"
echo "  操作系统: $OS_TYPE"
echo "  架构: $ARCH"
echo ""

# 检查 Python
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version)
    echo "✅ Python: $PYTHON_VERSION"
else
    echo "❌ Python 3 未安装，请先安装 Python 3.8+"
    exit 1
fi

# 询问安装方式
echo ""
echo "请选择安装方式:"
echo "  1) 使用 uv (推荐 - 快速且可靠)"
echo "  2) 使用 conda (适合已有 conda 环境)"
echo "  3) 使用 pip + venv (传统方式)"
read -p "请输入选项 [1/2/3]: " choice

case $choice in
    1)
        echo ""
        echo "📦 使用 uv 安装..."

        # 检查 uv
        if ! command -v uv &> /dev/null; then
            echo "📥 安装 uv..."
            pip install uv
        else
            echo "✅ uv 已安装"
        fi

        # 检查是否是 Intel Mac
        if [ "$OS_TYPE" = "Darwin" ] && [ "$ARCH" = "x86_64" ]; then
            echo ""
            echo "⚠️  检测到 Intel Mac，可能需要特殊处理 torch 版本"
            read -p "是否修改 pyproject.toml 中的 torch 版本为 2.2.2? [y/N]: " modify_torch

            if [ "$modify_torch" = "y" ] || [ "$modify_torch" = "Y" ]; then
                # 备份原文件
                cp pyproject.toml pyproject.toml.backup

                # 修改 torch 版本
                sed -i '' 's/torch = ".*"/torch = "==2.2.2"/' pyproject.toml
                echo "✅ 已修改 torch 版本"
            fi
        fi

        # 运行 uv sync
        echo ""
        echo "📥 安装依赖（这可能需要几分钟）..."
        uv sync

        echo ""
        echo "✅ 依赖安装完成！"
        echo ""
        echo "🎯 激活虚拟环境:"
        echo "   source .venv/bin/activate"
        ;;

    2)
        echo ""
        echo "📦 使用 conda 安装..."

        # 检查 conda
        if ! command -v conda &> /dev/null; then
            echo "❌ conda 未安装，请先安装 Anaconda 或 Miniconda"
            exit 1
        fi

        # 环境名称
        ENV_NAME="ai-engineer-finetuning-peft"

        # 检查环境是否存在
        if conda env list | grep -q "^$ENV_NAME "; then
            echo "⚠️  环境 $ENV_NAME 已存在"
            read -p "是否删除并重新创建? [y/N]: " recreate

            if [ "$recreate" = "y" ] || [ "$recreate" = "Y" ]; then
                echo "🗑️  删除旧环境..."
                conda env remove -n $ENV_NAME -y
            else
                echo "取消安装"
                exit 0
            fi
        fi

        # 创建环境
        echo "📥 创建 conda 环境 $ENV_NAME..."
        conda create --name $ENV_NAME python=3.11 -y

        # 激活环境并安装依赖
        echo "📥 安装依赖..."
        eval "$(conda shell.bash hook)"
        conda activate $ENV_NAME

        pip install uv
        uv pip compile pyproject.toml --output-file requirements.txt
        uv pip install -r requirements.txt

        echo ""
        echo "✅ 依赖安装完成！"
        echo ""
        echo "🎯 激活环境:"
        echo "   conda activate $ENV_NAME"
        ;;

    3)
        echo ""
        echo "📦 使用 pip + venv 安装..."

        VENV_DIR="venv"

        # 检查虚拟环境是否存在
        if [ -d "$VENV_DIR" ]; then
            echo "⚠️  虚拟环境已存在"
            read -p "是否删除并重新创建? [y/N]: " recreate

            if [ "$recreate" = "y" ] || [ "$recreate" = "Y" ]; then
                echo "🗑️  删除旧虚拟环境..."
                rm -rf $VENV_DIR
            else
                echo "使用现有虚拟环境"
            fi
        fi

        # 创建虚拟环境
        if [ ! -d "$VENV_DIR" ]; then
            echo "📥 创建虚拟环境..."
            python3 -m venv $VENV_DIR
        fi

        # 激活虚拟环境
        source $VENV_DIR/bin/activate

        # 升级 pip
        echo "📥 升级 pip..."
        pip install --upgrade pip

        # 安装依赖
        echo "📥 安装核心依赖..."

        # 根据系统和架构选择 torch 版本
        if [ "$OS_TYPE" = "Darwin" ]; then
            if [ "$ARCH" = "arm64" ]; then
                # Apple Silicon
                echo "  检测到 Apple Silicon，安装 torch for macOS"
                pip install torch torchvision torchaudio
            else
                # Intel Mac
                echo "  检测到 Intel Mac，安装 torch 2.2.2"
                pip install torch==2.2.2 torchvision torchaudio
            fi
        else
            # Linux
            echo "  检测到 Linux，安装 CUDA 版本 torch"
            pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118
        fi

        echo "📥 安装其他依赖..."
        pip install transformers accelerate
        pip install gradio fastapi uvicorn
        pip install ms-swift
        pip install pillow matplotlib tqdm pyyaml

        echo ""
        echo "✅ 依赖安装完成！"
        echo ""
        echo "🎯 激活虚拟环境:"
        echo "   source venv/bin/activate"
        ;;

    *)
        echo "❌ 无效选项"
        exit 1
        ;;
esac

# 验证安装
echo ""
echo "=========================================="
echo "🔍 验证安装..."
echo "=========================================="

# 根据选择激活对应环境进行验证
case $choice in
    1)
        ACTIVATE_CMD="source .venv/bin/activate"
        ;;
    2)
        ACTIVATE_CMD="conda activate ai-engineer-finetuning-peft"
        ;;
    3)
        ACTIVATE_CMD="source venv/bin/activate"
        ;;
esac

echo ""
echo "请在新终端运行以下命令激活环境并验证:"
echo ""
echo "  cd 06_finetuning_and_data_processing_and_routing_react_and_tools/01_finetuning_and_data_processing/01_finetuning_overview"
echo "  $ACTIVATE_CMD"
echo ""
echo "  # 验证 PyTorch"
echo "  python3 -c \"import torch; print('PyTorch:', torch.__version__)\""
echo ""
echo "  # 验证 Transformers"
echo "  python3 -c \"import transformers; print('Transformers:', transformers.__version__)\""
echo ""
echo "  # 验证 ms-swift"
echo "  python3 -c \"import swift; print('ms-swift installed')\""
echo ""
echo "  # 检查 CUDA (如果有 GPU)"
echo "  python3 -c \"import torch; print('CUDA available:', torch.cuda.is_available())\""
echo ""

echo "=========================================="
echo "✅ 安装完成！"
echo "=========================================="
echo ""
echo "📚 下一步:"
echo "  1. 激活环境: $ACTIVATE_CMD"
echo "  2. 阅读文档: cat 开始前必读.md"
echo "  3. 开始训练: ./quick_start_massive.sh"
echo ""
echo "祝你训练顺利！🚀"
