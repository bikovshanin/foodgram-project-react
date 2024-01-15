from rest_framework.pagination import PageNumberPagination


class LimitPaginator(PageNumberPagination):
    """
    Лимит пагинации рецептов по переданному в запросе параметру.
    """
    page_size = 6
    page_size_query_param = 'limit'
