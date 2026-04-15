from datetime import datetime

import numpy as np
from django.core.management.base import BaseCommand
from loguru import logger
from tqdm import tqdm
from utils.feature_extractor import FeatureStorage
from wallpaper.models import WallFeatures, WallSimilarities

# python manage.py calc_similarities_topN --wall-id 123


class Command(BaseCommand):
    help = "预计算壁纸的TopN相似度"

    def add_arguments(self, parser):
        parser.add_argument("--wall-id", type=int, help="壁纸ID")
        parser.add_argument("--topN", type=int, default=12, help="TopN相似度")
        parser.add_argument("--force", action="store_true", help="强制重新计算所有壁纸")  # 布尔值，还有store_false

    def handle(self, *args, **options):
        wall_id = options.get("wall_id")
        topN = options.get("topN")
        force = options.get("force", False)

        start_time = datetime.now()

        # 1.缓存数据, 减少数据库查询, 后续计算时直接从缓存中获取。
        # 缓存所有壁纸的特征向量. key为壁纸ID, value为特征向量
        logger.info(f"开始计算壁纸的 Top{topN} 相似度")
        all_features = WallFeatures.objects.filter(feature_vector__isnull=False)
        all_features_list = list(all_features)
        feature_vectors = {
            f.wall_id: np.array(FeatureStorage.blob_to_vector(f.feature_vector, f.feature_dim)) for f in all_features_list
        }

        # 缓存所有壁纸的相似度记录, 用于后续更新已计算过的壁纸的TopN相似度记录. key为source_wall_id, value为最小相似度
        similarities_data = list(WallSimilarities.objects.all())
        min_sim_dict = {}
        for row in similarities_data:
            k = row.source_wall_id
            v = row.similarity
            if k not in min_sim_dict:
                min_sim_dict[k] = v
            else:
                min_sim_dict[k] = min(min_sim_dict[k], v)

        # 2.参数处理，取得待计算的壁纸ID集合
        if wall_id:
            # 计算指定壁纸的 TopN 相似度
            src_vecs = {wall_id: feature_vectors.get(wall_id)}
        elif not force:
            # 计算所有壁纸的TopN相似度,除了已计算过的壁纸
            # src_vecs = all_features.exclude(
            #     数据库的not in 操作, 会自动排除所有已计算过的壁纸
            #     wall_id__in=WallSimilarities.objects.all().values_list("source_wall_id", flat=True)
            # )
            src_vecs = {k: v for k, v in feature_vectors.items() if k not in min_sim_dict}
        else:
            # 强制重新计算所有壁纸的TopN相似度
            src_vecs = feature_vectors.copy()

        if not src_vecs:
            logger.warning("没有找到需要计算的壁纸特征向量")
            return

        # 3.计算相似度
        logger.info(f"共 {len(src_vecs)} 张 source 壁纸")
        all_similarities_data = []
        for src_id, src_vec in tqdm(src_vecs.items(), desc=f"{datetime.now()} 正在计算相似度"):
            # 去除和自己计算相似度
            tgt_features = {k: v for k, v in feature_vectors.items() if k != src_id}

            create_similarities = []
            update_similarities = []
            for tgt_id, tgt_vec in tgt_features.items():
                # 余弦相似度（向量已归一化，直接用内积）。
                sim = np.dot(src_vec, tgt_vec)
                create_similarities.append((src_id, tgt_id, sim))

                # step1: 检查已有图片的相似度列表，新增图片是否能够进入它们的TopN。如果相似度高于原有列表的第N名，则插入，并最后一起删除多余的相似度
                if tgt_id in min_sim_dict and sim > min_sim_dict[tgt_id]:
                    update_similarities.append((tgt_id, src_id, sim))

                # 频繁的数据库查询, 会导致性能问题, 所以这里注释掉
                # tgt_similarities = WallSimilarities.objects.filter(source_wall_id=tgt_id).order_by("-similarity")
                # if tgt_similarities.exists() and sim > tgt_similarities.last().similarity:
                #     created, obj = tgt_similarities.get_or_create(
                #         source_wall_id=tgt_id,
                #         target_wall_id=src_id,
                #         similarity=sim,
                #     )
                #     # 如果是新增记录, 则删除最后一名, 否则更新相似度
                #     if created:
                #         tgt_similarities.last().delete()
                #     else:
                #         obj.similarity = sim
                #         obj.save()
                #     self.stdout.write(self.style.SUCCESS(f"{datetime.now()}: 已更新 壁纸ID={tgt_id} 的 Top{topN} 相似度"))

            # step2: 对于新增壁纸，按相似度降序排序，取前TopN写入数据库
            create_similarities.sort(key=lambda x: x[2], reverse=True)
            all_similarities_data.extend(create_similarities[:topN] + update_similarities)

        # 4.批量写入数据库
        upsert_similarities_objs = [
            WallSimilarities(
                source_wall_id=src_id,
                target_wall_id=tgt_id,
                similarity=sim,
            )
            for src_id, tgt_id, sim in all_similarities_data
        ]
        upserted_objects = WallSimilarities.objects.bulk_create(
            upsert_similarities_objs,  # 要插入的数据列表
            update_conflicts=True,  # 遇到冲突时执行更新
            unique_fields=[
                "source_wall_id",
                "target_wall_id",
            ],  # 用于判断冲突的唯一字段（通常是主键或唯一约束字段）
            update_fields=["similarity"],  # 冲突时要更新的字段
            batch_size=1000,
        )
        self.stdout.write(self.style.SUCCESS(f"{datetime.now()}: 已写入/更新 {len(all_similarities_data)} 条记录。"))

        # 5.兜底处理, 删除所有 source_wall_id 壁纸大于TopN的相似度记录数
        from django.db import connection

        db_table = WallSimilarities._meta.db_table
        with connection.cursor() as cursor:
            sql = f"""
            SELECT t.id FROM (
                SELECT id, ROW_NUMBER() OVER(PARTITION BY source_wall_id ORDER BY similarity DESC) as rn 
                FROM {db_table}
            ) t WHERE t.rn > %s
            """
            logger.info(f"正在执行SQL: {sql}")
            cursor.execute(sql, [topN])
            rows = cursor.fetchall()
            ids_to_delete = [row[0] for row in rows]

        if ids_to_delete:
            # 分批删除，避免 in 列表过长
            batch_size = 1000
            for i in range(0, len(ids_to_delete), batch_size):
                WallSimilarities.objects.filter(id__in=ids_to_delete[i : i + batch_size]).delete()
            self.stdout.write(self.style.SUCCESS(f"{datetime.now()}: 已删除 {len(ids_to_delete)} 条多余的相似度记录。"))

        self.stdout.write(
            self.style.SUCCESS(
                f"{datetime.now()}: 已计算 {len(src_vecs)} 个壁纸的 Top{topN} 相似度, 共耗时 {datetime.now() - start_time}"
            )
        )
