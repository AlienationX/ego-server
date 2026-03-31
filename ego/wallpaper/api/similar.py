import numpy as np
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet
from utils.feature_extractor import FeatureStorage

from ..models import Wall, WallFeatures
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import WallSerializer

# 使用FAISS（Facebook AI Similarity Search）加速检索，缺点：当数据库新增/删除/修改图片时，需要更新 FAISS 索引。
# 使用近似最近邻搜索（ANN）加速
# 使用向量数据库存储特征向量，提高检索效率（如Qdrant, Weaviate, Milvus）


class ApiModelView(RetrieveModelMixin, GenericViewSet):
    queryset = Wall.objects.select_related("wall_features").all()
    serializer_class = WallSerializer
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    def retrieve(self, request, *args, **kwargs):
        from datetime import datetime

        print(f"{datetime.now()} 1")
        query_wall = self.get_object()  # 获取单个对象
        feature_vector = FeatureStorage.blob_to_vector(
            query_wall.wall_features.feature_vector, query_wall.wall_features.feature_dim
        )
        print(f"{datetime.now()} 2")
        query_vec = np.array(feature_vector)
        print(f"{datetime.now()} 3")

        # 获取所有其他有特征的图片，预加载 Wall 数据
        all_images = (
            WallFeatures.objects.select_related("wall").exclude(wall_id=query_wall.id).filter(feature_vector__isnull=False)
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
        print(f"{datetime.now()} 6")

        data = [
            {
                "wall_id": wall.id,
                "picurl": wall.picurl,
                "description": wall.description,
                "classify": wall.classify_id,
                "tabs": wall.tabs,
                "score": wall.score,
                "is_locked": wall.is_locked,
                "similarity": round(float(sim), 4),
            }
            for wall, sim in top10
        ]

        return Response(data)

    @action(detail=True, methods=["get"])
    def precomputed(self, request, pk=None):
        """获取预计算的TopN相似度"""
        search_wall = self.serializer_class(self.get_object())
        search_wall.is_valid(raise_exception=True)
        return Response(search_wall.data)
