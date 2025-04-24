from django.db import connection
from rest_framework.viewsets import ModelViewSet, ViewSet
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError, APIException
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework import status


from ..renderers import CustomJSONRenderer
from ..paginations import CustomPageNumberPagination
from ..permissions import HasAccessKey


class ApiModelView(ViewSet):
    """
    直接写sql返回结果，切记增加权限控制，该接口不要轻易暴露
    ViewSet的CRUD需要自己实现，ModelViewSet自带5个方法
    """
    permission_classes = [HasAccessKey, IsAdminUser]
    pagination_class = CustomPageNumberPagination
    renderer_classes = [CustomJSONRenderer]

    def list(self, request, *args, **kwargs):

        # 如果有多个数据库，需要指定简称 with connections["my_db_alias"].cursor() as cursor:
        with connection.cursor() as cursor:
            # cursor.execute("UPDATE bar SET foo = 1 WHERE baz = %s", [self.baz])
            # 只能执行一条sql，否则报错 sqlite3.Warning: You can only execute one statement at a time.

            # sqlite3
            # sql = "SELECT name as table_name FROM sqlite_master WHERE type='table'"

            # mysql
            sql = "select table_name from information_schema.tables t where t.table_schema='wp' and t.table_name like 'wallpaper_%';"

            cursor.execute(sql)
            
            # 获取列名（首行元数据）
            columns = [str(col[0]).lower() for col in cursor.description]
            # 将游标结果转换为字典列表
            data = [dict(zip(columns, row)) for row in cursor.fetchall() if str(row[0]).lower().startswith("wallpaper_")]

            # 如果启用分页器，则返回分页信息
            # if ApiModelView.pagination_class is not None:
            #     paginator = self.pagination_class()
            #     paginated_data = paginator.paginate_queryset(data, request)
            #     return paginator.get_paginated_response(paginated_data)

            # 直接返回数据，不使用分页
            return Response(data)

    # (?P<path_param>.+)     包括/，可以是 custom/abc
    # (?P<path_param>[^/]+)  不包括/，只能是 abc 或者 def，如果存在/会报url404没有找到的错误
    @action(detail=False, methods=['get'], url_path='(?P<path_param>[^/]+)')
    def dynamic_route(self, request, path_param=None):
        """动态路由，路由即为表名，只能一级url，如果包含/需要进行参数校验"""
        # return Response({
        #     "full_path": request.path,      # 完整路径（如 /wallpaper/api/table/wall/）
        #     "param": path_param,            # 动态参数（如 wall, 多个路径为wall/abc）
        #     "method": request.method        # 请求方法（如 GET）
        # })

        table = path_param
        try:
            with connection.cursor() as cursor:
                # cursor.execute("UPDATE bar SET foo = 1 WHERE baz = %s", [self.baz])
                # 只能执行一条sql，否则报错 sqlite3.Warning: You can only execute one statement at a time.
                cursor.execute(f"select * from wallpaper_{table};")
                # 获取列名（首行元数据）
                columns = [col[0] for col in cursor.description]
                # 将游标结果转换为字典列表
                data = [dict(zip(columns, row)) for row in cursor.fetchall()]

                # 如果启用分页器，则返回分页信息
                if ApiModelView.pagination_class is not None:
                    paginator = self.pagination_class()
                    paginated_data = paginator.paginate_queryset(data, request)
                    return paginator.get_paginated_response(paginated_data)

                return Response(data)
            
        except Exception as e:
            # 异常处理，比如表不存在，传入的sql存在问题等
            # e.args / str(e) / repr(e)
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
