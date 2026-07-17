import logging
import random
import time
from datetime import timedelta

from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayTradeAppPayModel import AlipayTradeAppPayModel
from alipay.aop.api.request.AlipayTradeAppPayRequest import AlipayTradeAppPayRequest
from alipay.aop.api.util.SignatureUtils import verify_with_rsa
from django.conf import settings
from django.db import transaction
from django.utils import timezone
from django.http import HttpResponse
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.mixins import CreateModelMixin, ListModelMixin, RetrieveModelMixin
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from ..models import Order, Product, Profile
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey
from ..renderers import CustomJSONRenderer
from ..serializers import OrderSerializer, ProductSerializer

logger = logging.getLogger(__name__)


def get_alipay_client():
    """创建支付宝客户端，从 settings 读取配置"""
    config = AlipayClientConfig()
    config.server_url = settings.DECOUPLE_CONFIG("ALIPAY_SERVER_URL", default="https://openapi.alipay.com/gateway.do")
    config.app_id = settings.DECOUPLE_CONFIG("ALIPAY_APP_ID")
    config.app_private_key = settings.DECOUPLE_CONFIG("ALIPAY_APP_PRIVATE_KEY")
    config.alipay_public_key = settings.DECOUPLE_CONFIG("ALIPAY_PUBLIC_KEY")
    config.charset = "utf-8"
    config.format = "json"
    return DefaultAlipayClient(alipay_client_config=config)



class ApiModelView(ListModelMixin, CreateModelMixin, RetrieveModelMixin, GenericViewSet):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [HasAccessKey, IsAuthenticated]
    pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    # def get_queryset(self):
    #     """只返回当前用户自己的订单"""
    #     return Order.objects.filter(user=self.request.user).order_by("-created_at")

    # def list(self, request, *args, **kwargs):
    #     """GET /payment/ - 当前用户订单列表"""
    #     return super().list(request, *args, **kwargs)

    # def retrieve(self, request, *args, **kwargs):
    #     """GET /payment/{id}/ - 订单详情"""
    #     return super().retrieve(request, *args, **kwargs)

    # def create(self, request, *args, **kwargs):
    #     """POST /payment/ - 暂不开放直接创建，下单通过 alipay/wxpay action"""
    #     return Response({"error": "请通过支付方式接口下单"}, status=status.HTTP_405_METHOD_NOT_ALLOWED)

    @action(detail=False, methods=["get"], permission_classes=[HasAccessKey])
    def products(self, request):
        """GET /payment/products/ - 获取上架商品列表（无需登录）"""
        queryset = Product.objects.filter(is_active=True).order_by("price")
        serializer = ProductSerializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["get"], url_path="status/(?P<order_no>[^/.]+)")
    def order_status(self, request, order_no=None):
        """
        GET /payment/status/{order_no}/ - 查询指定订单状态
        """
        try:
            order = Order.objects.get(order_no=order_no, user=request.user)
            return Response({"order_no": order.order_no, "status": order.status})
        except Order.DoesNotExist:
            return Response({"error": "订单不存在"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["post"])
    def alipay(self, request):
        """
        POST /payment/alipay/ - 支付宝 App 支付下单
        请求体: { product_id, platform, device_id }
        返回: { order_no, order_string } — order_string 直接传给 uni.requestPayment()
        """
        product_id = request.data.get("product_id")
        platform = request.data.get("platform", "unknown")
        device_id = request.headers.get("Device-Id")

        if not product_id:
            return Response({"error": "缺少 product_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({"error": "商品不存在或已下架"}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            order = Order.objects.create(
                order_no=self._generate_order_no(),
                user=request.user,
                device_id=device_id,
                product=product,
                product_name=product.name,
                price=product.price,
                original_price=product.original_price,
                currency=product.currency,
                period_days=product.period_days,
                amount=product.price,
                platform=platform,
                payment_method="alipay",
                status="pending",
            )

        try:
            client = get_alipay_client()

            model = AlipayTradeAppPayModel()
            model.out_trade_no = order.order_no
            model.subject = product.name
            model.total_amount = str(product.price)
            model.product_code = "QUICK_MSECURITY_PAY"
            model.body = product.description or product.name
            model.timeout_express = "30m"

            req = AlipayTradeAppPayRequest(biz_model=model)
            req.notify_url = settings.DECOUPLE_CONFIG("ALIPAY_NOTIFY_URL", default="")
            order_string = client.sdk_execute(req)
            logger.info("支付宝下单成功，order_no=%s", order.order_no)
            return Response({"order_no": order.order_no, "order_string": order_string})

        except Exception:
            logger.exception("支付宝下单失败，order_no=%s", order.order_no)
            order.status = "failed"
            order.save(update_fields=["status"])
            return Response({"error": "支付宝下单失败，请稍后重试"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def alipay_notify(self, request):
        """
        POST /payment/alipay_notify/ - 支付宝异步通知回调（无需鉴权）
        支付宝以 application/x-www-form-urlencoded 格式 POST 过来
        必须以 text/plain 格式返回 success 或 fail
        """
        data = request.POST.dict()
        logger.debug("支付宝回调 request.Post: %s", data)
        logger.debug("支付宝回调 request.data: %s", request.data)
        sign = data.pop("sign", None)
        data.pop("sign_type", None)

        # 验证签名
        try:
            public_key = settings.DECOUPLE_CONFIG("ALIPAY_PUBLIC_KEY")
            sorted_params = "&".join([f"{k}={v}" for k, v in sorted(data.items())])
            verify_with_rsa(public_key, sorted_params, sign, "utf-8")
        except Exception:
            logger.exception("支付宝回调签名验证失败")
            return HttpResponse("fail", content_type="text/plain")

        trade_status = data.get("trade_status")
        out_trade_no = data.get("out_trade_no")
        trade_no = data.get("trade_no")

        if trade_status == "TRADE_SUCCESS":
            try:
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(order_no=out_trade_no, status="pending")
                    order.status = "paid"
                    order.paid_at = timezone.now()
                    order.transaction_id = trade_no
                    order.save(update_fields=["status", "paid_at", "transaction_id"])
                    self._grant_vip(order.user, order.period_days)
                logger.info("支付宝回调处理成功，order_no=%s, trade_no=%s", out_trade_no, trade_no)
            except Order.DoesNotExist:
                logger.warning("支付宝回调：订单不存在或状态不是 pending，order_no=%s", out_trade_no)
            except Exception:
                logger.exception("支付宝回调处理异常，order_no=%s", out_trade_no)
                return HttpResponse("fail", content_type="text/plain")

        return HttpResponse("success", content_type="text/plain")


    # ──────────────── 测试沙盒 ────────────────
    @action(detail=False, methods=["post"], url_path="mock_pay/(?P<order_no>[^/.]+)")
    def mock_pay(self, request, order_no=None):
        """
        POST /payment/mock_pay/{order_no}/ - 仅供测试：一键模拟付款成功
        """
        try:
            order = Order.objects.get(order_no=order_no, user=request.user, status="pending")
        except Order.DoesNotExist:
            return Response({"error": "订单不存在或状态不是 pending"}, status=status.HTTP_404_NOT_FOUND)

        with transaction.atomic():
            order.status = "paid"
            order.paid_at = timezone.now()
            order.transaction_id = f"MOCK_ALIPAY_{int(time.time())}"
            order.save(update_fields=["status", "paid_at", "transaction_id"])
            self._grant_vip(order.user, order.period_days)

        logger.info("Mock 支付成功，order_no=%s", order_no)
        return Response({"message": "模拟支付成功"})

    @action(detail=False, methods=["post"])
    def wxpay(self, request):
        """POST /payment/wxpay/ - 微信支付（待实现）"""
        return Response({"error": "微信支付暂未开放"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=["post"])
    def paypal(self, request):
        """POST /payment/paypal/ - PayPal支付（待实现）"""
        return Response({"error": "PayPal支付暂未开放"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=["post"])
    def google_play(self, request):
        """POST /payment/google_play/ - Google Play支付（待实现）"""
        return Response({"error": "Google Play支付暂未开放"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=["post"])
    def ios_app_store(self, request):
        """POST /payment/ios_app_store/ - iOS App Store支付（待实现）"""
        return Response({"error": "iOS App Store支付暂未开放"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    def _generate_order_no(self):
        # 获取带时区感知的本地时间
        local_now = timezone.localtime(timezone.now())
        # 格式化时间并截取毫秒（微秒前 3 位）
        timestamp = local_now.strftime("%Y%m%d%H%M%S%f")[:-3]
        random_str = str(random.randint(1000, 9999))
        return f"NO{timestamp}{random_str}"

    def _grant_vip(self, user, period_days):
        """为用户充值 VIP 时间，支持叠加"""
        profile, _ = Profile.objects.get_or_create(user=user)
        now = timezone.now()
        if profile.vip_expire_time and profile.vip_expire_time > now:
            profile.vip_expire_time += timedelta(days=period_days)
        else:
            profile.vip_expire_time = now + timedelta(days=period_days)
        profile.save(update_fields=["vip_expire_time"])