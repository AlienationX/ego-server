import joblib
import numpy as np
from sklearn.decomposition import PCA

from .models import Image


def reduce_features_with_pca(target_dim=256):
    # 1. 从数据库加载所有特征
    features = []
    ids = []
    for img in Image.objects.filter(feature_vector__isnull=False).iterator():
        features.append(img.feature_vector)
        ids.append(img.id)
    features = np.array(features)  # shape: (N, D)

    # 2. 训练 PCA
    pca = PCA(n_components=target_dim)
    reduced = pca.fit_transform(features)

    # 3. 保存降维后的特征
    for i, img_id in enumerate(ids):
        Image.objects.filter(id=img_id).update(
            feature_lowdim=reduced[i].tolist()  # 新增字段
        )

    # 保存 PCA 模型供后续新图片使用
    joblib.dump(pca, "pca_model.pkl")


def reduce_single_feature(feature, pca_model=None):
    # 新增图片降维，降维单个特征
    if pca_model is None:
        pca_model = joblib.load("pca_model.pkl")
    return pca_model.transform([feature])[0].tolist()
