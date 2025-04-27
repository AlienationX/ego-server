
# Overview

```shell

# 创建虚拟环境
mkdir ego_project
cd ego_project
python -m venv .venv

# 安装django
pip install django
python -m django --version

# 创建项目
mkdir ego
django-admin stratporject server ego
cd ego
python manage.py runserver

# 初始化数据库，访问admin管理页面
python manage.py migrate
# 创建管理员用户
python manage.py createsuperuser

# 创建应用
python manage.py startapp pokemon_library
python manage.py startapp pokemon_wallpaper

pip install djangorestframework

# 解决跨域问题
pip install django-cors-headers

# jwt用户认证(jwt库已不再维护，推荐使用simplejwt)
pip install djangorestframework-simplejwt

# 敏感信息使用环境变量管理
pip install python-decouple

# 中小型项目静态文件服务器，中间件
pip install whitenoise
```

```shell
pip install django djangorestframework django-cors-headers djangorestframework-simplejwt python-decouple requests pymysql
```

> debug=False，生产环境需执行生成static目录 python manage.py collectstatic
