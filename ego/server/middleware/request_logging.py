import logging
import time

from django.http import JsonResponse

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

        # 记录请求信息
        # logger.info(
        #     f"Request: {request.method} {request.path} "
        #     f"User: {request.user if request.user.is_authenticated else 'Anonymous'} "
        #     f"IP: {request.META.get('REMOTE_ADDR')}"
        # )

        # 调用 process_view 方法
        # 处理请求，调用下一个中间件或视图，即执行处理逻辑
        response = self.get_response(request)

        # 计算处理时间
        duration = time.time() - request.start_time

        # 记录响应信息
        # logger.info(
        #     f"Response: {request.method} {request.path} "
        #     f"Status: {response.status_code} "
        #     f"Duration: {duration:.2f}s"
        # )

        # 合并成一条请求数据
        logger.info(
            f"Request and Response: {request.method} {request.path}"
            f", User: {request.user if request.user.is_authenticated else 'Anonymous'}"
            f", IP: {request.META.get('REMOTE_ADDR')}"
            f", Status: {response.status_code}"
            f", Duration: {duration:.2f}s"
        )

        return response

    def process_view(self, request, view_func, view_args, view_kwargs):
        """在视图函数执行前调用"""
        # logger.info(f"process_view: 即将执行视图 {view_func.__name__}")
        pass

    # 可选：处理异常日志
    def process_exception(self, request, exception):
        """当视图抛出异常时调用"""
        logger.error(
            f"Unhandled exception [middleware]: {request.META.get('REMOTE_ADDR')} {request.method} {request.path} Error:\n {exception}",
            exc_info=True,
        )

        # 如果是API请求（根据请求头或路径判断），返回JSON格式的错误
        if ("/api/") in request.path:
            return JsonResponse({"code": "500", "message": "middleware 服务器内部错误", "detail": str(exception)}, status=500)

        return None

    # def process_template_response(self, request, response):
    #     """当视图返回 TemplateResponse 时调用"""
    #     logger.info("当视图返回 TemplateResponse 时调用")
    #     return response
