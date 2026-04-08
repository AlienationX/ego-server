#!/bin/bash

# 每日凌晨1点执行一次，保存Bing每日壁纸，增量计算壁纸的特征向量并存储，增量预计算壁纸的TopN相似度

PYTHON=/app/ego-server/.venv/bin/python
log_file="/var/log/ego-server/daily_tasks_$(date +%Y-%m-%d).log"

cd /app/ego-server/ego

# 保存Bing每日壁纸
$PYTHON -u manage.py save_bing_image &>> $log_file

# 增量计算壁纸的特征向量并存储
$PYTHON -u manage.py extract_features &>> $log_file

# 增量预计算壁纸的TopN相似度
$PYTHON -u manage.py calc_similarities_topN &>> $log_file
