import time
from pathlib import Path

from django.conf import settings
from PIL import Image
from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Feedback
from ..renderers import CustomJSONRenderer
from ..serializers import FeedbackSerializer


class ApiModelView(CreateModelMixin, GenericViewSet):
    # CreateAPIView = (CreateModelMixin, GenericViewSet) # 不能使用CreateAPIView，启动报错

    queryset = Feedback.objects.all()
    serializer_class = FeedbackSerializer
    pagination_class = None  # 不使用分页器，直接返回所有数据
    renderer_classes = [CustomJSONRenderer]
    # permission_classes = []  # 这里可以根据需要设置权限类

    def create(self, request, *args, **kwargs):
        # QueryDict 用 .dict() 转为普通dict，避免赋值列表时双重包裹；JSON请求本身就是dict直接copy
        data = request.data.dict() if hasattr(request.data, "dict") else request.data.copy()
        upload_files = request.FILES.getlist("images")
        images_list = []
        if upload_files:
            for uploaded_file in upload_files:
                image_url, file_save_path = self._upload_feedback_images(uploaded_file)
                images_list.append(image_url)

        data["images"] = images_list
        feedback = Feedback.objects.create(**data)
        return Response(FeedbackSerializer(feedback).data)

    def _upload_feedback_images(self, uploaded_file):
        if not uploaded_file:
            raise Exception("未提供文件")

        # 1. 自定义验证：文件大小
        max_size = 4 * 1024 * 1024  # 4MB
        if uploaded_file.size > max_size:
            raise Exception(f"文件大小不能超过{max_size / 1024 / 1024}MB")

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

        dt = int(time.time() * 1000 * 1000)  # 当前16位时间戳
        image_url = f"feedback/{dt}{ext}"
        file_save_path = Path(settings.MEDIA_ROOT) / Path(image_url)

        # 保存文件到服务器
        try:
            with open(file_save_path, "wb+") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except IOError as e:
            raise Exception(f"文件保存失败 {e.strerror}")

        return image_url, file_save_path
