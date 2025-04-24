# paginations.py
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomPageNumberPagination(PageNumberPagination):
    page_size = 12                      # 默认每页数据量
    max_page_size = 30                  # 允许客户端设置的最大每页数据量
    page_query_param = "pageNum"        # 页码参数名（默认 page）
    page_size_query_param = "pageSize"  # 每页数据量参数名（默认 page_size）

    def get_paginated_response(self, data):
        # 只有分页数据才会返回如下Response格式
        return Response({
            "pagination": {
                "total": self.page.paginator.count,
                "total_pages": self.page.paginator.num_pages,
                "current_page": self.page.number,
                "page_size": self.page.paginator.per_page,
                "next": self.get_next_link(),
                "previous": self.get_previous_link(),
            },
            "data": data  # 将默认的 results 改为 data
        })
