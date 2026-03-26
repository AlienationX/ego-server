from typing import Any, Dict, Optional, Union

from rest_framework import status
from rest_framework.response import Response

from .business_status import BusinessStatus, get_business_message


class BusinessResponse(Response):
    """
    自定义业务响应类

    功能：
    1. 自动处理业务状态码和HTTP状态码的关系
    2. 当业务状态码>=600时，HTTP状态码设为200
    3. 统一响应格式：{"code": xxx, "message": "xxx", "data": xxx}
    """

    def __init__(
        self,
        data: Any = None,
        business_status: Union[int, BusinessStatus] = BusinessStatus.SUCCESS,
        message: str = "",
        http_status: Optional[int] = None,
        headers: Optional[Dict] = None,
        exception: bool = False,
        content_type: str = None,
        **kwargs,
    ):
        """
        初始化业务响应

        Args:
            data: 响应数据
            business_status: 业务状态码
            message: 响应消息，为空时使用业务码对应的默认消息
            http_status: HTTP状态码，为空时根据business_status自动判断
            headers: HTTP响应头
            exception: 是否为异常响应
            content_type: 响应内容类型
            **kwargs: 额外字段，会合并到响应数据中
        """
        # 确保business_status是整数
        if isinstance(business_status, BusinessStatus):
            business_status = business_status.value

        # 获取消息
        if not message:
            status_enum = BusinessStatus(business_status)
            message = get_business_message(status_enum)

        # 构建响应数据
        response_data = {"code": business_status, "message": message, "data": data}

        # 合并额外字段
        if kwargs:
            response_data.update(kwargs)

        # 确定HTTP状态码
        if http_status is not None:
            # 如果明确指定了http_status，使用指定的
            final_http_status = http_status
        elif business_status >= 600:
            # 如果业务码>=600，HTTP状态码设为200
            final_http_status = status.HTTP_200_OK
        elif 400 <= business_status < 600:
            # 如果业务码在400-599之间，使用对应的HTTP状态码
            final_http_status = business_status
        else:
            # 其他情况使用200
            final_http_status = status.HTTP_200_OK

        # 调用父类初始化
        super().__init__(
            data=response_data, status=final_http_status, headers=headers, exception=exception, content_type=content_type
        )


class SuccessResponse(BusinessResponse):
    """成功响应快捷类"""

    def __init__(self, data: Any = None, message: str = "", **kwargs):
        super().__init__(data=data, business_status=BusinessStatus.SUCCESS, message=message or "操作成功", **kwargs)


# 常用快捷函数
def success_response(data: Any = None, message: str = "操作成功", **kwargs) -> BusinessResponse:
    """创建成功响应"""
    return SuccessResponse(data=data, message=message, **kwargs)
