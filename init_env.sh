#!/usr/bin/env bash

ENV_NAME="gobi"

if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    echo "Please run: source init_env.sh"
    exit 1
fi

# check conda
if ! command -v conda >/dev/null 2>&1; then
    echo "Error: conda not found. Please install Miniconda or Anaconda first."
    return 1 2>/dev/null || exit 1
fi

# if env not exist, then create
if ! conda env list | awk '{print $1}' | grep -qx "$ENV_NAME"; then
    echo "Creating conda environment '$ENV_NAME'..."
    conda env create -f environment_essential.yml -n "$ENV_NAME"
else
    echo "Conda environment '$ENV_NAME' already exists, skipping creation."
fi

echo "Activating environment '$ENV_NAME'..."
conda activate "$ENV_NAME"
