from rest_framework import permissions


class AuthorOrReadOnly(permissions.BasePermission):
    """
    Ограничение доступа к редактированию рецептов.
    Только авторы постов и комментариев могут редактировать их и удалять.
    """

    def has_object_permission(self, request, view, obj):
        return (
            request.user == obj.author
            or request.method in permissions.SAFE_METHODS
        )
