import json

import numpy as np
import torch
import torchvision.models as models
import torchvision.transforms as transforms
from PIL import Image


class ImageFeatureExtractor:
    def __init__(self, model_name="resnet50", device="cuda"):
        self.device = device if torch.cuda.is_available() else "cpu"

        # 加载预训练模型
        if model_name == "resnet50":
            self.model = models.resnet50(weights=models.ResNet50_Weights.IMAGENET1K_V1)
            self.model = torch.nn.Sequential(*list(self.model.children())[:-1])  # 去掉分类层
            self.feature_dim = 2048
        elif model_name == "efficientnet_b0":
            self.model = models.efficientnet_b0(weights=models.EfficientNet_B0_Weights.IMAGENET1K_V1)
            self.model = torch.nn.Sequential(*list(self.model.children())[:-1])
            self.feature_dim = 1280
        elif model_name == "mobilenet_v3_large":
            self.model = models.mobilenet_v3_large(weights=models.MobileNet_V3_Large_Weights.IMAGENET1K_V1)
            self.feature_dim = 960  # 使用MobileNetV3，速度更快
        else:
            raise ValueError(f"未实现的模型: {model_name}")

        self.model_name = model_name
        self.model = self.model.to(self.device)
        self.model.eval()

        # 图像预处理
        self.transform = transforms.Compose(
            [
                transforms.Resize(256),
                transforms.CenterCrop(224),
                transforms.ToTensor(),
                transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
            ]
        )

    def extract_features(self, image_path):
        """提取单张图片的特征向量"""
        img = Image.open(image_path).convert("RGB")
        img_tensor = self.transform(img).unsqueeze(0).to(self.device)

        with torch.no_grad():
            features = self.model(img_tensor)
            features = features.squeeze().cpu().numpy()  # 转为numpy数组

        # L2归一化，使余弦相似度等价于欧氏距离
        features = features / np.linalg.norm(features)
        return features, self.feature_dim, self.model_name

    def reduce_dimension(self, features, target_dim=128):
        """
        features: 二维数组，每个元素是一个特征向量
        将每个特征降维到target_dim维，减少存储和计算量
        保留90%以上信息的情况下，计算量减少16倍
        """
        from sklearn.decomposition import PCA

        # 使用PCA降维
        pca = PCA(n_components=target_dim)
        features_compressed = pca.fit_transform(features)
        return features_compressed


class FeatureStorage:
    @staticmethod
    def vector_to_blob(feature_vector: np.ndarray) -> bytes:
        """将numpy数组转换为二进制BLOB。512维float32 ≈ 2KB"""
        # 确保是float32类型
        vector_float32 = feature_vector.astype(np.float32)
        # 转换为二进制
        return vector_float32.tobytes()

    @staticmethod
    def blob_to_vector(blob: bytes, dim: int) -> np.ndarray:
        """从BLOB恢复numpy数组"""
        # 从二进制读取
        vector = np.frombuffer(blob, dtype=np.float32)
        # 验证维度
        if len(vector) != dim:
            raise ValueError(f"维度不匹配: 期望{dim}, 实际{len(vector)}")
        return vector

    @staticmethod
    def vector_to_json(feature_vector: np.ndarray, precision: int = 6) -> str:
        """转换为JSON字符串（便于调试，但体积大）。512维 ≈ 8KB (不推荐)"""
        # 保留小数位减少体积
        vector_list = [round(float(x), precision) for x in feature_vector]
        return json.dumps(vector_list)

    @staticmethod
    def json_to_vector(json_str: str) -> np.ndarray:
        """从JSON恢复numpy数组"""
        vector_list = json.loads(json_str)
        return np.array(vector_list, dtype=np.float32)


# 使用示例
if __name__ == "__main__":
    extractor = ImageFeatureExtractor(model_name="resnet50")
    features, paths = extractor.batch_extract("your_image_folder/")
