from rest_framework.permissions import BasePermission

# class IsEmailVerified(BasePermission):

#     message = "You must verify your email before performing this action."

#     def has_permission(self, request, view):

#         return (
#             request.user and
#             request.user.is_authenticated and
#             request.user.is_email_verified
#         )

class IsPhoneVerified(BasePermission):

    message = "You must verify your phone number before performing this action"

    def has_permission(self, request, view):
        return (
            request.user and
            request.user.is_authenticated and
            request.user.is_phone_verified
        )