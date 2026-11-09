import base64
import logging

from rest_framework import status
from rest_framework.decorators import action
from rest_framework.parsers import FormParser, JSONParser, MultiPartParser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..utils.wechat_sec import check_image_security, check_text_security

logger = logging.getLogger(__name__)


class ApiModelView(GenericViewSet):
    """
    内容安全审核 API
    用于微信小程序等平台的文本与图片前置安全合规检测
    """
    permission_classes = [HasAccessKey]
    renderer_classes = [CustomJSONRenderer]
    parser_classes = [MultiPartParser, FormParser, JSONParser]

    @action(detail=False, methods=["post"], url_path="check_text")
    def check_text(self, request):
        """
        文本内容安全检测 (POST /wallpaper/api/security/check_text/)
        入参: { "content": "待检测文本" }
        """
        content = request.data.get("content") or request.data.get("text") or ""
        openid = request.data.get("openid") or ""

        # 如果用户已登录且有微信关联信息，尝试提取 openid
        if not openid and request.user and request.user.is_authenticated:
            try:
                profile = getattr(request.user, "profile", None)
                if profile and getattr(profile, "wechat_openid", None):
                    openid = profile.wechat_openid
            except Exception:
                pass

        is_pass, err_msg = check_text_security(str(content), openid=openid)

        if not is_pass:
            return Response(
                {
                    "code": 400,
                    "message": err_msg or "内容包含敏感或违规信息，请修改后重试",
                    "data": {"pass": False},
                },
                status=status.HTTP_200_OK,  # 业务级 400，外层 200 方便前端拦截器统一处理
            )

        return Response(
            {
                "code": 200,
                "message": "检测通过",
                "data": {"pass": True},
            }
        )

    @action(detail=False, methods=["post"], url_path="check_image")
    def check_image(self, request):
        """
        图片内容安全检测 (POST /wallpaper/api/security/check_image/)
        入参: 文件上传 (media / file / image) 或 Base64 (image_base64)
        """
        image_bytes = None
        filename = "image.jpg"

        # 1. 优先从表单文件获取
        for field in ["media", "file", "image"]:
            if field in request.FILES:
                uploaded = request.FILES[field]
                filename = uploaded.name
                image_bytes = uploaded.read()
                break

        # 2. 从 Base64 字符串解析
        if not image_bytes:
            base64_data = request.data.get("image_base64") or request.data.get("base64")
            if base64_data and isinstance(base64_data, str):
                if "," in base64_data:
                    base64_data = base64_data.split(",", 1)[1]
                try:
                    image_bytes = base64.b64decode(base64_data)
                except Exception as e:
                    logger.warning(f"Base64 解析失败: {e}")

        if not image_bytes:
            return Response(
                {
                    "code": 400,
                    "message": "请上传待检测的图片数据",
                    "data": {"pass": False},
                },
                status=status.HTTP_200_OK,
            )

        is_pass, err_msg = check_image_security(image_bytes, filename=filename)

        if not is_pass:
            return Response(
                {
                    "code": 400,
                    "message": err_msg or "所选图片包含违规信息，请重新选择",
                    "data": {"pass": False},
                },
                status=status.HTTP_200_OK,
            )

        return Response(
            {
                "code": 200,
                "message": "检测通过",
                "data": {"pass": True},
            }
        )
