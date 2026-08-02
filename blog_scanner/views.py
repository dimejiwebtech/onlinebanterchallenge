from django.shortcuts import render, get_object_or_404, redirect
from django.contrib import messages
from django.db.models import Q
from .models import InstagramProfile, BlogPost, ScanLog
from .scanner_service import InstagramScannerService

def home_view(request):
    """
    Homepage: Display handle scanner search bar, active profiles, and aggregated editorial post grid.
    """
    query = request.GET.get('q', '').strip()
    posts = BlogPost.objects.filter(is_published=True)

    if query:
        posts = posts.filter(
            Q(title__icontains=query) | 
            Q(caption__icontains=query) | 
            Q(profile__handle__icontains=query)
        )

    recent_profiles = InstagramProfile.objects.all()[:12]
    featured_post = posts.first()
    grid_posts = posts[1:] if featured_post else []

    context = {
        'featured_post': featured_post,
        'grid_posts': grid_posts,
        'recent_profiles': recent_profiles,
        'query': query,
        'total_posts_count': BlogPost.objects.count(),
        'total_handles_count': InstagramProfile.objects.count()
    }
    return render(request, 'blog/home.html', context)


def scan_view(request, handle=None):
    """
    On-the-fly Instagram handle scanner view.
    Can be called via POST form or directly via GET URL `/scan/<handle>/`.
    """
    if request.method == 'POST':
        raw_handle = request.POST.get('handle', '')
    else:
        raw_handle = handle

    if not raw_handle:
        messages.error(request, "Please enter a valid Instagram handle.")
        return redirect('home')

    success, message, new_posts = InstagramScannerService.scan_handle(raw_handle)
    if success:
        messages.success(request, message)
        clean_handle = raw_handle.strip().lstrip('@').lower()
        return redirect('profile_detail', handle=clean_handle)
    else:
        messages.error(request, message)
        return redirect('home')


def profile_detail_view(request, handle):
    """
    View all video blog posts for a specific Instagram handle.
    """
    clean_handle = handle.strip().lstrip('@').lower()
    profile = get_object_or_404(InstagramProfile, handle=clean_handle)
    posts = profile.posts.filter(is_published=True)

    context = {
        'profile': profile,
        'posts': posts,
        'post_count': posts.count()
    }
    return render(request, 'blog/profile.html', context)


def post_detail_view(request, slug):
    """
    Individual video blog article page with custom video player and reader metrics.
    """
    post = get_object_or_404(BlogPost, slug=slug, is_published=True)
    
    # Increment view count
    post.views_count += 1
    post.save(update_fields=['views_count'])

    related_posts = BlogPost.objects.filter(is_published=True).exclude(id=post.id)[:3]

    context = {
        'post': post,
        'related_posts': related_posts
    }
    return render(request, 'blog/detail.html', context)


def admin_dashboard_view(request):
    """
    Quick dashboard preview for viewing scan logs and managed handles.
    """
    profiles = InstagramProfile.objects.all()
    logs = ScanLog.objects.all().order_by('-timestamp')[:20]

    context = {
        'profiles': profiles,
        'logs': logs
    }
    return render(request, 'blog/admin_dashboard.html', context)
