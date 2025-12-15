from django.urls import path
from django.views.generic.base import RedirectView
from django.contrib.staticfiles.storage import staticfiles_storage
from . import views

favicon_view = RedirectView.as_view(url=staticfiles_storage.url("favicon.ico"), permanent=True)

urlpatterns = [
    # user management
    path("", RedirectView.as_view(url="/register_user/", permanent=False)),
    path("register_user/", views.register_user, name="register_user"),
    path("update_user/", views.update_user, name="update_user"),
    path("my_profile/", views.get_current_user, name="profile"),
    path("profile/<str:username>/", views.user_profile, name="other_user_profile"),
    path("verify_phone/send/", views.send_phone_verification, name="send_phone_verification"),
    path("verify_phone/confirm/", views.verify_phone, name="verify_phone"),

    # posts
    path("home/", views.home_feed, name="home"),
    path("posts/create/", views.create_post, name="create_post"),
    path("posts/update/<int:pk>/", views.update_post, name="update_post"),
    path("posts/delete/<int:pk>/", views.delete_post, name="delete_post"),

    # likes and comments
    path("posts/like/<int:pk>/", views.like_unlike_post, name="like_unlike_post"),
    path("posts/<int:pk>/likes/", views.see_post_likes, name="see_post_likes"),
    path("posts/<int:pk>/comments/create/", views.create_comment, name="create_comment"),
    path("comments/<int:pk>/update/", views.update_comment, name="update_comment"),
    path("comments/<int:pk>/delete/", views.delete_comment, name="delete_comment"),
    path("comments/<int:pk>/like/", views.like_unlike_comment, name="like_unlike_comment"),

    # follow
    path("users/<str:username>/follow/", views.follow_unfollow, name="follow_unfollow"),
    path("users/<str:username>/followers/", views.see_user_followers, name="see_user_followers"),
    path("users/<str:username>/following/", views.see_user_following, name="see_user_following"),

    # notifications
    path("notifications/", views.get_notifications, name="get_notifications"),
    path("notifications/<int:pk>/read/", views.mark_notification_read, name="mark_notification_read"),
    path("notifications/<int:pk>/delete/", views.delete_notification, name="delete_notification"),

    # favicon error
    path("favicon/ico", favicon_view, name="favicon")
]