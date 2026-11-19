import time
import uuid
from pathlib import Path

from django.conf import settings
from PIL import Image
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.generics import CreateAPIView
from rest_framework.mixins import CreateModelMixin
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet, ModelViewSet

from ..models import Feedback
from ..renderers import CustomJSONRenderer
from ..serializers import FeedbackSerializer
from ..utils.wechat_sec import check_image_security, check_text_security
from ..utils.email_notify import send_feedback_notification_async


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

        # 微信小程序渠道内容安全前置校验
        channel = request.headers.get("Channel") or data.get("channel") or ""
        device_id = (
            request.headers.get("Device-Id")
            or request.headers.get("DeviceId")
            or data.get("device_id")
            or data.get("deviceId")
            or ""
        )
        if channel == "wechat":
            content_val = data.get("content", "")
            if content_val:
                is_safe, err = check_text_security(str(content_val))
                if not is_safe:
                    return Response(
                        {"code": 400, "message": err or "内容包含敏感或违规信息，请修改后重试"},
                        status=status.HTTP_200_OK,
                    )

        # 兼容多种上传键名（images, images_0, images_1, images[], 等），收集所有上传文件
        upload_files = []
        for key in request.FILES:
            upload_files.extend(request.FILES.getlist(key))

        if channel == "wechat" and upload_files:
            for f in upload_files:
                f.seek(0)
                is_safe, err = check_image_security(f.read(), filename=f.name)
                f.seek(0)
                if not is_safe:
                    return Response(
                        {"code": 400, "message": err or "图片包含违规信息，请重新选择"},
                        status=status.HTTP_200_OK,
                    )

        # 支持保留已有图片列表（例如通过单图预上传接口获取的 URL）
        existing_images = data.get("images", [])
        if isinstance(existing_images, str):
            try:
                import json
                existing_images = json.loads(existing_images)
            except Exception:
                existing_images = [existing_images] if existing_images else []
        if not isinstance(existing_images, list):
            existing_images = []

        images_list = list(existing_images)
        if upload_files:
            for uploaded_file in upload_files:
                image_url, file_save_path = self._upload_feedback_images(uploaded_file)
                images_list.append(image_url)

        data["images"] = images_list
        data["channel"] = channel
        data["device_id"] = device_id
        if "fb_type" not in data and "type" in data:
            data["fb_type"] = data["type"]

        valid_fields = {f.name for f in Feedback._meta.fields}
        create_data = {k: v for k, v in data.items() if k in valid_fields}
        feedback = Feedback.objects.create(**create_data)

        # 提交成功后，后台异步发送邮件通知管理员
        send_feedback_notification_async(feedback)

        return Response(FeedbackSerializer(feedback).data)

    @action(detail=False, methods=["post"])
    def upload_image(self, request):
        upload_files = []
        for key in request.FILES:
            upload_files.extend(request.FILES.getlist(key))
        if not upload_files:
            return Response({"code": 400, "message": "未提供文件"}, status=status.HTTP_200_OK)

        channel = request.headers.get("Channel") or request.data.get("channel") or ""
        if channel == "wechat":
            for f in upload_files:
                f.seek(0)
                is_safe, err = check_image_security(f.read(), filename=f.name)
                f.seek(0)
                if not is_safe:
                    return Response(
                        {"code": 400, "message": err or "图片包含违规信息，请重新选择"},
                        status=status.HTTP_200_OK,
                    )

        images_list = []
        for uploaded_file in upload_files:
            image_url, _ = self._upload_feedback_images(uploaded_file)
            images_list.append(image_url)

        return Response({"code": 200, "data": {"images": images_list}})

    def _upload_feedback_images(self, uploaded_file):
        if not uploaded_file:
            raise Exception("未提供文件")

        # 1. 自定义验证：文件大小
        max_size = 4 * 1024 * 1024  # 4MB
        if uploaded_file.size > max_size:
            raise Exception(f"文件大小不能超过{max_size / 1024 / 1024}MB")

        # 2. 自定义验证：文件扩展名
        allowed_extensions = [".jpg", ".jpeg", ".png", ".webp"]
        ext = Path(uploaded_file.name).suffix.lower()
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
        random_suffix = uuid.uuid4().hex[:6]
        image_url = f"wallpaper/feedback/{dt}_{random_suffix}{ext}"
        file_save_path = Path(settings.MEDIA_ROOT) / Path(image_url)

        # 确保目录存在，避免 FileNotFoundError
        file_save_path.parent.mkdir(parents=True, exist_ok=True)

        # 保存文件到服务器
        try:
            with open(file_save_path, "wb+") as f:
                for chunk in uploaded_file.chunks():
                    f.write(chunk)
        except IOError as e:
            raise Exception(f"文件保存失败 {e.strerror}")

        return image_url, file_save_path
