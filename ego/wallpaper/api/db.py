from django.db import connection
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework.permissions import IsAdminUser
from rest_framework import status


from ..renderers import CustomJSONRenderer
from ..paginations import CustomPageNumberPagination
from ..permissions import IsSuperUser, HasAccessKey


class ApiModelView(ViewSet):
    """
    直接写sql返回结果，切记增加权限控制，该接口不要轻易暴露
    ViewSet的CRUD需要自己实现，ModelViewSet自带5个方法
    """

    # 同时支持 JWT、Session、Basic 认证
    # authentication_classes = [
    #     'rest_framework_simplejwt.authentication.JWTAuthentication',
    #     SessionAuthentication,
    #     BasicAuthentication,
    # ]

    permission_classes = [HasAccessKey, IsAdminUser, IsSuperUser]
    pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def create(self, request, *args, **kwargs):
        # 循环参数校验方式，校验全部必填项参数
        required_fields = ['sql']
        missing_fields = [k for k in required_fields if k not in request.data]
        if missing_fields:
            return Response({k: f'{k} 是必填项' for k in missing_fields}, status=status.HTTP_400_BAD_REQUEST)

        sql = request.data.get("sql")

        if not sql or not str(sql).lower().startswith("select "):
            # 如果写成detail也会将该信息放入到message字段中
            # Response({"detail": "输入的sql必须是 select 开始的查询语句"}, status=status.HTTP_400_BAD_REQUEST)
            return Response({"error": "输入的sql必须是 select 开始的查询语句"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # 如果有多个数据库，需要指定简称 with connections["my_db_alias"].cursor() as cursor:
            with connection.cursor() as cursor:
                # cursor.execute("UPDATE bar SET foo = 1 WHERE baz = %s", [self.baz])
                # 只能执行一条sql，否则报错 sqlite3.Warning: You can only execute one statement at a time.
                cursor.execute(sql)
                # 获取列名（首行元数据）
                columns = [col[0] for col in cursor.description]
                # 将游标结果转换为字典列表
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]

                # 返回分页信息
                paginator = self.pagination_class()
                paginated_data = paginator.paginate_queryset(data, request)
                return paginator.get_paginated_response(paginated_data)
            
        except Exception as e:
            # 异常处理，比如表不存在，传入的sql存在问题等
            # e.args / str(e) / repr(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
