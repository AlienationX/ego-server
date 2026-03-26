from enum import IntEnum

# ==================== http 标准状态码定义 ====================
# 1xx 信息响应
# 100 Continue(继续)
# 服务器已收到请求头，客户端应继续发送请求体。
# 101 Switching Protocols(切换协议)
# 服务器根据客户端请求切换通信协议(如切换到 WebSocket)。
# 2xx 成功
# 200 OK(成功)
# 请求成功，响应中包含请求的数据。
# 201 Created(已创建)
# 请求成功，并在服务器创建了新资源(如 POST 新建数据)。
# 204 No Content(无内容)
# 请求成功，但响应中无返回内容(常见于 DELETE 或 PUT 请求)。
# 3xx 重定向
# 301 Moved Permanently(永久重定向)
# 请求的资源已永久移至新 URL ，应使用新 URL 访问。
# 302 Found(临时重定向)
# 请求的资源临时移至新 URL ，后续仍建议用原 URL。
# 304 Not Modified(未修改)
# 资源未修改，客户端可使用本地缓存版本(常用于缓存验证)。
# 4xx 客户端错误
# 400 Bad Request(错误请求)
# 请求语法错误，服务器无法理解。
# 401 Unauthorized(未授权)
# 请求需要身份验证(如未登录或凭据无效)。
# 403 Forbidden(禁止访问)
# 服务器理解请求，但拒绝执行(权限不足)。
# 404 Not Found(未找到)
# 请求的资源在服务器上不存在。
# 405 Method Not Allowed(方法不允许)
# 请求的 HTTP 方法不被该资源支持(如用 POST 访问只接受 GET 的接口)。
# 408 Request Timeout(请求超时)
# 服务器等待请求超时，客户端需重试。
# 429 Too Many Requests(请求过多)
# 客户端发送的请求频率超出限制(防滥用机制)。
# 5xx 服务器错误
# 500 Internal Server Error(内部服务器错误)
# 服务器内部错误，无法完成请求(常见于代码异常)。
# 502 Bad Gateway(错误网关)
# 作为网关或代理的服务器，从上游服务器接收到无效响应。
# 503 Service Unavailable(服务不可用)
# 服务器暂时过载或维护中，无法处理请求。
# 504 Gateway Timeout(网关超时)
# 网关或代理服务器未能及时从上游服务器获得响应。


class BusinessStatus(IntEnum):
    """业务状态码定义"""

    # 成功
    SUCCESS = 0

    # 系统错误 (1xxx)
    SYSTEM_ERROR = 1000
    DATABASE_ERROR = 1001
    CACHE_ERROR = 1002
    REDIS_ERROR = 1003
    RABBITMQ_ERROR = 1004

    # 参数错误 (2xxx)
    PARAM_ERROR = 2000
    PARAM_REQUIRED = 2001
    PARAM_INVALID = 2002
    PARAM_FORMAT_ERROR = 2003

    # 认证授权 (3xxx)
    AUTH_ERROR = 3000
    TOKEN_EXPIRED = 3001
    TOKEN_INVALID = 3002
    PERMISSION_DENIED = 3003
    LOGIN_REQUIRED = 3004
    ACCOUNT_DISABLED = 3005

    # 资源操作 (4xxx)
    RESOURCE_NOT_FOUND = 4000
    RESOURCE_EXISTS = 4001
    RESOURCE_CREATE_FAILED = 4002
    RESOURCE_UPDATE_FAILED = 4003
    RESOURCE_DELETE_FAILED = 4004

    # 业务逻辑 (5xxx)
    BUSINESS_ERROR = 5000
    INSUFFICIENT_BALANCE = 5001
    INSUFFICIENT_STOCK = 5002
    ORDER_CREATE_FAILED = 5003
    PAYMENT_FAILED = 5004
    USER_FROZEN = 5005

    # 第三方服务 (6xxx)
    THIRD_PARTY_ERROR = 6000
    WEIXIN_ERROR = 6001
    ALIPAY_ERROR = 6002
    SMS_ERROR = 6003
    EMAIL_ERROR = 6004

    # 文件操作 (7xxx)
    FILE_ERROR = 7000
    FILE_TOO_LARGE = 7001
    FILE_TYPE_INVALID = 7002
    FILE_UPLOAD_FAILED = 7003
    FILE_NOT_FOUND = 7004


# 业务码对应的消息映射
BUSINESS_MESSAGES = {
    # 成功
    BusinessStatus.SUCCESS: "success",
    # 系统错误
    BusinessStatus.SYSTEM_ERROR: "系统错误",
    BusinessStatus.DATABASE_ERROR: "数据库错误",
    BusinessStatus.CACHE_ERROR: "缓存错误",
    BusinessStatus.REDIS_ERROR: "Redis错误",
    BusinessStatus.RABBITMQ_ERROR: "消息队列错误",
    # 参数错误
    BusinessStatus.PARAM_ERROR: "参数错误",
    BusinessStatus.PARAM_REQUIRED: "参数缺失",
    BusinessStatus.PARAM_INVALID: "参数无效",
    BusinessStatus.PARAM_FORMAT_ERROR: "参数格式错误",
    # 认证授权
    BusinessStatus.AUTH_ERROR: "认证失败",
    BusinessStatus.TOKEN_EXPIRED: "Token已过期",
    BusinessStatus.TOKEN_INVALID: "Token无效",
    BusinessStatus.PERMISSION_DENIED: "权限不足",
    BusinessStatus.LOGIN_REQUIRED: "请先登录",
    BusinessStatus.ACCOUNT_DISABLED: "账户已被禁用",
    # 资源操作
    BusinessStatus.RESOURCE_NOT_FOUND: "资源不存在",
    BusinessStatus.RESOURCE_EXISTS: "资源已存在",
    BusinessStatus.RESOURCE_CREATE_FAILED: "资源创建失败",
    BusinessStatus.RESOURCE_UPDATE_FAILED: "资源更新失败",
    BusinessStatus.RESOURCE_DELETE_FAILED: "资源删除失败",
    # 业务逻辑
    BusinessStatus.BUSINESS_ERROR: "业务错误",
    BusinessStatus.INSUFFICIENT_BALANCE: "余额不足",
    BusinessStatus.INSUFFICIENT_STOCK: "库存不足",
    BusinessStatus.ORDER_CREATE_FAILED: "订单创建失败",
    BusinessStatus.PAYMENT_FAILED: "支付失败",
    BusinessStatus.USER_FROZEN: "用户已被冻结",
    # 第三方服务
    BusinessStatus.THIRD_PARTY_ERROR: "第三方服务错误",
    BusinessStatus.WEIXIN_ERROR: "微信服务错误",
    BusinessStatus.ALIPAY_ERROR: "支付宝服务错误",
    BusinessStatus.SMS_ERROR: "短信发送失败",
    BusinessStatus.EMAIL_ERROR: "邮件发送失败",
    # 文件操作
    BusinessStatus.FILE_ERROR: "文件操作错误",
    BusinessStatus.FILE_TOO_LARGE: "文件过大",
    BusinessStatus.FILE_TYPE_INVALID: "文件类型不支持",
    BusinessStatus.FILE_UPLOAD_FAILED: "文件上传失败",
    BusinessStatus.FILE_NOT_FOUND: "文件不存在",
}


def get_business_message(status: BusinessStatus) -> str:
    """获取业务状态码对应的消息"""
    return BUSINESS_MESSAGES.get(status, "未知错误")
