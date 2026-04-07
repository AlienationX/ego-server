# your_app/renderers.py
import time

from rest_framework.renderers import JSONRenderer


class CustomJSONRenderer(JSONRenderer):
    """
    自定义JSON渲染器，添加code和message字段
    接收到的响应码由两部分组成：外层是 HTTP 状态码，内层是响应体正文中的定义的业务错误码，提供了更具体的错误描述。
    """

    def render(self, data, accepted_media_type=None, renderer_context=None):
        # 获取请求开始时间（需通过中间件或视图记录）, 每个接口增加cost_time耗时字段
        request = renderer_context["request"]
        if hasattr(request, "start_time"):
            duration = time.time() - request.start_time
        else:
            duration = None

        response = renderer_context.get("response") if renderer_context else None
        # 从BusinessResponse响应体中获取code和message字段
        code = data["code"] if "code" in data else response.status_code
        message = data["message"] if "message" in data else response.status_text

        formatted_data = {
            "code": code,
            "message": message,
            "data": data["data"] if "data" in data else data,
            "duration": f"{duration:.2f}s",
        }

        # 增加 pagination 字段和 duration 字段
        # 判断是否为分页响应
        if "pagination" in data:
            formatted_data["pagination"] = data["pagination"]

        return super().render(formatted_data, accepted_media_type, renderer_context)
