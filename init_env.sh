#!/usr/bin/env bash

ENV_NAME="gobi"

# 1) 检查 conda 命令是否可用
if ! command -v conda >/dev/null 2>&1; then
    echo "❌ conda 命令不存在。请先打开一个已初始化 conda 的终端，或检查 mambaforge 安装。"
    return 1 2>/dev/null || exit 1
fi

# 2) 如果环境不存在，就根据 environment.yml 创建
if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "🔧 未找到环境：$ENV_NAME，正在根据 environment.yml 创建..."
    conda env create -f environment.yml
else
    echo "✅ conda 环境 $ENV_NAME 已存在，跳过创建。"
fi

# 3) 激活环境
echo "🔄 正在激活 conda 环境：$ENV_NAME ..."
conda activate "$ENV_NAME"

echo "✅ conda 环境 $ENV_NAME 已就绪。"
