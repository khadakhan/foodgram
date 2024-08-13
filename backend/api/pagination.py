from rest_framework.pagination import PageNumberPagination

from api.const import RECIPES_LIMIT


class UsersRecipesPagination(PageNumberPagination):
    """Pagination for users and recipes list."""

    page_size = RECIPES_LIMIT
    page_size_query_param = 'limit'
