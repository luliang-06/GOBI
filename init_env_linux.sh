#!/usr/bin/env bash

LOGFILE="init_env.log"
echo "=== $(date) start init_env.sh ===" > "$LOGFILE"

# Initiate conda shell hook
eval "$(conda shell.bash hook)" >> "$LOGFILE" 2>&1 || {
  echo "ERROR: failed eval cond­a shell hook" >> "$LOGFILE"
  exit 1
}

# load conda env script
echo "info: conda command: $(which conda)" >> "$LOGFILE"
echo "info: conda version: $(conda --version)" >> "$LOGFILE"

# check environment.yml
if [[ ! -f "environment_linux.yml" ]]; then
  echo "ERROR: environment_linux.yml not “exist >> "$LOGFILE"
  exit 1
fi

# try create / update
ENV_NAME="gobi"

# check env exist 
if conda info --envs | grep -E "^${ENV_NAME}[[:space:]]" >/dev/null; then
  echo "✅ conda env ${ENV_NAME} already exist，skip creation >> "$LOGFILE"
else
  echo "🔧 creating conda env ${ENV_NAME} ..." >> "$LOGFILE"

  conda env create --name ${ENV_NAME} -f environment_linux.yml >> "$LOGFILE" 2>&1 || {
    echo "ERROR: conda env create failed" >> "$LOGFILE"
    exit 1
  }
  echo "✔ Conda env ${ENV_NAME} created >> "$LOGFILE"
fi

echo "=== $(date) script end ===" >> "$LOGFILE"
