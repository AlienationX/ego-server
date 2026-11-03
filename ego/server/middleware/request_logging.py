import logging
import time

from django.conf import settings
from django.http import JsonResponse
from utils.tools import get_client_ip

logger = logging.getLogger(__name__)


class RequestLoggingMiddleware:
    """
    自定义中间件，额外增加相应时间和IP地址等。
    """

    def __init__(self, get_response):
        self.get_response = get_response
        # 忽略特定路径的请求（如静态文件）
        self.ignore_paths = ["/static/", "/favicon.ico"]

    def __call__(self, request):
        """新式中间件，替代 process_request 和 process_response，逻辑更集中"""

        # 忽略特定路径的请求（如静态文件）
        if any(request.path.startswith(path) for path in self.ignore_paths):
            return self.get_response(request)

        # 用户认证等，其实django自带auth中间件，不需要再在这里处理，除非自定义auth
        # if not request.user.is_authenticated and request.path != '/login/':
        #     return HttpResponseForbidden("请先登录")

        # 记录请求开始时间
        # start_time = time.time()
        # 自定义渲染器CustomJSONRenderer中需要使用，计算接口耗时，所以放到request中方便传递获取
        request.start_time = time.time()

        # 提取请求体数据（用于在报错时输出入参排查）
        req_body = ""
        if request.method in ["POST", "PUT", "PATCH"]:
            content_type = getattr(request, "content_type", "") or ""
            if "multipart/form-data" in content_type:
                req_body = f"<multipart/form-data: {list(request.POST.keys())}>"
            else:
                try:
                    req_body = request.body.decode("utf-8", errors="replace")[:1000]
                except Exception:
                    req_body = "<unreadable body>"
        elif request.method == "GET" and request.GET:
            req_body = str(dict(request.GET))[:500]

        # 调用 process_view 方法
        # 处理请求，调用下一个中间件或视图，即执行处理逻辑
        response = self.get_response(request)

        # 计算处理时间
        duration = time.time() - request.start_time
        user_str = request.user if getattr(request, "user", None) and request.user.is_authenticated else "Anonymous"
        client_ip = get_client_ip(request)

        # 对 4xx 和 5xx 状态码单独高亮告警并输出详细入参和返回内容
        if response.status_code >= 500:
            resp_content = getattr(response, "data", None)
            if resp_content is None:
                try:
                    resp_content = response.content.decode("utf-8", errors="replace")[:1000]
                except Exception:
                    resp_content = "<unreadable content>"
            logger.error(
                f"【全局响应异常 5xx】{request.method} {request.path}\n"
                f"Status: {response.status_code}, Duration: {duration:.2f}s\n"
                f"User: {user_str}, IP: {client_ip}\n"
                f"Request Data: {req_body}\n"
                f"Response Error: {resp_content}"
            )
        elif response.status_code >= 400:
            resp_content = getattr(response, "data", None)
            if resp_content is None:
                try:
                    resp_content = response.content.decode("utf-8", errors="replace")[:1000]
                except Exception:
                    resp_content = "<unreadable content>"
            logger.warning(
                f"【全局业务错误 4xx】{request.method} {request.path}\n"
                f"Status: {response.status_code}, Duration: {duration:.2f}s\n"
                f"User: {user_str}, IP: {client_ip}\n"
                f"Request Data: {req_body}\n"
                f"Response Error: {resp_content}"
            )
        else:
            logger.info(
                f"Request and Response: {request.method} {request.path}"
                f", User: {user_str}"
                f", IP: {client_ip}"
                f", Status: {response.status_code}"
                f", Duration: {duration:.2f}s"
            )

        return response

    # 可选：处理异常日志
    def process_exception(self, request, exception):
        """当视图抛出异常时调用，比如代码错误等没有使用try except捕获的"""

        # 记录完整的异常信息和堆栈跟踪
        logger.error(
            f"全局异常捕获[middleware]: {request.method} {request.path}\n"
            f"异常类型: {type(exception).__name__}\n"
            f"异常信息: {str(exception)}\n"
            f"IP: {get_client_ip(request)}\n"
            f"用户: {request.user if request.user.is_authenticated else 'Anonymous'}",
            exc_info=True,
        )

        # 如果是API请求（根据请求头或路径判断），返回JSON格式的错误
        if ("/api/") in request.path:
            error_data = {
                "code": "500",
                "message": "Internal Server Error",
                "detail": str(exception) if settings.DEBUG else "Internal Server Error",
            }
            return JsonResponse(error_data, status=500)

        # 或者返回 500.html 模板
        return None

    def process_view(self, request, view_func, view_args, view_kwargs):
        """在视图函数执行前调用"""
        # logger.debug(
        #     f"process_view: 即将执行视图 {type(view_func)}, {view_func}, {view_func.__name__}, {view_func.__module__}, 参数: {view_args}, {view_kwargs}"
        # )

    def process_template_response(self, request, response):
        """当视图返回 TemplateResponse 时调用"""
        # logger.debug(
        #     f"process_template_response: 即将返回 TemplateResponse {type(response)}, {response}, {response.template_name}, {response.status_code} {response.content_type}"
        # )
        return response
