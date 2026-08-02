from django.contrib import admin
from .models import InstagramProfile, BlogPost, ScanLog
from .scanner_service import InstagramScannerService

@admin.register(InstagramProfile)
class InstagramProfileAdmin(admin.ModelAdmin):
    list_display = ('handle', 'display_name', 'is_active', 'last_scanned_at', 'created_at')
    list_filter = ('is_active', 'last_scanned_at')
    search_fields = ('handle', 'display_name')
    actions = ['trigger_manual_rescan']

    @admin.action(description="Scan / Rescan selected Instagram handles now")
    def trigger_manual_rescan(self, request, queryset):
        scanned_count = 0
        for profile in queryset:
            success, msg, _ = InstagramScannerService.scan_handle(profile.handle)
            if success:
                scanned_count += 1
        self.message_user(request, f"Successfully rescanned {scanned_count} Instagram handles.")


@admin.register(BlogPost)
class BlogPostAdmin(admin.ModelAdmin):
    list_display = ('title', 'profile', 'views_count', 'is_published', 'published_at')
    list_filter = ('is_published', 'profile')
    search_fields = ('title', 'caption', 'profile__handle')
    prepopulated_fields = {'slug': ('title',)}


@admin.register(ScanLog)
class ScanLogAdmin(admin.ModelAdmin):
    list_display = ('handle', 'status', 'posts_found', 'timestamp')
    list_filter = ('status', 'timestamp')
    search_fields = ('handle', 'error_message')
