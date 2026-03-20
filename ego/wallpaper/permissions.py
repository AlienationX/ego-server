import logging

from django.conf import settings
from rest_framework.permissions import BasePermission

logger = logging.getLogger(__name__)


class HasAccessKey(BasePermission):
    def has_permission(self, request, view):
        access_key = request.headers.get("Access-Key", None)
        secret_key = settings.SECRET_KEY

        # logger.debug(f"verify access_key: {access_key}, secret_key: {secret_key}")
        return access_key == secret_key


class IsSuperUser(BasePermission):
    """仅允许超级管理员访问"""

    message = "仅超级管理员可访问此接口"

    def has_permission(self, request, view):
        return bool(request.user and request.user.is_superuser)
