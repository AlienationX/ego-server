# gunicorn server.wsgi:application -c gunicorn_conf.py -D

import multiprocessing
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

bind = "127.0.0.1:8080"

# ==================== 进程与线程（适配 2核2G） ====================
# 2核 CPU 建议配置 2 个 Worker，相比 3 个 Worker 可直降约 200MB+ 常驻内存
workers = 2
worker_class = "gthread"
# 每个 Worker 3 个线程，总并发处理能力为 6，兼顾 I/O 并发与内存稳定性
threads = 3

# ==================== 内存防泄漏机制（核心防崩项） ====================
# 单个 Worker 处理满 1000 个请求后平滑重启，主动释放 C 扩展和 Python 运行时内存碎片
max_requests = 1000
# 随机扰动 0~100 次，避免所有 Worker 在同一时刻同时重启造成服务瞬时无响应
max_requests_jitter = 100

# ==================== 超时与连接管理 ====================
timeout = 60          # 请求超时时间（防止长耗时请求拖死 worker 线程）
graceful_timeout = 30 # 平滑停止时的等待时间
keepalive = 5         # 保持与 Nginx 的长连接复用（秒）

forwarded_allow_ips = "127.0.0.1"  # 信任来自 Nginx 代理的 X-Forwarded-For 头

# ==================== 日志与输出 ====================
loglevel = "info"  # 生产环境建议设为 warning，减少低速云盘 IOPS 消耗
accesslog = f"{PROJECT_ROOT}/logs/access.log"
errorlog = f"{PROJECT_ROOT}/logs/error.log"
capture_output = True # 将 stdout/stderr 重定向到 errorlog

Path(accesslog).parent.mkdir(parents=True, exist_ok=True)
Path(errorlog).parent.mkdir(parents=True, exist_ok=True)
