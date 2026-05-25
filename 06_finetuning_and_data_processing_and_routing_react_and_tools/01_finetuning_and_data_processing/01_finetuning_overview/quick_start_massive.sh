#!/bin/bash
# MASSIVE 中文意图分类模型微调 - 快速启动脚本

set -e  # 遇到错误立即退出

DATA_DIR="../02_massive_dataset_processing/amazon_massive_intent_zh_cn"
CONVERTER="../02_massive_dataset_processing/convert_massive_to_training_format.py"
SERVER_SCRIPT="../04_local_finetuning_platform/local_ft/server.py"

echo "=========================================="
echo "🚀 MASSIVE 中文意图分类模型微调"
echo "=========================================="
echo ""

# 检查数据是否已转换
if [ ! -f "$DATA_DIR/train_converted.jsonl" ]; then
    echo "📦 步骤 1: 转换数据格式..."
    python3 "$CONVERTER" \
        --input "$DATA_DIR/train.jsonl" \
        --output "$DATA_DIR/train_converted.jsonl" \
        --format instruction

    python3 "$CONVERTER" \
        --input "$DATA_DIR/validation.jsonl" \
        --output "$DATA_DIR/validation_converted.jsonl" \
        --format instruction

    python3 "$CONVERTER" \
        --input "$DATA_DIR/test.jsonl" \
        --output "$DATA_DIR/test_converted.jsonl" \
        --format instruction

    echo "✅ 数据转换完成！"
    echo ""
else
    echo "✅ 数据已转换，跳过此步骤"
    echo ""
fi

# 询问用户选择微调方式
echo "请选择微调方式:"
echo "  1) 使用 Web 界面（推荐新手）"
echo "  2) 使用命令行（推荐高级用户）"
read -p "请输入选项 [1/2]: " choice

if [ "$choice" == "1" ]; then
    echo ""
    echo "🌐 启动 Web 界面..."
    echo "访问: http://localhost:7866"
    echo ""
    echo "操作步骤:"
    echo "  1. 进入'数据上传'页面，上传 train_converted.jsonl"
    echo "  2. 进入'模型微调'页面，配置参数并开始训练"
    echo "  3. 训练完成后，进入'权重合并'页面合并模型"
    echo ""
    python3 "$SERVER_SCRIPT"

elif [ "$choice" == "2" ]; then
    echo ""
    echo "⚙️  配置微调参数..."

    # 默认参数
    MODEL="Qwen/Qwen2.5-1.5B-Instruct"
    EPOCHS=3
    BATCH_SIZE=8
    LR=1e-4
    LORA_RANK=8

    read -p "基础模型 [$MODEL]: " input_model
    MODEL=${input_model:-$MODEL}

    read -p "训练轮数 [$EPOCHS]: " input_epochs
    EPOCHS=${input_epochs:-$EPOCHS}

    read -p "批次大小 [$BATCH_SIZE]: " input_batch
    BATCH_SIZE=${input_batch:-$BATCH_SIZE}

    read -p "学习率 [$LR]: " input_lr
    LR=${input_lr:-$LR}

    read -p "LoRA Rank [$LORA_RANK]: " input_rank
    LORA_RANK=${input_rank:-$LORA_RANK}

    # 生成输出目录名
    TIMESTAMP=$(date +%Y%m%d-%H%M%S)
    OUTPUT_DIR="output/massive_zh_${TIMESTAMP}"

    echo ""
    echo "📊 微调配置:"
    echo "  模型: $MODEL"
    echo "  轮数: $EPOCHS"
    echo "  批次: $BATCH_SIZE"
    echo "  学习率: $LR"
    echo "  LoRA Rank: $LORA_RANK"
    echo "  输出: $OUTPUT_DIR"
    echo ""

    read -p "确认开始训练? [y/N]: " confirm
    if [ "$confirm" != "y" ] && [ "$confirm" != "Y" ]; then
        echo "取消训练"
        exit 0
    fi

    echo ""
    echo "🚀 开始训练..."
    echo ""

    # 构建训练命令
    swift sft \
        --model "$MODEL" \
        --train_type lora \
        --dataset "$DATA_DIR/train_converted.jsonl" \
        --num_train_epochs $EPOCHS \
        --per_device_train_batch_size $BATCH_SIZE \
        --learning_rate $LR \
        --lora_rank $LORA_RANK \
        --lora_alpha $(($LORA_RANK * 2)) \
        --target_modules q_proj k_proj v_proj o_proj \
        --gradient_accumulation_steps 4 \
        --eval_steps 100 \
        --save_steps 500 \
        --save_total_limit 2 \
        --logging_steps 10 \
        --max_length 512 \
        --warmup_ratio 0.1 \
        --output_dir "$OUTPUT_DIR"

    if [ $? -eq 0 ]; then
        echo ""
        echo "✅ 训练完成！"
        echo ""
        echo "📁 输出目录: $OUTPUT_DIR"
        echo ""
        echo "🔗 下一步:"
        echo "  1. 合并权重: swift export --ckpt_dir $OUTPUT_DIR/checkpoint-xxx --merge_lora true"
        echo "  2. 测试模型: python evaluate_model.py --model $OUTPUT_DIR"
        echo ""
    else
        echo ""
        echo "❌ 训练失败！请检查日志"
        exit 1
    fi

else
    echo "无效选项"
    exit 1
fi
