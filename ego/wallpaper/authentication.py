# authentication.py
# from server.settings import SECRET_KEY. # 不推荐直接导入settings文件
import logging

from django.conf import settings
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication

logger = logging.getLogger(__name__)


class ApiKeyJWTAuthentication(BaseAuthentication):
    """自定义认证类，先校验自定义密钥，再执行 JWT 认证"""

    def authenticate(self, request):
        logger.info(f"Request authentication headers: {request.headers}")

        # 1. 提取并校验自定义密钥（如 X-API-Key）
        access_key = request.headers.get("Access-Key")
        if not access_key:
            raise AuthenticationFailed("Access Key 缺失")  # 401

        # 密钥校验逻辑（示例：对比预设值或数据库查询）
        if access_key != settings.SECRET_KEY:
            raise AuthenticationFailed("Access Key 无效")  # 401

        # 2. 继续执行 JWT 认证（如使用 rest_framework_simplejwt）
        jwt_auth = JWTAuthentication()
        return jwt_auth.authenticate(request)  # 返回 (user, token)
