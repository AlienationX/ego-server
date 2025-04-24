from django.urls import path, include

from rest_framework import routers

# from drf_yasg.views import get_schema_view
# from drf_yasg import openapi
# from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView, SpectacularRedocView

from pathlib import Path
from importlib import import_module

from . import views


# 设置API文档的schema视图
# schema_view = get_schema_view(
#     openapi.Info(
#         title="Wallpaper API",
#         default_version='v1',
#         description="Test description",
#         terms_of_service="https://www.google.com/policies/terms/",
#         contact=openapi.Contact(email="contact@myapi.com"),
#         license=openapi.License(name="BSD License"),
#     ),
#     public=True,
# )

# 静态注册路由，不灵活
router = routers.DefaultRouter()
# router.register(r'wall', views.WallView, basename="wall")
# router.register(r'classify', views.ClassifyView, basename="classify")
# router.register(r'banner', views.BannerView, basename="banner")
# router.register(r'notice', views.NoticeView, basename="notice")


def router_register(p: Path, folder="api"):
    name = p.stem
    file = import_module(f'.{folder}.{name}', package=__package__)
    module = getattr(file, 'ApiModelView', None)
    # print(name, file, module)
    if module:
        router.register(name, module, basename=name)
        # print(f"=> router register {__package__}.{folder}.{name}")


# 动态注册路由
apis_path = Path(__file__).resolve().parent.joinpath("api")
for p in apis_path.iterdir():
    # 进行文件名等逻辑判断，过滤不需要注册的路由
    if not p.is_file():
        continue
    router_register(p)


app_name = 'wallpaper'
urlpatterns = [
    path('api/', include(router.urls)),

    # drf-yasg
    # path('yasg-swagger/', schema_view.with_ui('swagger', cache_timeout=0), name='schema-swagger-ui'),
    # path('yasg-redoc/', schema_view.with_ui('redoc', cache_timeout=0), name='schema-redoc'),

    # 在这里配置无效，只能在项目根目录的url中配置？
    # # drf-spectacular
    # path('schema/', SpectacularAPIView.as_view(), name='schema'),
    # # 为 Swagger UI 添加路径
    # path('spe-swagger/', SpectacularSwaggerView.as_view(url_name='schema'), name='spe-swagger'),
    # path('spe-redoc/', SpectacularRedocView.as_view(url_name='schema'), name='redoc'),
]
