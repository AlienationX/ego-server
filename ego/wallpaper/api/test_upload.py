import base64
import json
import logging
import uuid
from pathlib import Path

import requests
from django.conf import settings
from PIL import Image
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from ..models import Actions, Classify, Profile
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import ProfileSerializer, UserSerializer, WallSerializer

logger = logging.getLogger(__name__)


class ApiModelView(GenericViewSet):

    parser_classes = [MultiPartParser]  # 重要：允许处理文件上传
    # queryset = User.objects.select_related("profile").all()
    # serializer_class = UserSerializer
    # authentication_classes = [JSONWebTokenAuthentication]  # JWT 认证, 已在settings中全局配置
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]

    @action(detail=False, methods=["post"])
    def files(self, request):
        # 关键：通过 get 获取单个文件对象
        # uploaded_file = request.FILES.get("avatar")  # 'avatar' 是前端表单中文件字段的name，postman字段类型不是string，而是file

        # 关键：通过 getlist 获取所有文件对象
        uploaded_files = request.FILES.getlist("files")  # 'files' 是前端input的name

        if not uploaded_files:
            return Response({"error": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # 1. 上传到服务器
        saved_paths = []
        for uploaded_file in uploaded_files:
            # 处理每个文件，例如保存到服务器
            file_save_path = self._update_file(uploaded_file)  # 您的文件保存逻辑
            saved_paths.append(file_save_path)

        # 2. 使用llm进行图片分类及生成相关信息
        for path in saved_paths:
            info = self._generate_info(path)

        # 3. 移动到正式路径及上传到云服务器

        # 4. 更新数据库

        return Response({"saved_paths": saved_paths})

    def _update_file(self, uploaded_file) -> str:

        logger.debug(type(uploaded_file))  # <class 'django.core.files.uploadedfile.InMemoryUploadedFile'>
        logger.debug(uploaded_file.file)  # <_io.BytesIO object at 0x10d413d30>
        logger.debug(uploaded_file.name)  # 7932ba4egw1dk8ujxykglj.jpg
        logger.debug(uploaded_file.size)  # 14864
        logger.debug(uploaded_file.content_type)  # image/jpeg

        # 1. 自定义验证：文件大小
        max_size = 1 * 1024 * 1024  # 1MB
        if uploaded_file.size > max_size:
            raise Exception("文件大小不能超过1MB")

        # 2. 自定义验证：文件扩展名
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        ext = Path(uploaded_file.name).suffix
        if ext not in allowed_extensions:
            raise Exception("不支持的文件格式。请上传JPG, JPEG, PNG或WebP图片。")

        # 3. (推荐) 自定义验证：使用PIL检查文件内容是否为有效图片
        try:
            image = Image.open(uploaded_file)
            image.verify()  # 验证图片完整性
            # 重置文件指针，因为verify()或open()操作可能会改变它
            uploaded_file.seek(0)
        except Exception:
            raise Exception("无效的图片文件")

        # 使用UUID重命名文件，避免重名和特殊字符问题
        tmp_image_path = f"tmp/{uuid.uuid4().hex}{ext}"
        # 使用md5重命名文件，避免重名和特殊字符问题
        # tmp_image_path = f"tmp/{}{ext}"
        file_save_path = Path(settings.MEDIA_ROOT) / Path(tmp_image_path)
        logger.debug(file_save_path)

        # 保存文件到服务器
        try:
            with open(file_save_path, "wb+") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except IOError as e:
            raise Exception(f"文件保存失败 {e.strerror}")

        return tmp_image_path

    def _generate_info(self, img_path) -> dict:
        with open(img_path, "rb") as img_file:
            img_base = base64.b64encode(img_file.read()).decode("utf-8")

        # exclude 取反 实现 notin 逻辑
        classify_objects = Classify.objects.all().exclude(name__in=("必应每日壁纸", "宝可梦官方壁纸", "宝可梦睡眠"))
        classcfy_name = [obj.name for obj in classify_objects]

        prompt = f"""根据图片内容，回答以下问题：
        1. 用自然柔和的语言，生成图片描述，30字以内
        2. 生成2到5个中文标签（tag），用英文逗号分隔，逗号之间不要有空格
        3. 在以下分类中选择最合适的一个作为图片分类：{', '.join(classcfy_name)}
        请将回答内容以json格式返回，key分别为：description, tabs, classify_name
        """

        url = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
        headers = {"Authorization": f"Bearer {settings.DECOUPLE_CONFIG("ZHIPU_API_KEY")}", "Content-Type": "application/json"}
        data = {
            "model": "glm-4.6v",  # glm-4.6v-flash、glm-4.6v 付费
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "image_url",
                            "image_url": {
                                # "url": "https://cloudcovert-1305175928.cos.ap-guangzhou.myqcloud.com/%E5%9B%BE%E7%89%87grounding.PNG"
                                "url": img_base
                            },
                        },
                        {
                            "type": "text",
                            "text": prompt,
                        },
                    ],
                }
            ],
            # "thinking": {"type": "enabled"},
        }

        response = requests.post(url, headers=headers, json=data)
        response.raise_for_status()

        result = response.json()
        logger.debug(json.dumps(result, indent=2, ensure_ascii=False))

        content = result["choices"][0]["message"]["content"].strip()
        # 已经包含字段：description, tabs, classify_name
        info = json.loads(content)
        info["tabs"] = info.get("tabs").replace(", ", ",")
        info["pic_path_prefix"] = classify_objects.get(name=info["classify_name"]).pic_path_prefix
        info["classify_id"] = classify_objects.get(name=info["classify_name"]).id

        return info
