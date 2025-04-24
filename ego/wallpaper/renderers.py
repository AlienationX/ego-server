# your_app/renderers.py
from rest_framework.renderers import JSONRenderer
from rest_framework import status

import time

class CustomJSONRenderer(JSONRenderer):
    def render(self, data, accepted_media_type=None, renderer_context=None):
        response = renderer_context.get("response") if renderer_context else None
        code = response.status_code if response else status.HTTP_500_INTERNAL_SERVER_ERROR
        # message = "success" if code < 400 else self._get_error_message(data, response)
        message = "success" if code == status.HTTP_200_OK else self._get_error_message(data, response)

        # 获取请求开始时间（需通过中间件或视图记录）, 每个接口增加cost_time耗时字段
        request = renderer_context["request"]
        if hasattr(request, 'start_time'):
            duration = time.time() - request.start_time
        else:
            duration = None

        # 判断是否为分页响应
        if isinstance(data, dict) and "pagination" in data and "data" in data:
            formatted_data = {
                "code": code,
                "message": message,
                "pagination": data["pagination"],    # 分页信息
                "data": data["data"],              # 分页数据
                # "data": data["data"] if code == status.HTTP_200_OK else [],              # 如果报错返回空列表
                "duration": f"{duration:.2f}s",
            }
        else:
            formatted_data = {
                "code": code,
                "message": message,
                "data": data,  # 非分页数据
                # "data": data if code == status.HTTP_200_OK else [],              # 如果报错返回空列表
                "duration": f"{duration:.2f}s",
            }

        return super().render(formatted_data, accepted_media_type, renderer_context)

    def _get_error_message(self, data, response):
        """提取错误信息"""
        if isinstance(data, dict):
            return data.get("detail", response.status_text)
        elif isinstance(data, list):
            return data[0] if len(data) > 0 else response.status_text
        else:
            return response.status_text