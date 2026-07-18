import logging
import random
from collections import defaultdict
from datetime import datetime

from django.core.cache import cache
from django.db.models import F, Q
from django.forms.models import model_to_dict
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Wall
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(ListModelMixin, CreateModelMixin, GenericViewSet):
    queryset = Wall.objects.select_related("classify").all()
    serializer_class = WallSerializer
    permission_classes = [HasAccessKey]
    pagination_class = CustomPageNumberPagination  # 使用自定义分页类
    renderer_classes = [CustomJSONRenderer]  # 使用自定义渲染器，额外统一增加code和message字段。默认是JSONRenderer

    def get_queryset(self):
        # 获取所有数据，且classify.enable为True的数据
        queryset = Wall.objects.select_related("classify").filter(is_active=True)
        # 获取查询参数中的 classify_id ，如果参数存在，则过滤查询集
        classify_id = self.request.query_params.get("classify_id")
        if classify_id:
            queryset = queryset.filter(classify_id=classify_id)

        # 获取查询参数中的 subject_id，如果参数存在，则过滤查询集
        subject_id = self.request.query_params.get("subject_id")
        if subject_id:
            queryset = queryset.filter(subjects__id=subject_id)

        # 获取查询参数中的 classify_enable
        classify_enable = self.request.query_params.get("classify_enable", "true").lower()
        if classify_enable != "false":
            queryset = queryset.filter(classify__enable=True)

        # 返回最终的查询集
        return queryset

    def _apply_sort_order(self, queryset):
        """对queryset应用非随机排序"""
        sortord = self.request.query_params.get("sortord")
        if sortord == "score":
            return queryset.order_by("-score", "-updated_at", "-id")
        elif sortord == "date_asc":
            return queryset.order_by("updated_at", "-id")
        else:  # date_desc 或默认
            return queryset.order_by("-updated_at", "-id")

    def _get_random_cached_data(self, queryset, keyword=None):
        """随机排序使用缓存策略，避免分页出现重复数据"""
        classify_id = self.request.query_params.get("classify_id", "0")
        cache_key = f"walls_rand_{keyword or 'blank'}_{classify_id}"
        data = cache.get_or_set(
            cache_key,
            lambda: list(
                queryset.annotate(classify_name=F("classify__name"), classify_name_en=F("classify__name_en"))
                .order_by("?")
                .values()
            ),
            timeout=10 * 60,
        )
        return data

    def list(self, request, *args, **kwargs):
        """重写list方法，非随机排序直接使用数据库分页，避免全量数据加载到内存"""
        queryset = self.get_queryset()
        sortord = request.query_params.get("sortord")

        if sortord == "random":
            # 随机排序需要缓存完整列表，否则分页会出现重复数据
            data = self._get_random_cached_data(queryset)
            page = self.paginate_queryset(data)
            if page is not None:
                return self.get_paginated_response(page)
            return Response(data)

        # 非随机排序：直接利用数据库排序和分页，不加载全量数据到内存
        queryset = self._apply_sort_order(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(queryset, many=True).data)

    def create(self, request, *args, **kwargs):
        """更新壁纸相关信息，如名称、描述、分类等。使用字段白名单防止越权修改"""
        user = request.user
        if not user.is_authenticated or not user.is_staff:
            return Response({"error": "您没有权限修改壁纸信息"}, status=status.HTTP_403_FORBIDDEN)

        try:
            data = request.data.copy()
            wall_obj = Wall.objects.filter(id=data.get("id")).first()
            if not wall_obj:
                return Response({"error": "壁纸不存在"}, status=status.HTTP_404_NOT_FOUND)

            data.pop("id", None)

            # 白名单过滤，防止恶意修改 views/downloads 等计数字段
            # 允许通过 create 接口更新的字段白名单
            # ALLOWED_UPDATE_FIELDS = {"description", "description_en", "tags", "tags_en", "classify_id", "remark", "score"}
            # update_data = {k: v for k, v in data.items() if k in ALLOWED_UPDATE_FIELDS}
            # if not update_data:
            #     return Response({"error": "没有可更新的字段"}, status=status.HTTP_400_BAD_REQUEST)

            update_data = data
            for attr, value in update_data.items():
                setattr(wall_obj, attr, value)
            wall_obj.save(update_fields=list(update_data.keys()))
            return Response(model_to_dict(wall_obj))
        except Exception as e:
            logger.error(e, exc_info=True)
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    @action(detail=False, methods=["get"])
    def random_daily(self, request):
        """每日随机推荐，使用 random.sample 替代 order_by('?') 避免全表扫描"""
        # detail=False 表示这个动作是针对所有对象的

        cache_key = f"walls_rand_daily_{datetime.today().strftime('%Y%m%d')}"
        # data = cache.get(cache_key)
        # if data is not None:
        #     return Response(data)

        queryset = self.get_queryset()

        # 先取 ID 列表（轻量查询），再随机选取，避免 order_by('?') 的全表随机排序
        id_list = list(queryset.values_list("id", flat=True))
        if not id_list:
            return Response([])

        sample_ids = random.sample(id_list, min(12, len(id_list)))
        random_queryset = queryset.filter(id__in=sample_ids)

        # 缓存序列化后的数据，避免直接缓存 QuerySet
        serializer = self.get_serializer(random_queryset, many=True)
        data = serializer.data
        cache.set(cache_key, data, timeout=10 * 60)  # 缓存10分钟
        return Response(data)

    @action(detail=False, methods=["get"])
    def random_recommend(self, request):
        """随机推荐，按分类分组。一次性查询所有数据后 Python 侧分组，消除 N+1 查询"""
        cache_key = f"walls_rand_recommend_{datetime.today().strftime('%Y%m%d')}"
        data = cache.get(cache_key)
        if data is not None:
            return Response(data)

        classify_ids = self.request.query_params.get("classify_ids", "")
        classify_ids = [cid.strip() for cid in classify_ids.split(",") if cid.strip()]
        if not classify_ids:
            return Response([])

        # 获取所有的对象，且classify.enable为True的数据
        queryset = self.get_queryset().filter(classify_id__in=classify_ids)

        # 一次性查询所有相关数据，按 classify 分组，避免循环内多次查询
        walls_by_classify = defaultdict(list)
        for wall in queryset.select_related("classify"):
            walls_by_classify[wall.classify_id].append(wall)

        data = []
        for classify_id in classify_ids:
            cid = int(classify_id)
            walls = walls_by_classify.get(cid, [])
            if not walls:
                continue
            sampled = random.sample(walls, min(12, len(walls)))
            first_wall = sampled[0]
            data.append(
                {
                    "id": first_wall.classify.id,
                    "name": first_wall.classify.name,
                    "name_en": first_wall.classify.name_en,
                    "data": self.get_serializer(sampled, many=True).data,
                }
            )

        cache.set(cache_key, data, timeout=10 * 60)  # 缓存10分钟
        return Response(data)

    @action(detail=False, methods=["get"])
    def search(self, request):
        """搜索壁纸，非随机排序直接使用数据库分页"""

        keyword = self.request.query_params.get("keyword")
        if not keyword:
            # 如果kw为空则返回空结果
            return Response([])

        # 使用 Q 对象进行过滤
        # models.XX.objects.filter( Q(id=10) )
        # models.XX.objects.filter( Q(id=10)&Q(age=19) )
        # models.XX.objects.filter( Q(id=10)|Q(age=19) )
        # models.XX.objects.filter( Q(id__gt=10)|Q(age__lte=19) )
        # models.XX.objects.filter( Q( Q(id__gt=10)|Q(age__lte=19) ) & Q(name=19))

        # 以年龄为例
        # res = models.User.objects.filter(age__gt=35)
        # 1、年龄大于35的：age__gt=35
        # 2、年龄小于35的：age__lt=35
        # 3、年龄大于等于35的：age__gte=35
        # 4、年龄小于等于35的：age__lte=35
        # 5、age__in=[1,3,5]   # age=1 or age=3 or age=5   （in走索引、not in不在索引）
        # 6、age__range=[18,40] # where age between 18 and 40
        # 7、age__contains="s" # age like %s%  包含s的
        # 8、age__icontains="s"  #忽略大小写
        # 9、age__startswith= "m" #以m开头的 age like m%
        # 10、age__endswith= "m" #以m结尾的 age like %n
        # 11、create_time__year="2021" #查出某一年的
        # 12、create_time__mouth="10" #查出某一月的
        # 13、create_time__day="17" #查出每个月17号的

        if keyword.startswith("#") and keyword[1:].isdigit():
            # 如果kw以#开头且为数字，则按ID查询
            wall_id = int(keyword[1:])
            queryset = self.get_queryset().filter(id=wall_id)
        else:
            # 进行过滤，中英文 description 字段包含kw关键字，或者中英文 tags 字段包含kw关键字
            queryset = self.get_queryset().filter(
                Q(description__icontains=keyword)
                | Q(description_en__icontains=keyword)
                | Q(tags__icontains=keyword)
                | Q(tags_en__icontains=keyword)
            )
        sortord = request.query_params.get("sortord")

        if sortord == "random":
            data = self._get_random_cached_data(queryset, keyword=keyword)
            page = self.paginate_queryset(data)
            if page is not None:
                return self.get_paginated_response(page)
            return Response(data)

        # 非随机排序：直接利用数据库排序和分页
        queryset = self._apply_sort_order(queryset)
        page = self.paginate_queryset(queryset)
        if page is not None:
            return self.get_paginated_response(self.get_serializer(page, many=True).data)
        return Response(self.get_serializer(queryset, many=True).data)

    @action(detail=False, methods=["get"])
    def top(self, request):
        """获取排行榜数据，带缓存"""
        sort_type = self.request.query_params.get("type")
        try:
            n = int(self.request.query_params.get("n", "10"))
        except (ValueError, TypeError):
            n = 10
        if sort_type not in ["views", "downloads"]:
            return Response([])
        n = max(1, min(n, 30))

        cache_key = f"walls_top_{sort_type}_{n}"
        data = cache.get(cache_key)
        if data is None:
            queryset = self.get_queryset().order_by(f"-{sort_type}")[:n]
            data = self.get_serializer(queryset, many=True).data
            cache.set(cache_key, data, timeout=5 * 60)  # 缓存5分钟
        return Response(data)

    # detail=True时，表示这个动作是针对单个对象。url会自动增加pk，例如wall/<pk>/increment_views/
    # pk参数会自动传入increment_views和increment_downloads方法，必须有
    @action(detail=True, methods=["post"])
    def increment_views(self, request, pk=None):
        instance = self.get_object()  # 获取单个对象
        instance.views = F("views") + 1  # 使用 F() 避免竞争条件
        instance.save(update_fields=["views"])
        instance.refresh_from_db(fields=["views"])  # 刷新实例字段值
        return Response({"id": instance.id, "views": instance.views})

    @action(detail=True, methods=["post"])
    def increment_downloads(self, request, pk=None):
        instance = self.get_object()
        instance.downloads = F("downloads") + 1
        instance.save(update_fields=["downloads"])
        instance.refresh_from_db(fields=["downloads"])
        return Response({"id": instance.id, "downloads": instance.downloads})
