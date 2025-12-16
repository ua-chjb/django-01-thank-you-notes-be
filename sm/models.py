from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings
from PIL import Image
from io import BytesIO
from django.core.files.uploadedfile import InMemoryUploadedFile
import sys

def compress_image(image, max_size=(1920, 1080), quality=85):
    img = Image.open(image)

    if img.mode in ("RGBA", "P"):
        img = img.convert("RGB")

    if img.width > max_size[0] or img.height > max_size[1]:
        img.thumbnail(max_size, Image.LANCZOS)
    
    buffer = BytesIO()
    img.save(buffer, format="JPEG", quality=quality, optimize=True)
    buffer.seek(0)

    return InMemoryUploadedFile(
        buffer, "ImageField",
        f"{image.name.rsplit('.', 1)[0]}.jpg",
        "image/jpg",
        sys.getsizeof(buffer),
        None
    )

class CustomUser(AbstractUser):
    bio = models.TextField(blank=True, null=True)
    email = models.EmailField(blank=True)
    profile_picture = models.ImageField(upload_to="profile_pic/", blank=True, null=True)
    is_phone_verified = models.BooleanField(default=False)
    phone_verification_code = models.CharField(max_length=6, blank=True, null=True)
    code_created_at = models.DateTimeField(blank=True, null=True)

    REQUIRED_FIELDS = ["first_name", "last_name"]

    def save(self, *args, **kwargs):
        if self.profile_picture:
            if self.pk:
                old_instance = CustomUser.objects.filter(pk=self.pk).first()
                is_new_image = old_instance is None or old_instance.profile_picture != self.profile_picture
            else:
                is_new_image = True

            if is_new_image:
                self.profile_picture = compress_image(self.profile_picture, max_size=(800, 800))

        super().save(*args, **kwargs)

    def __str__(self):
        return self.username

class Follow(models.Model):

    follower = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="following")
    following = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="followers")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("follower", "following")

    def __str__(self):
        return f"{self.follower.username} follows {self.following.username}"


class Post(models.Model):

    status_enum = [
        ("not_started", "Not started"),
        ("drafted", "Drafted"),
        ("sent", "Sent")
    ]

    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="posts")
    what = models.CharField(max_length=255, null=False)
    who  = models.CharField(max_length=255, null=False)
    note = models.CharField(max_length=1000, null=True, blank=True)
    gift_image = models.ImageField(upload_to="blog_img/", blank=True, null=True)
    status = models.CharField(max_length=20, choices=status_enum, default="not_started")
    created_at = models.DateTimeField(auto_now_add=True, null=False)
    updated_at = models.DateTimeField(auto_now=True, null=False)

    class Meta:
        ordering = ["-created_at"]

    def save(self, *args, **kwargs):
        if self.gift_image:
            if self.pk:
                old_instance = Post.objects.filter(pk=self.pk).first()
                is_new_image = old_instance is None or old_instance.gift_image != self.gift_image
            
            else:
                is_new_image = True

            if is_new_image:
                self.gift_image = compress_image(self.gift_image)

        super().save(*args, **kwargs)

    def __str__(self):
        return self.what
    

class PostLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "post")

class Comment(models.Model):
    author = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_comments")
    post = models.ForeignKey(Post, on_delete=models.CASCADE, related_name="comments")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

class CommentLike(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    comment = models.ForeignKey(Comment, on_delete=models.CASCADE, related_name="likes")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("user", "comment")


class Notification(models.Model):
    notifs_enum = [
        ("like_post", "Like on post"),
        ("like_comment", "like on coment"),
        ("comment", "Comment on post"),
        ("follow", "New follower")
    ]

    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="notifications")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="sent_notifications")
    notification_type = models.CharField(max_length=20, choices=notifs_enum)

    post = models.ForeignKey("Post", on_delete=models.CASCADE, null=True, blank=True)
    comment = models.ForeignKey("Comment", on_delete=models.CASCADE, null=True, blank=True)

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["recipient", "is_read"]),
        ]

    def __str__(self):
        return f"{self.sender.username} -> {self.recipient.username}: {self.notification_type}"