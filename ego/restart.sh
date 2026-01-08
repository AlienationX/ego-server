#!/bin/bash

if pgrep -f "ego-server" > /dev/null; then
    echo "ego-server is running"
    pgrep -f "ego-server" | xargs kill
    # 谨慎使用 kill -9：SIGKILL信号（-9）强制进程立即终止，不给进程任何清理资源的机会
fi


# source /app/ego-server/.venv/bin/activate
cd /app/ego-server/ego/
/app/ego-server/.venv/bin/gunicorn server.wsgi:application -c gunicorn_conf.py -D