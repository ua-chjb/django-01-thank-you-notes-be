from django.shortcuts import render
from django.views.decorators.csrf import ensure_csrf_cookie
from django.utils import timezone
from datetime import timedelta
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework import status
from .permissions import IsPhoneVerified
from .serializers import (
    UserRegistrationSerializer, 
    CustomTokenObtainPairSerializer, 
    UserUpdateSerializer, 
    UserProfileSerializer, 
    PostSerializer, 
    CommentSerializer,
    NotificationSerializer
)
from .models import Post, CustomUser, Follow, PostLike, Comment, CommentLike, Notification
from .utils import send_sms_verification, create_notification

import logging
logging.getLogger('botocore').setLevel(logging.DEBUG)
logging.getLogger('boto3').setLevel(logging.DEBUG)
logging.getLogger('s3transfer').setLevel(logging.DEBUG)

# verification data
@api_view(["POST"])
def register_user(request):
    ser = UserRegistrationSerializer(
        data=request.data
    )

    if ser.is_valid():
        user = ser.save()

        return Response(status=status.HTTP_201_CREATED)

    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

class CustomTokenObtainPairView(TokenObtainPairView):
    serializer_class = CustomTokenObtainPairSerializer

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def send_phone_verification(request):

    phone_number = request.data.get("phone_number")

    if not phone_number:
        return Response(
            {"error": "Phone number is required"},
            status=status.HTTP_400_BAD_REQUEST
        )

    user = request.user
    user.phone_number = phone_number
    user.save()

    try:
        send_sms_verification(user)
        return Response(
            {"message": "Verification code sent to your phone"},
            status=status.HTTP_200_OK
        )
    except Exception as e:
        return Response(
            {"error": f"Failed to send SMS: {str(e)}"},
            status=status.HTTP_500_INTERNAL_SERVER_ERROR
        )

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def verify_phone(request):

    code = request.data.get("code")

    if not code:
        return Response(
            {"error": "Code is required"},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    user = request.user

    if user.phone_verification_code != code:
        return Response(
            {"error": "Invalid verification code"},
            status=status.HTTP_400_BAD_REQUEST
        )

    if user.code_created_at and timezone.now() > user.code_created_at + timedelta(minutes=10):
        return Response(
            {"error": "Verification code has expired"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    
    user.is_phone_verified = True
    user.phone_verification_code = None
    user.code_created_at = None
    user.save()

    return Response(
        {"message": "Phone verified successfully!"},
        status=status.HTTP_200_OK
    )

# Basic user data
@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_user(request):
    user = request.user
    ser = UserUpdateSerializer(user, data=request.data, partial=True)
    if ser.is_valid():
        ser.save()
        return Response(ser.data)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_current_user(request):
    user = request.user
    ser = UserProfileSerializer(user)
    return Response(ser.data)

# Basic post data
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_post(request):
    user = request.user
    ser = PostSerializer(
        data=request.data,
        context={"request": request}
    )

    if ser.is_valid():
        ser.save(author=user)
        return Response(ser.data)
    
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["PUT"])
@permission_classes([IsAuthenticated])
def update_post(request, pk):
    post = Post.objects.get(id=pk)
    if post.author != request.user:
        return Response({"error": "You can only edit your own posts"}, status=status.HTTP_403_FORBIDDEN)
    ser = PostSerializer(
        post, data=request.data,
        partial=True,
        context={"request": request}
    )
    if ser.is_valid():

        # 🚨 START CRITICAL DEBUGGING BLOCK 🚨
        import sys
        import traceback
        from botocore.exceptions import ClientError
        
        try:
            ser.save() # <-- THE S3 UPLOAD HAPPENS HERE
            return Response(ser.data) # Only return 200 OK on successful save
            
        except ClientError as e:
            # Catches all AWS service errors (400, 403, etc.)
            print(f"!!! S3 CLIENT ERROR: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return Response(
                {"error": "S3 Upload Failed. Check Server Logs for Details."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
            
        except Exception as e:
            # Catches any other Python error during the save process
            print(f"!!! GENERIC PYTHON ERROR DURING UPLOAD: {e}", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            return Response(
                {"error": "Internal Server Error during save."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        # 🚨 END CRITICAL DEBUGGING BLOCK 🚨

        # ser.save()
        # return Response(ser.data)
    
    
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_post(request, pk):
    user = request.user
    post = Post.objects.get(id=pk)
    if post.author != user:
        return Response({"error": "You are not the author of this blog"}, status=status.HTTP_403_FORBIDDEN)
    post.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

# Like and comment data
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def like_unlike_post(request, pk):
    post = Post.objects.filter(id=pk).first()
    like = PostLike.objects.filter(user=request.user, post=post).first()

    if like:
        like.delete()

        Notification.objects.filter(
            recipient=post.author,
            sender=request.user,
            notification_type="like_post",
            post=post
        ).delete()

        return Response({"liked": False}, status=status.HTTP_200_OK)

    else:
        PostLike.objects.create(user=request.user, post=post)

        create_notification(
            recipient=post.author,
            sender=request.user,
            notification_type="like_post",
            post=post
        )

        return Response({"liked": True}, status=status.HTTP_201_CREATED)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def create_comment(request, pk):
    post = Post.objects.filter(id=pk).first()
    ser = CommentSerializer(
        data=request.data,
        context={"request": request}
    )
    if ser.is_valid():
        comment = ser.save(
            author=request.user,
            post=post
        )

        create_notification(
            recipient=post.author,
            sender=request.user,
            notification_type="comment",
            post=post,
            comment=comment
        )

        return Response(ser.data, status=status.HTTP_201_CREATED)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["PUT", "PATCH"])
@permission_classes([IsAuthenticated])
def update_comment(request, pk):
    comment = Comment.objects.filter(id=pk).first()

    if comment.author != request.user:
        return Response({"error": "You can only edit your own comments"}, status=status.HTTP_403_FORBIDDEN)

    ser = CommentSerializer(
        comment,
        data=request.data,
        partial=True,
        context={"request": request}
    )

    if ser.is_valid():
        ser.save()
        return Response(ser.data)
    return Response(ser.errors, status=status.HTTP_400_BAD_REQUEST)

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_comment(request, pk):
    comment = Comment.objects.filter(id=pk).first()

    if comment.author != request.user and comment.post.author!= request.user:
        return Response(
            {"error": "You can only delete your own comments or comments on your posts."},
            status=status.HTTP_403_FORBIDDEN
        )
    comment.delete()
    return Response(status=status.HTTP_204_NO_CONTENT)

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def like_unlike_comment(request, pk):
    comment = Comment.objects.filter(id=pk).first()

    like = CommentLike.objects.filter(
        user=request.user,
        comment=comment
    ).first()

    if like:
        like.delete()

        Notification.objects.filter(
            recipient=comment.author,
            sender=request.user,
            notification_type="like_comment",
            comment=comment
        ).delete()

        return Response({"liked": False}, status=status.HTTP_200_OK)
    else:
        CommentLike.objects.create(user=request.user, comment=comment)

        create_notification(
            recipient=comment.author,
            sender=request.user,
            notification_type="like_comment",
            comment=comment
        )

        return Response({"liked": True}, status=status.HTTP_201_CREATED)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def see_post_likes(request, pk):
    post = Post.objects.filter(id=pk).first()

    likes = PostLike.objects.filter(post=post).select_related("user")

    users = [like.user for like in likes]
    ser = UserProfileSerializer(users, many=True)

    return Response(ser.data)

# Follow data
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def follow_unfollow(request, username):
    user_to_follow = CustomUser.objects.filter(username=username).first()

    if user_to_follow == request.user:
        return Response({"error": "You cannot follow yourself"}, status= status.HTTP_400_BAD_REQUEST)

    follow = Follow.objects.filter(follower=request.user, following=user_to_follow).first()

    if follow:
        follow.delete()

        Notification.objects.filter(
            recipient=user_to_follow,
            sender=request.user,
            notification_type="follow"
        ).delete()

        return Response({"following": False}, status=status.HTTP_200_OK)
    else:
        Follow.objects.create(follower=request.user, following=user_to_follow)

        create_notification(
            recipient=user_to_follow,
            sender=request.user,
            notification_type="follow"
        )

        return Response({"following": True}, status=status.HTTP_201_CREATED)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def see_user_followers(request, username):
    user = CustomUser.objects.filter(username=username).first()
    followers = Follow.objects.filter(following=user).select_related("follower")
    users = [follow.follower for follow in followers]
    ser = UserProfileSerializer(users, many=True)

    return Response({"followers": ser.data})

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def see_user_following(request, username):
    user = CustomUser.objects.filter(username=username).first()
    following = Follow.objects.filter(follower=user).select_related("following")
    users = [follow.following for follow in following]
    ser = UserProfileSerializer(users, many=True)

    return Response({"following": ser.data})

# Notifications data
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def get_notifications(request):
    notifications = Notification.objects.filter(recipient=request.user)
    ser = NotificationSerializer(notifications, many=True, context={"request": request})

    unread_count = notifications.filter(is_read=False).count()

    return Response({
        "notifications": ser.data,
        "unread_count": unread_count
    })

@api_view(["POST"])
@permission_classes([IsAuthenticated])
def mark_notification_read(request, pk):
    
    notification = Notification.objects.filter(id=pk, recipient=request.user).first()

    notification.is_read=True
    notification.save()

    return Response({"message": "Notification marked as read"})

@api_view(["DELETE"])
@permission_classes([IsAuthenticated])
def delete_notification(request, pk):
    notification = Notification.objects.filter(id=pk, recipient=request.user).first()

    notification.delete()

    return Response(status=status.HTTP_204_NO_CONTENT)

# Display data
@api_view(["GET"])
@permission_classes([IsAuthenticated])
def home_feed(request):

    filter_type = request.GET.get("filter", "all")

    if filter_type == "following":
        following_users = Follow.objects.filter(follower=request.user).values_list("following", flat=True)
        posts = Post.objects.filter(author__in=following_users).order_by("-created_at")
    else:
        posts = Post.objects.all().order_by("-created_at")

    ser = PostSerializer(
        posts,
        many=True,
        context={"request": request}
    )
    return Response(ser.data)

@api_view(["GET"])
@permission_classes([IsAuthenticated])
def user_profile(request, username):
    user = CustomUser.objects.filter(username=username).first()
    posts = Post.objects.filter(author=user).order_by("-created_at")

    posts_ser = PostSerializer(
        posts, many=True,
        context={"request": request}
    )

    is_following = Follow.objects.filter(follower=request.user, following=user).exists()
    follower_count = user.followers.count()
    following_count = user.following.count()
    post_count = user.posts.count()

    data = {
        "id": user.id,
        "username": user.username,
        "first_name": user.first_name,
        "profile_picture": user.profile_picture.url if user.profile_picture else None,
        "is_following": is_following,
        "follower_count": follower_count,
        "following_count": following_count,
        "post_count": post_count,
        "is_own_profile": user == request.user,
        "posts": posts_ser.data
    }

    return Response(data)