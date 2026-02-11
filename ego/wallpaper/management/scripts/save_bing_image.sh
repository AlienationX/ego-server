#!/bin/bash

cd /app/ego-server/ego && 
/app/ego-server/.venv/bin/python -u manage.py save_bing_image &>> /var/log/ego-server/save_bing_image_$(date +%Y-%m-%d).log