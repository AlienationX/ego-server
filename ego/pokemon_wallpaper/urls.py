from django.urls import path
from django.views.static import serve
from django.conf import settings

from pathlib import Path
from . import views

app_name = 'pokemon_wallpaper'
urlpatterns = [
    # 手动映射django/static的统一静态文件到应用的路径上
    # http://127.0.0.1:8000/static/pokemon_wallpaper/images/banner1.jpg  默认地址
    # http://127.0.0.1:8000/pokemon_wallpaper/static/images/banner1.jpg  映射地址
    path(
        'static/images/<path:path>',  # 自定义 URL 路径
        serve,
        {'document_root': Path(settings.BASE_DIR).joinpath('pokemon_wallpaper/static/pokemon_wallpaper/images')}
    ),

    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),

    path("index/", views.index, name="index"),
]

# from . import views

# urlpatterns = [
#     # ex: /polls/
#     # path('', views.IndexView.as_view(), name='index'),
#     # # ex: /polls/5/
#     # path('<int:pk>/', views.DetailView.as_view(), name='detail'),
#     # # ex: /polls/5/results/
#     # path('<int:pk>/results/', views.ResultsView.as_view(), name='results'),
#     # # ex: /polls/5/vote/
#     # path('<int:question_id>/vote/', views.vote, name='vote'),
# ]