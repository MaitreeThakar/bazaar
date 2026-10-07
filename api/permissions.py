from rest_framework import permissions

class IsSupplierOrReadOnly(permissions.BasePermission):
    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True
        return obj.supplier == request.user

class IsCustomerOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        if request.method in  permissions.SAFE_METHODS:
            return True
        return (request.user.is_authenticated and request.user.account.role == 'customer')
    def has_object_permission(self, request, view, obj):

        if request.method in permissions.SAFE_METHODS:
            return True
        return (request.user.account.role == 'customer' and obj.customer == request.user)