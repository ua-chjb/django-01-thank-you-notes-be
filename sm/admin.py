from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import CustomUser, Post, Comment, PostLike, CommentLike, Follow, Notification

# Register your models here.

@admin.register(CustomUser)
class CustomUserAdmin(UserAdmin):
    list_display = ("username", "first_name", "last_name", "bio", "profile_picture", "is_phone_verified", "is_staff")
    list_filter = ("is_phone_verified", "is_active", "is_staff")

@admin.register(Post)
class PostAdmin(admin.ModelAdmin):
    list_display = ("id", "author", "status", "what", "who", "note", "gift_image", "created_at", "updated_at")
    list_filter = ("author", "status", "created_at")
    search_fields = ("what", "who", "note")

@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display= ("id", "author", "post", "text", "created_at")
    list_filter = ("author", "created_at")
    search_fields = ("text",)

@admin.register(PostLike)
class PostLikeAdin(admin.ModelAdmin):
    list_display = ("id", "user", "post", "created_at")
    list_filter = ("user", "created_at")

@admin.register(CommentLike)
class CommentLikeAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "comment", "created_at")
    list_filter = ("user", "created_at")

@admin.register(Follow)
class FollowAdmin(admin.ModelAdmin):
    list_display = ("id", "follower", "following", "created_at")
    list_filter = ("created_at",)
    search_fields = ("follower__username", "following__username")

@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "recipient", "sender", "notification_type", "is_read", "created_at")
    list_filter = ("notification_type", "is_read", "created_at")
    search_fields = ("recipient__username", "sender__username")