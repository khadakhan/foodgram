from rest_framework.pagination import PageNumberPagination


class UsersPagination(PageNumberPagination):
    """Pagination for users list."""
    page_size = 1
    page_size_query_param = 'limit'
    max_page_size = 10
