import json
import logging
import random
import time
import requests
import hashlib
from datetime import timedelta

from alipay.aop.api.AlipayClientConfig import AlipayClientConfig
from alipay.aop.api.DefaultAlipayClient import DefaultAlipayClient
from alipay.aop.api.domain.AlipayTradeAppPayModel import AlipayTradeAppPayModel
from alipay.aop.api.request.AlipayTradeAppPayRequest import AlipayTradeAppPayRequest
from alipay.aop.api.util.SignatureUtils import get_sign_content, verify_with_rsa
from django.conf import settings
from django.db import transaction
from django.http import HttpResponse
from django.utils import timezone
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
from ..utils.wechat_xpay import WeChatXPayService

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
        GET /payment/status/{order_no}/ - 查询指定订单状态（支持微信虚拟支付自动兜底查单）
        """
        try:
            order = Order.objects.get(order_no=order_no, user=request.user)
            # 若状态为 pending 且为微信虚拟支付，主动调用 query_order 进行兜底核实
            if order.status == "pending" and order.payment_method == "wechat_virtual":
                profile = getattr(request.user, "profile", None)
                openid = profile.wechat_openid if profile else None
                if openid:
                    res = WeChatXPayService.query_order(openid, order.order_no)
                    if res and res.get("errcode") == 0:
                        order_info = res.get("order", {})
                        # status: 0-待支付 1-已支付 2-已退款
                        if order_info.get("status") == 1:
                            with transaction.atomic():
                                order.status = "paid"
                                order.paid_at = timezone.now()
                                order.transaction_id = order_info.get("wx_order_id") or ""
                                order.save(update_fields=["status", "paid_at", "transaction_id"])
                                self._grant_vip(order.user, order.period_days)
                            logger.info(f"通过 query_order 兜底查单成功并已发货, order_no={order.order_no}")

            return Response({"order_no": order.order_no, "status": order.status})
        except Order.DoesNotExist:
            return Response({"error": "订单不存在"}, status=status.HTTP_404_NOT_FOUND)

    @action(detail=False, methods=["post"])
    def alipay(self, request):
        """
        POST /payment/alipay/ - 支付宝 App 支付下单
        请求体: { product_id, channel, platform, device_id }
        返回: { order_no, order_string } — order_string 直接传给 uni.requestPayment()
        """
        product_id = request.data.get("product_id")
        channel = request.data.get("channel")
        platform = request.data.get("platform")
        device_id = request.headers.get("Device-Id")

        if not product_id:
            return Response({"error": "缺少 product_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({"error": "商品不存在或已下架"}, status=status.HTTP_404_NOT_FOUND)

        # 防重与幂等处理：若用户 5 分钟内针对同一商品存在待支付订单，直接复用
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        existing_order = (
            Order.objects.filter(
                user=request.user,
                product=product,
                status="pending",
                created_at__gte=five_minutes_ago,
            )
            .order_by("-created_at")
            .first()
        )

        if existing_order:
            order = existing_order
            logger.info("复用已存在的待支付订单，order_no=%s", order.order_no)
        else:
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
                    channel=channel,
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
        logger.info("支付宝回调 request.Post: %s", data)
        sign = data.pop("sign", None)
        data.pop("sign_type", None)

        # 验证签名
        try:
            public_key = settings.DECOUPLE_CONFIG("ALIPAY_PUBLIC_KEY")
            sign_content = get_sign_content(data)
            success = verify_with_rsa(public_key, sign_content.encode("utf-8"), sign)
            if not success:
                logger.error("支付宝回调签名验证不通过，sign=%s", sign)
                return HttpResponse("fail", content_type="text/plain")
        except Exception:
            logger.exception("支付宝回调签名验证异常")
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
    def wechat_virtual_pay(self, request):
        """
        POST /payment/wechat_virtual_pay/ - 微信小程序虚拟支付（道具直购）下单
        请求体: { product_id, channel, platform, code }
        返回: { order_no, mode, signData, paySig, signature }
        """
        product_id = request.data.get("product_id")
        channel = request.data.get("channel")
        platform = request.data.get("platform")
        code = request.data.get("code")
        device_id = request.headers.get("Device-Id")

        if not product_id:
            return Response({"error": "缺少 product_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({"error": "商品不存在或已下架"}, status=status.HTTP_404_NOT_FOUND)

        user = request.user
        profile, _ = Profile.objects.get_or_create(user=user)

        # 尝试通过前端传来的最新 code 刷新 session_key
        if code:
            try:
                resp = requests.get(
                    "https://api.weixin.qq.com/sns/jscode2session",
                    params={
                        "appid": settings.WECHAT_APPID,
                        "secret": settings.WECHAT_SECRET,
                        "js_code": code,
                        "grant_type": "authorization_code",
                    },
                    timeout=5,
                )
                wx_res = resp.json()
                s_key = wx_res.get("session_key")
                o_id = wx_res.get("openid")
                if s_key:
                    profile.wechat_session_key = s_key
                if o_id and not profile.wechat_openid:
                    profile.wechat_openid = o_id
                profile.save(update_fields=["wechat_session_key", "wechat_openid"])
            except Exception as e:
                logger.warning(f"通过 code 刷新 session_key 失败: {e}")

        session_key = profile.wechat_session_key
        if not session_key:
            return Response({"error": "未获取到微信登录凭证，请在小程序端重新授权或传入 code"}, status=status.HTTP_400_BAD_REQUEST)

        # 防重与幂等处理：若用户 5 分钟内针对同一商品存在待支付订单，直接复用
        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        existing_order = (
            Order.objects.filter(
                user=user,
                product=product,
                payment_method="wechat_virtual",
                status="pending",
                created_at__gte=five_minutes_ago,
            )
            .order_by("-created_at")
            .first()
        )

        if existing_order:
            order = existing_order
            logger.info("复用已存在的待支付微信虚拟支付订单，order_no=%s", order.order_no)
        else:
            with transaction.atomic():
                order = Order.objects.create(
                    order_no=self._generate_order_no(),
                    user=user,
                    device_id=device_id or "",
                    product=product,
                    product_name=product.name,
                    price=product.price,
                    original_price=product.original_price,
                    currency=product.currency,
                    period_days=product.period_days,
                    amount=product.price,
                    channel=channel or "wechat",
                    platform=platform or "mp-weixin",
                    payment_method="wechat_virtual",
                    status="pending",
                )

        try:
            # 微信虚拟支付金额单位为分
            goods_price_fen = int(round(float(product.price) * 100))
            # 道具ID：优先取 Product.wx_product_id，其次 code，其次 id
            xpay_product_id = product.wx_product_id or product.code or f"vip_{product.id}"

            pay_data = WeChatXPayService.build_order_pay_data(
                out_trade_no=order.order_no,
                product_id=xpay_product_id,
                goods_price_fen=goods_price_fen,
                session_key=session_key,
                buy_quantity=1,
                attach=f"user_{user.id}",
            )

            logger.info(f"微信虚拟支付下单成功, order_no={order.order_no}, pay_data={pay_data}")
            return Response({
                "order_no": order.order_no,
                **pay_data,
            })
        except Exception as e:
            logger.exception(f"微信虚拟支付下单失败, order_no={order.order_no}: {e}")
            return Response({"error": f"微信虚拟支付下单失败: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=False, methods=["get", "post"], permission_classes=[AllowAny])
    def wechat_virtual_notify(self, request):
        """
        GET  /payment/wechat_virtual_notify/ - 微信公众平台消息推送服务器 Token 有效性验证
        POST /payment/wechat_virtual_notify/ - 微信虚拟支付官方发货推送异步回调（无需鉴权）
        微信推送格式为 XML，处理完毕后必须返回格式为 <xml><ErrCode>0</ErrCode><ErrMsg><![CDATA[success]]></ErrMsg></xml>
        """
        # 1. 响应微信公众平台后台配置消息推送时的 GET 校验请求
        if request.method.lower() == "get":
            signature = request.GET.get("signature", "")
            timestamp = request.GET.get("timestamp", "")
            nonce = request.GET.get("nonce", "")
            echostr = request.GET.get("echostr", "")
            token = getattr(settings, "WECHAT_MSG_TOKEN", "egowallpaper")
            tmp_list = sorted([token, timestamp, nonce])
            hashcode = hashlib.sha1("".join(tmp_list).encode("utf-8")).hexdigest()

            if hashcode == signature:
                logger.info("微信消息推送 Token 校验通过")
                return HttpResponse(echostr, content_type="text/plain")
            else:
                logger.warning(f"微信消息推送 Token 校验不匹配, calc={hashcode}, sign={signature}, echostr={echostr}")
                return HttpResponse(echostr, content_type="text/plain")

        # 获取原始 XML 内容
        raw_body = request.body.decode("utf-8") if isinstance(request.body, bytes) else str(request.body or "")
        logger.info(f"收到微信虚拟支付发货推送: {raw_body}")

        notify_data = WeChatXPayService.parse_deliver_notify_xml(raw_body)
        if not notify_data:
            logger.error("解析微信虚拟支付发货推送失败")
            return HttpResponse(WeChatXPayService.format_deliver_response(-1, "invalid xml"), content_type="text/xml")

        event = notify_data.get("event")
        out_trade_no = notify_data.get("out_trade_no")
        wx_order_id = notify_data.get("wx_order_id")

        if event != "xpay_goods_deliver_notify":
            logger.warning(f"忽略非发货推送事件: {event}")
            return HttpResponse(WeChatXPayService.format_deliver_response(0, "success"), content_type="text/xml")

        if not out_trade_no:
            logger.error("推送数据缺少 OutTradeNo")
            return HttpResponse(WeChatXPayService.format_deliver_response(-1, "missing out_trade_no"), content_type="text/xml")

        try:
            with transaction.atomic():
                order = Order.objects.select_for_update().filter(order_no=out_trade_no).first()
                if not order:
                    logger.error(f"发货推送对应订单不存在: {out_trade_no}")
                    return HttpResponse(WeChatXPayService.format_deliver_response(-1, "order not found"), content_type="text/xml")

                # 幂等核验：若已发货，直接回复成功
                if order.status == "paid":
                    logger.info(f"订单已发货，幂等直接返回成功: {out_trade_no}")
                    return HttpResponse(WeChatXPayService.format_deliver_response(0, "success"), content_type="text/xml")

                # 发货并开通权益
                order.status = "paid"
                order.paid_at = timezone.now()
                order.transaction_id = wx_order_id or order.transaction_id or ""
                order.save(update_fields=["status", "paid_at", "transaction_id"])
                self._grant_vip(order.user, order.period_days)
                logger.info(f"微信虚拟支付发货成功，已为用户 {order.user_id} 激活 VIP {order.period_days} 天, order_no={out_trade_no}, wx_order_id={wx_order_id}")

            return HttpResponse(WeChatXPayService.format_deliver_response(0, "success"), content_type="text/xml")
        except Exception as e:
            logger.exception(f"处理微信发货推送异常, out_trade_no={out_trade_no}: {e}")
            return HttpResponse(WeChatXPayService.format_deliver_response(-1, str(e)), content_type="text/xml")

    @action(detail=False, methods=["post"])
    def wxpay(self, request):
        """POST /payment/wxpay/ - 微信App支付（保留备用）"""
        return Response({"error": "微信App支付暂未开放"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=["post"])
    def paypal(self, request):
        """POST /payment/paypal/ - PayPal支付（待实现）"""
        return Response({"error": "PayPal支付暂未开放"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=["post"])
    def google_play(self, request):
        """POST /payment/google_play/ - Google Play支付（待实现）"""
        return Response({"error": "Google Play支付暂未开放"}, status=status.HTTP_501_NOT_IMPLEMENTED)

    @action(detail=False, methods=["post"])
    def huawei_pay(self, request):
        """
        POST /payment/huawei_pay/ - 华为应用内支付（IAP）下单
        请求体: { product_id, channel, platform, device_id }
        返回: { order_no, order_string, purchase_params }
        """
        product_id = request.data.get("product_id")
        channel = request.data.get("channel")
        platform = request.data.get("platform")
        device_id = request.headers.get("Device-Id")

        if not product_id:
            return Response({"error": "缺少 product_id"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            product = Product.objects.get(id=product_id, is_active=True)
        except Product.DoesNotExist:
            return Response({"error": "商品不存在或已下架"}, status=status.HTTP_404_NOT_FOUND)

        five_minutes_ago = timezone.now() - timedelta(minutes=5)
        existing_order = (
            Order.objects.filter(
                user=request.user,
                product=product,
                status="pending",
                created_at__gte=five_minutes_ago,
            )
            .order_by("-created_at")
            .first()
        )

        if existing_order:
            order = existing_order
            logger.info("复用已存在的华为待支付订单，order_no=%s", order.order_no)
        else:
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
                    channel=channel,
                    platform=platform,
                    payment_method="huawei",
                    status="pending",
                )

        huawei_product_id = f"vip_product_{product.id}"
        purchase_params = {
            "merchantOrderId": order.order_no,
            "productId": huawei_product_id,
            "price": str(product.price),
            "currency": product.currency or "CNY",
            "productName": product.name,
            "applicationId": settings.HUAWEI_CLIENT_ID,
        }
        order_string = json.dumps(purchase_params)

        logger.info("华为支付下单成功，order_no=%s", order.order_no)
        return Response({
            "order_no": order.order_no,
            "order_string": order_string,
            "purchase_params": purchase_params,
        })

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def huawei_notify(self, request):
        """
        POST /payment/huawei_notify/ - 华为 IAP 官方服务端关键事件回调通知（无需鉴权）
        """
        data = request.data or {}
        logger.info("华为支付服务端通知 request.data: %s", data)

        # 1. 尝试解析 JWS 通知 payload (HarmonyOS V3 通知)
        jws_notification = data.get("notificationPayload") or data.get("jwsNotification") or data.get("purchaseData")
        out_trade_no = None
        purchase_order_id = None
        purchase_token = None
        purchase_state = None

        if jws_notification and isinstance(jws_notification, str) and "." in jws_notification:
            from ..utils.huawei_iap import HuaweiJWSChecker

            payload = HuaweiJWSChecker.decode_jws(jws_notification)
            if payload:
                logger.info(f"解析到华为回调通知 Payload: {payload}")
                purchase_order = payload.get("purchaseOrder") or payload
                out_trade_no = purchase_order.get("merchantOrderId") or purchase_order.get("developerPayload")
                purchase_order_id = purchase_order.get("purchaseOrderId") or purchase_order.get("payOrderId")
                purchase_token = purchase_order.get("purchaseToken")
                purchase_state = purchase_order.get("purchaseState", 0)

        # 2. 兼容传统 JSON 格式
        if not out_trade_no:
            purchase_data = data.get("purchaseData") or data.get("inAppPurchaseData")
            if purchase_data:
                try:
                    p_json = json.loads(purchase_data) if isinstance(purchase_data, str) else purchase_data
                    out_trade_no = p_json.get("developerPayload") or p_json.get("merchantOrderId") or p_json.get("orderId")
                    purchase_state = p_json.get("purchaseState")
                    purchase_order_id = p_json.get("payOrderId") or p_json.get("purchaseOrderId")
                    purchase_token = p_json.get("purchaseToken")
                except Exception as e:
                    logger.warning(f"解析 purchaseData 异常: {e}")

        if not out_trade_no:
            logger.warning("华为支付回调通知缺少有效订单标识")
            return Response({"result": 0, "message": "Ignored"})

        try:
            if purchase_state is None or purchase_state == 0 or purchase_state == "0":
                with transaction.atomic():
                    order = Order.objects.select_for_update().get(order_no=out_trade_no, status="pending")
                    order.status = "paid"
                    order.paid_at = timezone.now()
                    order.transaction_id = purchase_order_id or ""
                    order.save(update_fields=["status", "paid_at", "transaction_id"])
                    self._grant_vip(order.user, order.period_days)

                # 向华为确认发货
                if purchase_order_id and purchase_token:
                    from ..utils.huawei_iap import HuaweiIAPService

                    HuaweiIAPService.order_shipped_confirm(purchase_order_id, purchase_token)

                logger.info("华为支付服务端回调处理成功，已为用户发放 VIP，order_no=%s", out_trade_no)
                return Response({"result": 0, "message": "Success"})
        except Order.DoesNotExist:
            logger.info("华为支付回调通知：订单已处理或不存在，order_no=%s", out_trade_no)
            return Response({"result": 0, "message": "Order already processed or not found"})
        except Exception as e:
            logger.exception("华为支付回调处理异常: %s", e)
            return Response({"result": 1, "message": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"result": 0, "message": "OK"})

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
