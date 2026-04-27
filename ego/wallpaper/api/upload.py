import logging
import time
import uuid
from pathlib import Path

from django.conf import settings
from django.core.files.uploadedfile import InMemoryUploadedFile
from PIL import Image
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import MultiPartParser
from rest_framework.permissions import IsAdminUser, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet, ViewSet

from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer

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
        save_dir = request.data.get("dir", "upload_tmp")

        # 关键：通过 get 获取单个文件对象
        # uploaded_file = request.FILES.get("avatar")  # 'avatar' 是前端表单中文件字段的name，postman字段类型不是string，而是file

        # 关键：通过 getlist 获取所有文件对象
        uploaded_files = request.FILES.getlist("files")  # 'files' 是前端input的name

        if not uploaded_files:
            return Response({"error": "No files uploaded"}, status=status.HTTP_400_BAD_REQUEST)

        # 上传到服务器
        saved_paths = []
        for uploaded_file in uploaded_files:
            # 处理每个文件，例如保存到服务器
            file_save_path = self._upload_file(uploaded_file, save_dir=save_dir)  # 您的文件保存逻辑
            saved_paths.append(file_save_path)

        return Response({"saved_paths": saved_paths})

    @action(detail=False, methods=["post"])
    def file(self, request):
        """上传文件"""
        uploaded_file = request.FILES.get("file")
        file_save_path = self._upload_file(
            uploaded_file, max_size=10 * 1024 * 1024, allowed_extensions=[".pdf", ".doc", ".docx", ".xls", ".xlsx", ".txt"]
        )
        return Response({"saved_paths": file_save_path})

    @action(detail=False, methods=["post"])
    def img(self, request):
        """上传图片"""
        # uploaded_file = request.FILES.get("image")
        # file_save_path = self._upload_file(
        #     uploaded_file, max_size=2 * 1024 * 1024, allowed_extensions=[".jpg", ".jpeg", ".png", ".webp"], save_dir="tmp"
        # )
        # return Response({"saved_paths": file_save_path})

    @action(detail=False, methods=["post"])
    def audio(self, request):
        """上传音频"""
        # uploaded_file = request.FILES.get("audio")
        # file_save_path = self._upload_file(
        #     uploaded_file, max_size=2 * 1024 * 1024, allowed_extensions=[".mp3", ".wav", ".aac"], save_dir="tmp"
        # )
        # return Response({"saved_paths": file_save_path})

    @action(detail=False, methods=["post"])
    def video(self, request):
        """上传视频"""
        # uploaded_file = request.FILES.get("video")
        # file_save_path = self._upload_file(
        #     uploaded_file, max_size=2 * 1024 * 1024, allowed_extensions=[".mp4", ".avi", ".mov"], save_dir="tmp"
        # )
        # return Response({"saved_paths": file_save_path})

    def _upload_file(
        self,
        uploaded_file: InMemoryUploadedFile,
        max_size: int = 2 * 1024 * 1024,
        allowed_extensions: list = [".jpg", ".jpeg", ".png", ".webp"],
        save_dir: str = "wallpaper/upload_tmp",
    ) -> str:
        # logger.debug(type(uploaded_file))  # <class 'django.core.files.uploadedfile.InMemoryUploadedFile'>
        # logger.debug(uploaded_file.file)  # <_io.BytesIO object at 0x10d413d30>
        # logger.debug(uploaded_file.name)  # 7932ba4egw1dk8ujxykglj.jpg
        # logger.debug(uploaded_file.size)  # 14864
        # logger.debug(uploaded_file.content_type)  # image/jpeg

        # 1. 自定义验证：文件大小
        if uploaded_file.size > max_size:
            raise Exception(f"文件大小不能超过{max_size / 1024 / 1024}MB")

        # 2. 自定义验证：文件扩展名
        ext = Path(uploaded_file.name).suffix
        if ext not in allowed_extensions:
            raise Exception(f"不支持的文件格式。请上传{', '.join(allowed_extensions)}图片。")

        # 3. (推荐) 自定义验证：使用PIL检查文件内容是否为有效图片
        try:
            image = Image.open(uploaded_file)
            image.verify()  # 验证图片完整性
            # 重置文件指针，因为verify()或open()操作可能会改变它
            uploaded_file.seek(0)
        except Exception:
            raise Exception("无效的图片文件")

        # 使用UUID重命名文件，避免重名和特殊字符问题
        # tmp_image_path = f"{save_dir}/{uuid.uuid4().hex}{ext}"
        # 使用md5重命名文件，避免重名和特殊字符问题
        # tmp_image_path = f"tmp/{}{ext}"
        dt = int(time.time() * 1000 * 1000)
        tmp_image_path = f"{save_dir}/{dt}{ext}"
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
