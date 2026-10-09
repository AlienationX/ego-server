#!/bin/bash

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(echo "$SCRIPT_DIR" | grep -o '^.*/ego-server/')"

# 每日凌晨1点执行一次，保存Bing每日壁纸，增量计算壁纸的特征向量并存储，增量预计算壁纸的TopN相似度

PYTHON="$PROJECT_ROOT/.venv/bin/python"
log_file="$PROJECT_ROOT/ego/logs/daily_tasks_$(date +%Y-%m-%d).log"

cd "$PROJECT_ROOT/ego"

# 保存Bing每日壁纸
$PYTHON -u manage.py save_bing_image >> "$log_file" 2>&1

# 增量计算壁纸的特征向量并存储
$PYTHON -u manage.py extract_features &>> $log_file

# 增量预计算壁纸的TopN相似度
$PYTHON -u manage.py calc_similarities_topN &>> $log_file

# 增量翻译壁纸的description和tags
$PYTHON -u manage.py translate_walls &>> $log_file

# 全量计算壁纸的趋势分数
$PYTHON -u manage.py calc_trends_score --force &>> $log_file
