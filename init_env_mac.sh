#!/usr/bin/env bash
set -e

# 1) 确保 conda 已初始化
if [[ -n "$CONDA_EXE" ]]; then
    source "$(conda info --base)/etc/profile.d/conda.sh"
else
    # 通常安装在 ~/miniforge3 或 ~/mambaforge
    source "$HOME/miniforge3/etc/profile.d/conda.sh" 2>/dev/null || \
    source "$HOME/mambaforge/etc/profile.d/conda.sh"
fi

# 2) 如果环境不存在，就根据 environment.yml 创建
if ! conda info --envs | grep -q "^gobi "; then
    echo "🔧 创建 conda 环境 gobi..."
    conda env create -f environment.yml
else
    echo "✅ conda 环境 gobi 已存在，跳过创建。"
fi

# 3) 激活环境
conda activate gobi

echo "✅ conda 环境 gobi 已就绪。"
