from django.db import models
from django.utils import timezone
import os

class InstagramProfile(models.Model):
    handle = models.CharField(max_length=100, unique=True, help_text="Instagram handle without @ symbol")
    display_name = models.CharField(max_length=150, blank=True)
    bio = models.TextField(blank=True)
    profile_pic_url = models.URLField(blank=True)
    is_active = models.BooleanField(default=True)
    last_scanned_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"@{self.handle}"

    class Meta:
        ordering = ['-last_scanned_at', 'handle']


class BlogPost(models.Model):
    profile = models.ForeignKey(InstagramProfile, on_delete=models.CASCADE, related_name='posts')
    title = models.CharField(max_length=255)
    slug = models.SlugField(max_length=255, unique=True)
    caption = models.TextField(blank=True)
    article_body = models.TextField(help_text="Generated editorial blog article content")
    ig_post_id = models.CharField(max_length=100, unique=True)
    ig_url = models.URLField(blank=True)
    
    # Video & Media
    video_url = models.URLField(blank=True, max_length=500, help_text="Hosted or source video URL")
    thumbnail_url = models.URLField(blank=True, max_length=500)
    views_count = models.PositiveIntegerField(default=0)
    likes_count = models.PositiveIntegerField(default=0)
    comments_count = models.PositiveIntegerField(default=0)
    
    is_published = models.BooleanField(default=True)
    published_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} (@{self.profile.handle})"

    @property
    def get_video_url(self):
        if not self.video_url:
            return ""
        if 'r2.cloudflarestorage.com' in self.video_url and 'X-Amz-Signature' not in self.video_url:
            from django.core.files.storage import default_storage
            key_index = self.video_url.find('/videos/')
            if key_index != -1:
                key = self.video_url[key_index+1:]
                try:
                    return default_storage.url(key)
                except Exception:
                    pass
        return self.video_url

    @property
    def get_thumbnail_url(self):
        if not self.thumbnail_url:
            return ""
        if 'r2.cloudflarestorage.com' in self.thumbnail_url and 'X-Amz-Signature' not in self.thumbnail_url:
            from django.core.files.storage import default_storage
            key_index = self.thumbnail_url.find('/thumbnails/')
            if key_index != -1:
                key = self.thumbnail_url[key_index+1:]
                try:
                    return default_storage.url(key)
                except Exception:
                    pass
        return self.thumbnail_url

    class Meta:
        ordering = ['-published_at']



class ScanLog(models.Model):
    handle = models.CharField(max_length=100)
    status = models.CharField(max_length=50, choices=[('SUCCESS', 'Success'), ('FAILED', 'Failed')])
    posts_found = models.IntegerField(default=0)
    error_message = models.TextField(blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Scan @{self.handle} - {self.status} at {self.timestamp.strftime('%Y-%m-%d %H:%M')}"
