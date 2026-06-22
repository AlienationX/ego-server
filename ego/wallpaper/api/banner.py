import random

from django.core.cache import cache
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
        cache_data = cache.get(cache_key)
        if cache_data:
            return Response(cache_data)

        # 一次查询获取所有壁纸，包含分类信息，加载到内存中
        walls = Wall.objects.select_related("classify").filter(is_active=True, classify__enable=True).all()

        # 每个 .filter(...).first() 都是一次独立的数据库查询，总共触发了 5 次 SQL。如果数据量不大，可以一次全量加载到内存再过滤
        bing_wall = walls.filter(classify_id=30).order_by("-created_at").first()

        pokemon_wall = walls.filter(classify_id=62).order_by("?").first()

        snoopy_ids = [1899, 1894, 1895, 1896, 1900, 1902, 1897, 1901, 1898]
        snoopy_id = random.choice(snoopy_ids)
        snoopy_wall = walls.filter(id=snoopy_id).first()

        random_wall = walls.order_by("?").first()

        girl_wall = walls.filter(id=1056).first()

        data = []

        if bing_wall:
            data.append(
                {
                    "id": 1,
                    "url": "/pages/app/classlist?id=30&name=必应每日壁纸&name_en=Bing Daily Wallpaper",
                    "sort": 1,
                    "picurl": bing_wall.picurl,
                    "description": bing_wall.description,
                    "description_en": bing_wall.description_en,
                    "target": "self",
                    "appid": None,
                    "wall": None,
                }
            )

        if pokemon_wall:
            data.append(
                {
                    "id": 2,
                    "url": "/pages/app/classlist?id=62&name=宝可梦睡眠&name_en=Pokemon Sleep",
                    "sort": 2,
                    "picurl": pokemon_wall.picurl,
                    "description": pokemon_wall.description,
                    "description_en": pokemon_wall.description_en,
                    "target": "self",
                    "appid": None,
                    "wall": None,
                }
            )

        if snoopy_wall:
            data.append(
                {
                    "id": 3,
                    "url": "/pages/app/search?keyword=snoopy",
                    "sort": 3,
                    "picurl": snoopy_wall.picurl,
                    "description": snoopy_wall.description,
                    "description_en": snoopy_wall.description_en,
                    "target": "self",
                    "appid": None,
                    "wall": None,
                }
            )

        if random_wall:
            data.append(
                {
                    "id": 4,
                    "url": f"/pages/app/preview?id={random_wall.id}&mode=recommend",
                    "sort": 4,
                    "picurl": random_wall.picurl,
                    "description": random_wall.description,
                    "description_en": random_wall.description_en,
                    "target": "self",
                    "appid": None,
                    # subjects字段无法序列化，需要排除
                    "wall": model_to_dict(
                        random_wall, exclude=["subjects", "md5_hash", "content_hash", "created_at", "updated_at", "remark"]
                    )
                    | {"classify_id": random_wall.classify.id, "classify_name": random_wall.classify.name, "classify_name_en": random_wall.classify.name_en},
                }
            )

        if girl_wall:
            data.append(
                {
                    "id": 5,
                    "url": f"/pages/app/preview?id={girl_wall.id}&mode=recommend",
                    "sort": 5,
                    "picurl": girl_wall.picurl,
                    "description": girl_wall.description,
                    "description_en": girl_wall.description_en,
                    "target": "self",
                    "appid": None,
                    # 字典合并，包含壁纸信息和分类信息
                    "wall": model_to_dict(
                        girl_wall, exclude=["subjects", "md5_hash", "content_hash", "created_at", "updated_at", "remark"]
                    )
                    | {"classify_id": girl_wall.classify.id, "classify_name": girl_wall.classify.name, "classify_name_en": girl_wall.classify.name_en},
                }
            )

        # 最后增加小程序的跳转
        data.append(
            {
                "id": 6,
                "url": None,
                "sort": 6,
                "picurl": "banner/to_wechat.jpg",
                "description": "微信小程序",
                "description_en": "WeChat Mini Program",
                "target": "miniProgram",
                "appid": "wx74c392f8525b9268",
                "wall": None,
            }
        )

        # 增加缓存，缓存时间为 10 分钟
        cache.set(cache_key, data, timeout=10 * 60)
        return Response(data)
