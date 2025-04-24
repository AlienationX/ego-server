# authentication.py
from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication
from server.settings import SECRET_KEY


class ApiKeyJWTAuthentication(BaseAuthentication):
    def authenticate(self, request):
        # 1. 提取并校验自定义密钥（如 X-API-Key）
        access_key = request.headers.get('Access-Key')
        if not access_key:
            raise AuthenticationFailed('Access Key 缺失')  # 401
        
        # 密钥校验逻辑（示例：对比预设值或数据库查询）
        if access_key != SECRET_KEY:
            raise AuthenticationFailed('Access Key 无效')  # 401
        
        # 2. 继续执行 JWT 认证（如使用 rest_framework_simplejwt）
        jwt_auth = JWTAuthentication()
        return jwt_auth.authenticate(request)  # 返回 (user, token)