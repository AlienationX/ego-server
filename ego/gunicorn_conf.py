# gunicorn server.wsgi:application -c gunicorn_conf.py -D

import multiprocessing
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

bind = "127.0.0.1:8080"
# workers = multiprocessing.cpu_count() * 2 + 1
workers = 3
worker_class = "gthread"  # 或 "gevent"
threads = 4
timeout = 120
accesslog = f"{PROJECT_ROOT}/logs/access.log"
errorlog = f"{PROJECT_ROOT}/logs/error.log"
