import random

from django.forms.models import model_to_dict
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Banner, Wall
from ..renderers import CustomJSONRenderer
from ..serializers import BannerSerializer


class ApiModelView(ListModelMixin, CreateModelMixin, GenericViewSet):
    queryset = Banner.objects.all()
    serializer_class = BannerSerializer
    renderer_classes = [CustomJSONRenderer]

    def get_queryset(self):
        # 自定义结果集
        # 获取enable=True的数据并按 'created_at' 字段倒序排序，返回前 4 个滑动图
        return self.queryset.filter(enable=True).order_by("-created_at")[:4]

    def list(self, request, *args, **kwargs):
        # 读取缓存数据
        cache_key = "banner_list"
        cache_data = self.cache.get(cache_key)
        if cache_data:
            return Response(cache_data)

        # 一次查询获取所有壁纸，包含分类信息，加载到内存中
        walls = Wall.objects.select_related("classify").filter(is_active=True, classify__enable=True).all()

        bing_wall = walls.filter(classify_id=30).order_by("-created_at").first()

        pokemon_wall = walls.filter(classify_id=62).order_by("?").first()

        snoopy_ids = [1899, 1894, 1895, 1896, 1900, 1902, 1897, 1901, 1898]
        snoopy_id = random.choice(snoopy_ids)
        snoopy_wall = walls.filter(id=snoopy_id).first()

        random_wall = walls.filter(is_active=True).order_by("?").first()

        girl_wall = walls.filter(id=1056).first()

        # "picurl": str(bing_wall.picurl).replace(".jpg", "_small.webp"),
        data = [
            {
                "id": 1,
                "url": "/pages/app/classlist?id=30&name=必应每日壁纸",
                "sort": 1,
                "picurl": bing_wall.picurl,
                "description": bing_wall.description,
                "target": "self",
                "appid": None,
                "wall": None,
            },
            {
                "id": 2,
                "url": "/pages/app/classlist?id=62&name=宝可梦睡眠",
                "sort": 2,
                "picurl": pokemon_wall.picurl,
                "description": pokemon_wall.description,
                "target": "self",
                "appid": None,
                "wall": None,
            },
            {
                "id": 3,
                "url": "/pages/app/search/?keyword=snoopy",
                "sort": 5,
                "picurl": snoopy_wall.picurl,
                "description": snoopy_wall.description,
                "target": "miniProgram",
                "appid": "wxbd89d0ba67f6b6a4",
                "wall": None,
            },
            {
                "id": 4,
                "url": f"/pages/app/preview?id={random_wall.id}&mode=recommend",
                "sort": 4,
                "picurl": random_wall.picurl,
                "description": random_wall.description,
                "target": "self",
                "appid": None,
                "wall": model_to_dict(random_wall)
                | {"classify_id": random_wall.classify.id, "classify_name": random_wall.classify.name},
            },
            {
                "id": 5,
                "url": f"/pages/app/preview?id={girl_wall.id}&mode=recommend",
                "sort": 4,
                "picurl": girl_wall.picurl,
                "description": girl_wall.description,
                "target": "self",
                "appid": None,
                # 字典合并，包含壁纸信息和分类信息
                "wall": model_to_dict(girl_wall)
                | {"classify_id": girl_wall.classify.id, "classify_name": girl_wall.classify.name},
            },
        ]

        # 增加缓存，缓存时间为 10 分钟
        self.cache.set(cache_key, data, timeout=60 * 10)
        return Response(data)
