#!/bin/bash

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(echo "$SCRIPT_DIR" | grep -o '^.*/ego-server/')"

if pgrep -f "ego-server" > /dev/null; then
    echo "ego-server is running, will stop it..."
    pgrep -f "ego-server" | xargs kill
    # 谨慎使用 kill -9：SIGKILL信号（-9）强制进程立即终止，不给进程任何清理资源的机会
    echo "ego-server is stopped"
fi


# source ${PROJECT_ROOT}/.venv/bin/activate
cd ${PROJECT_ROOT}/ego/
${PROJECT_ROOT}/.venv/bin/gunicorn server.wsgi:application -c gunicorn_conf.py -D

echo "ego-server is started"