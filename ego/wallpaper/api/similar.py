import numpy as np
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from utils.feature_extractor import FeatureStorage

from ..models import Wall, WallFeatures, WallSimilarities
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import WallSerializer

# 使用FAISS（Facebook AI Similarity Search）加速检索，缺点：当数据库新增/删除/修改图片时，需要更新 FAISS 索引。
# 使用近似最近邻搜索（ANN）加速
# 使用向量数据库存储特征向量，提高检索效率（如Qdrant, Weaviate, Milvus）


class ApiModelView(RetrieveModelMixin, GenericViewSet):
    queryset = WallFeatures.objects.all()
    serializer_class = WallSerializer
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    def retrieve(self, request, *args, **kwargs):
        from datetime import datetime

        query_wall = self.get_object()  # 获取单个对象
        feature_vector = FeatureStorage.blob_to_vector(query_wall.feature_vector, query_wall.feature_dim)
        query_vec = np.array(feature_vector)
        print(f"{datetime.now()} 3")

        # 获取所有其他有特征的图片，预加载 Wall 数据
        # TODO 表数据量大查询慢，需要优化
        all_images = (
            WallFeatures.objects.select_related("wall").exclude(wall_id=query_wall.wall_id).filter(feature_vector__isnull=False)
        )
        print(f"{datetime.now()} 4")

        similarities = []
        for img in all_images:
            other_vec = np.array(FeatureStorage.blob_to_vector(img.feature_vector, img.feature_dim))
            # 余弦相似度（向量已归一化，直接用内积）
            sim = np.dot(query_vec, other_vec)
            # 欧氏距离 (越小越相似)
            # euclidean_dist = np.linalg.norm(query_vec - other_vec)
            similarities.append((img.wall, sim))
        print(f"{datetime.now()} 5")

        # 按相似度降序排序，取前10
        similarities.sort(key=lambda x: x[1], reverse=True)
        top10 = similarities[:10]

        data = [
            {
                "wall_id": wall.id,
                "picurl": wall.picurl,
                "description": wall.description,
                "classify_id": wall.classify_id,
                # "classify_name": wall.classify_name,
                "tabs": wall.tabs,
                "score": wall.score,
                "is_locked": wall.is_locked,
                "similarity": round(float(sim), 4),
            }
            for wall, sim in top10
        ]

        return Response(data)

    # 默认访问路径url_path = /api/similar/<wall_id>/precomputed/
    # 指定url_path = "top10", 访问路径为 /api/similar/<wall_id>/top10/
    @action(detail=True, methods=["get"])
    def precomputed(self, request, pk=None):
        """获取预计算的TopN相似度"""
        # 获取预计算的相似度
        similarities = WallSimilarities.objects.filter(source_wall_id=pk).order_by("-similarity")[:10]  # 只取前10个

        # 获取 target_wall_id 列表
        target_ids = [sim.target_wall_id for sim in similarities]

        # 批量获取 Wall 信息
        walls = Wall.objects.filter(id__in=target_ids)
        wall_map = {wall.id: wall for wall in walls}

        # 构建响应数据
        data = []
        for sim in similarities:
            wall = wall_map.get(sim.target_wall_id)
            if wall:
                data.append(
                    {
                        "wall_id": wall.id,
                        "picurl": wall.picurl,
                        "description": wall.description,
                        "classify_id": wall.classify_id,
                        "tabs": wall.tabs,
                        "score": wall.score,
                        "is_locked": wall.is_locked,
                        "similarity": round(float(sim.similarity), 4),
                    }
                )

        return Response(data)
