from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import CustomUser, Follow, Post, Comment, Notification


class UserRegistrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "password"
        ]
        extra_kwargs = {
            "password": {"write_only": True}
        }

    def create(self, validated_data):
        username = validated_data["username"]
        first_name = validated_data["first_name"]
        last_name = validated_data["last_name"]
        password = validated_data["password"]
    
        user = get_user_model()
        new_user = user.objects.create(
            username=username,
            email="",
            first_name=first_name,
            last_name=last_name
        )

        new_user.set_password(password)
        new_user.save()

        return new_user


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    def validate(self, attrs):

        data = super().validate(attrs)

        return data

    @classmethod
    def get_token(cls, user):

        token = super().get_token(user)
        return token

class UserProfileSerializer(serializers.ModelSerializer):
    followers_count = serializers.SerializerMethodField()
    following_count = serializers.SerializerMethodField()
    is_following = serializers.SerializerMethodField()


    class Meta:
        model = CustomUser
        fields = [
            "id",
            "username",
            "first_name",
            "last_name",
            "profile_picture",
            "is_phone_verified",
            "followers_count",
            "following_count",
            "is_following"
        ]
    
    def get_followers_count(self, obj):
        return obj.followers.count()

    def get_following_count(self, obj):
        return obj.following.count()

    def get_is_following(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return Follow.objects.filter(
                follower=request.user,
                following=obj
            ).exists()
        return False

class UserUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()

        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "password",
            "bio",
            "profile_picture"
        ]
        extra_kwargs = {
            "username": {"required": False},
            "password": {"required": False},
            "email": {"required": False},
            "first_name": {"required": False},
            "last_name": {"required": False},
            "bio": {"required": False},
            "profile_picture": {"required": False}
        }

class SimpleAutoSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "username",
            "first_name",
            "last_name"
        ]

class CommentSerializer(serializers.ModelSerializer):
    author = UserProfileSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()

    class Meta:
        model = Comment
        fields = [
            "id",
            "author",
            "post",
            "text",
            "like_count",
            "is_liked",
            "created_at",
            "updated_at",
        ]
        read_only_fields = [
            "author",
            "post",
            "created_at",
            "updated_at"
        ]
    
    def get_like_count(self, obj):
        return obj.likes.count()
    
    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
class PostSerializer(serializers.ModelSerializer):

    author = UserProfileSerializer(read_only=True)
    like_count = serializers.SerializerMethodField()
    comment_count = serializers.SerializerMethodField()
    is_liked = serializers.SerializerMethodField()
    comments = CommentSerializer(many=True, read_only=True)
    # note = serializers.SerializerMethodField()

    class Meta:
        model = Post
        
        fields = [
            "id",
            "author",
            "what",
            "who",
            "note",
            "gift_image",
            "status",
            "like_count",
            "comments",
            "comment_count",
            "is_liked",
            "created_at",
            "updated_at"
        ]
        read_only_fields = [
            "author",
            "created_at",
            "updated_at"
        ]
    
    def get_like_count(self, obj):
        return obj.likes.count()
    
    def get_comment_count(self, obj):
        return obj.comments.count()
    
    def get_is_liked(self, obj):
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            return obj.likes.filter(user=request.user).exists()
        return False
    
    def get_note(self, obj):
        request = self.context.get("request")
        if request and request.user == obj.author:
            return obj.note
        return None
    
class NotificationSerializer(serializers.ModelSerializer):
    sender = UserProfileSerializer(read_only=True)
    post_preview = serializers.SerializerMethodField()

    class Meta:
        model = Notification
        fields = [
            "id",
            "sender",
            "notification_type",
            "post",
            "comment",
            "post_preview",
            "is_read",
            "created_at"
        ]
    
    def get_post_preview(self, obj):

        if obj.post:
            return {
                "id": obj.post.id,
                "what": obj.post.what
            }
        return None