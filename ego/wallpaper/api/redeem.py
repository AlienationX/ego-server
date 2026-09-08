import logging
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from rest_framework.decorators import action
from rest_framework.parsers import JSONParser
from rest_framework.permissions import IsAuthenticated
from rest_framework.viewsets import GenericViewSet

from ..business_status import BusinessStatus
from ..models import Profile, RedeemCode, RedeemRecord
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..responses import BusinessResponse

logger = logging.getLogger(__name__)


class ApiModelView(GenericViewSet):
    """
    体验码/兑换码 API
    由 urls.py 自动注册为 /api/redeem/
    """

    permission_classes = [HasAccessKey, IsAuthenticated]
    renderer_classes = [CustomJSONRenderer]
    parser_classes = [JSONParser]

    @action(detail=False, methods=["post"])
    def exchange(self, request):
        """
        兑换体验码
        POST /api/redeem/exchange/
        Body: { "code": "EGO-8888" }
        """
        code_str = str(request.data.get("code") or "").strip().upper()
        if not code_str:
            return BusinessResponse(business_status=BusinessStatus.PARAM_REQUIRED)

        user = request.user
        now = timezone.now()

        try:
            with transaction.atomic():
                # 使用行级悲观排他锁，防止高并发下超兑
                code_obj = RedeemCode.objects.select_for_update().filter(code=code_str).first()
                if not code_obj or not code_obj.is_active:
                    return BusinessResponse(business_status=BusinessStatus.REDEEM_CODE_NOT_FOUND)

                # 校验有效期
                if code_obj.valid_end and code_obj.valid_end < now:
                    return BusinessResponse(business_status=BusinessStatus.REDEEM_CODE_EXPIRED)

                # 校验总使用上限
                if code_obj.used_count >= code_obj.max_uses:
                    return BusinessResponse(business_status=BusinessStatus.REDEEM_CODE_EXHAUSTED)

                # 校验单用户是否已领过此兑换码
                if RedeemRecord.objects.filter(code=code_obj, user=user).exists():
                    return BusinessResponse(business_status=BusinessStatus.REDEEM_CODE_ALREADY_USED)

                # 更新使用次数
                code_obj.used_count += 1
                code_obj.save(update_fields=["used_count"])

                # 计算并更新用户 VIP 到期时间 (支持在原基础上顺延)
                profile, _ = Profile.objects.get_or_create(user=user)
                add_days = timedelta(days=code_obj.reward_days)
                if profile.vip_expire_time and profile.vip_expire_time > now:
                    profile.vip_expire_time += add_days
                else:
                    profile.vip_expire_time = now + add_days
                profile.save(update_fields=["vip_expire_time"])

                # 记录客户端 IP 与流水
                x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
                if x_forwarded_for:
                    ip = x_forwarded_for.split(",")[0].strip()
                else:
                    ip = request.META.get("REMOTE_ADDR")

                RedeemRecord.objects.create(
                    code=code_obj,
                    user=user,
                    reward_desc=f"VIP会员{code_obj.reward_days}天",
                    ip_address=ip,
                )

                logger.info(f"用户 {user.id}({user.username}) 成功兑换体验码 {code_obj.code} (+{code_obj.reward_days}天)")

                # message不写死，交由 BusinessResponse/renderers 根据状态码自动匹配
                return BusinessResponse(
                    data={
                        "is_vip": True,
                        "vip_expire_time": profile.vip_expire_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "reward_days": code_obj.reward_days,
                    },
                    business_status=BusinessStatus.SUCCESS,
                )

        except Exception as e:
            logger.error(f"兑换体验码异常: {e}", exc_info=True)
            return BusinessResponse(business_status=BusinessStatus.SYSTEM_ERROR)
