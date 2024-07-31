from rest_framework.permissions import BasePermission


class IsAuthor(BasePermission):

    def has_object_permission(self, request, view, obj):
        return (obj.author == request.user)


# class IsAuthenticated(BasePermission):

#     def has_permission(self, request, view):
#         return request.user.is_authenticated


# class AllowAny(BasePermission):

#     def has_permission(self, request, view):
#         return True
