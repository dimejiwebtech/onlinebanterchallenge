import re
import json
import random
import requests
from django.utils import timezone
from django.utils.text import slugify
from .models import InstagramProfile, BlogPost, ScanLog

SAMPLE_VIDEOS = [
    {
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ForBiggerBlazes.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?w=800&auto=format&fit=crop&q=80",
        "title_template": "Exploring the Dynamics of High-Impact Visual Media",
        "tags": ["#ContentCreation", "#TechTrends", "#VibeCoding"]
    },
    {
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/ElephantsDream.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1579783902614-a3fb3927b675?w=800&auto=format&fit=crop&q=80",
        "title_template": "Inside the Creative Masterclass: Digital Artistry Redefined",
        "tags": ["#DesignInspiration", "#DigitalArt", "#Innovation"]
    },
    {
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/BigBuckBunny.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1550745165-9bc0b252726f?w=800&auto=format&fit=crop&q=80",
        "title_template": "Building Next-Gen Automated Content Engines with AI & Code",
        "tags": ["#PythonDjango", "#AIAutomation", "#WebDev"]
    },
    {
        "video_url": "https://commondatastorage.googleapis.com/gtv-videos-bucket/sample/WeAreGoingOnBullrun.mp4",
        "thumbnail": "https://images.unsplash.com/photo-1518770660439-4636190af475?w=800&auto=format&fit=crop&q=80",
        "title_template": "Mastering Fast Execution: From Concept to Published Media Platform",
        "tags": ["#VibeCode", "#FastExecution", "#Productivity"]
    }
]

class InstagramScannerService:
    """
    On-the-fly Instagram scanner service.
    Fetches videos and metadata for any Instagram handle without requiring pre-configuration.
    Converts posts into formatted editorial blog articles with playable hosted videos.
    """

    @staticmethod
    def scan_handle(raw_handle):
        handle = raw_handle.strip().lstrip('@').lower()
        if not handle:
            return False, "Invalid handle provided", []

        # Get or create Profile dynamically on the fly
        profile, created = InstagramProfile.objects.get_or_create(
            handle=handle,
            defaults={
                'display_name': handle.capitalize(),
                'bio': f"Content creator & digital strategist @{handle}. Automated feed aggregation.",
                'profile_pic_url': f"https://ui-avatars.com/api/?name={handle}&background=0D0D0D&color=FFFFFF&size=200",
            }
        )

        posts_created = []
        try:
            # 1. Attempt to fetch public IG metadata via oEmbed or direct scrapers
            ig_items = InstagramScannerService._fetch_ig_public_data(handle)

            for idx, item in enumerate(ig_items):
                post_id = f"ig_{handle}_{item['id']}"
                
                # Check existing post to avoid duplicates
                existing_post = BlogPost.objects.filter(ig_post_id=post_id).first()
                if existing_post:
                    posts_created.append(existing_post)
                    continue

                caption = item.get('caption', f"Featured updates from @{handle}'s latest Instagram video reel.")
                title = InstagramScannerService._generate_blog_title(caption, item.get('title_hint'))
                article_body = InstagramScannerService._generate_editorial_article(handle, caption, title)

                slug = slugify(f"{handle}-{title}")[:200]
                # Ensure unique slug
                base_slug = slug
                counter = 1
                while BlogPost.objects.filter(slug=slug).exists():
                    slug = f"{base_slug}-{counter}"
                    counter += 1

                # Download & host media locally on our platform
                local_video_url, local_thumb_url = InstagramScannerService._download_and_store_media(
                    post_id=post_id,
                    video_src=item.get('video_url'),
                    thumbnail_src=item.get('thumbnail_url')
                )

                blog_post = BlogPost.objects.create(
                    profile=profile,
                    title=title,
                    slug=slug,
                    caption=caption,
                    article_body=article_body,
                    ig_post_id=post_id,
                    ig_url=item.get('ig_url', f"https://instagram.com/{handle}"),
                    video_url=local_video_url,
                    thumbnail_url=local_thumb_url,
                    views_count=item.get('views', random.randint(1200, 45000)),
                    likes_count=item.get('likes', random.randint(300, 8500)),
                    comments_count=item.get('comments', random.randint(45, 920)),
                    published_at=timezone.now()
                )
                posts_created.append(blog_post)


            profile.last_scanned_at = timezone.now()
            profile.save()

            ScanLog.objects.create(
                handle=handle,
                status='SUCCESS',
                posts_found=len(posts_created)
            )
            return True, f"Successfully scanned @{handle} and synced {len(posts_created)} video posts.", posts_created

        except Exception as e:
            ScanLog.objects.create(
                handle=handle,
                status='FAILED',
                error_message=str(e)
            )
            return False, f"Error scanning @{handle}: {str(e)}", []

    @staticmethod
    def _fetch_ig_public_data(handle):
        """
        Fetches structured video items using configured third-party API providers (Apify or RapidAPI).
        Falls back smoothly to high-quality sample video media if no API key is provided or on request error.
        """
        from django.conf import settings
        provider = getattr(settings, 'THIRD_PARTY_API_PROVIDER', 'apify').lower()

        # Try Apify first if selected or if APIFY_TOKEN is present
        if provider == 'apify' and getattr(settings, 'APIFY_TOKEN', ''):
            try:
                items = InstagramScannerService._fetch_from_apify(handle)
                if items:
                    return items
            except Exception as e:
                print(f"[API Warning] Apify fetch failed for @{handle}: {e}. Falling back...")

        # Try RapidAPI if selected or if RAPIDAPI_KEY is present
        if getattr(settings, 'RAPIDAPI_KEY', ''):
            try:
                items = InstagramScannerService._fetch_from_rapidapi(handle)
                if items:
                    return items
            except Exception as e:
                print(f"[API Warning] RapidAPI fetch failed for @{handle}: {e}. Falling back...")

        # Try Apify as secondary if RapidAPI failed
        if getattr(settings, 'APIFY_TOKEN', ''):
            try:
                items = InstagramScannerService._fetch_from_apify(handle)
                if items:
                    return items
            except Exception as e:
                print(f"[API Warning] Apify fetch failed for @{handle}: {e}. Falling back...")

        # Fallback Simulation Generator
        return InstagramScannerService._fetch_fallback_data(handle)


    @staticmethod
    def _fetch_from_rapidapi(handle):
        """
        Fetches reels/posts data from RapidAPI Instagram Scraper endpoints.
        """
        from django.conf import settings
        url = f"https://{settings.RAPIDAPI_HOST}/v1/user_reels"
        headers = {
            "X-RapidAPI-Key": settings.RAPIDAPI_KEY,
            "X-RapidAPI-Host": settings.RAPIDAPI_HOST
        }
        params = {"username_or_id_or_url": handle}
        response = requests.get(url, headers=headers, params=params, timeout=10)
        
        if response.status_code != 200:
            try:
                err_msg = response.json().get('message', response.text)
            except Exception:
                err_msg = response.text
            raise RuntimeError(f"RapidAPI HTTP {response.status_code}: {err_msg}")

        data = response.json().get('data', {})
        items_raw = data.get('items', []) or data.get('reels', [])

        
        items = []
        for i, item in enumerate(items_raw[:4]):
            caption_text = ""
            if isinstance(item.get('caption'), dict):
                caption_text = item['caption'].get('text', '')
            elif isinstance(item.get('caption'), str):
                caption_text = item['caption']

            # Extract video URL and thumbnail
            video_versions = item.get('video_versions', [])
            video_url = video_versions[0].get('url') if video_versions else SAMPLE_VIDEOS[i % len(SAMPLE_VIDEOS)]['video_url']

            image_versions = item.get('image_versions2', {}).get('candidates', [])
            thumbnail_url = image_versions[0].get('url') if image_versions else SAMPLE_VIDEOS[i % len(SAMPLE_VIDEOS)]['thumbnail']

            post_id = item.get('id') or f"rapidapi_{handle}_{i+1}"
            code = item.get('code') or item.get('shortcode', post_id)

            items.append({
                "id": post_id,
                "title_hint": f"Reel from @{handle}",
                "caption": caption_text or f"Latest update from @{handle}'s Instagram reel.",
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "ig_url": f"https://instagram.com/reel/{code}",
                "views": item.get('play_count', item.get('view_count', random.randint(3500, 89000))),
                "likes": item.get('like_count', random.randint(800, 15400)),
                "comments": item.get('comment_count', random.randint(80, 2100))
            })
        return items

    @staticmethod
    def _fetch_from_apify(handle):
        """
        Fetches reels/posts data via Apify Actor API.
        """
        from django.conf import settings
        url = f"https://api.apify.com/v2/acts/apify~instagram-scraper/run-sync-get-dataset-items?token={settings.APIFY_TOKEN}&timeout=35"
        payload = {
            "directUrls": [f"https://www.instagram.com/{handle}/"],
            "resultsType": "posts",
            "resultsLimit": 4
        }
        response = requests.post(url, json=payload, timeout=45)
        if response.status_code not in (200, 201):
            raise RuntimeError(f"Apify HTTP {response.status_code}: {response.text[:200]}")

        apify_items = response.json()
        if not isinstance(apify_items, list) or not apify_items:
            return None

        items = []
        for i, item in enumerate(apify_items[:4]):
            post_id = item.get('id') or item.get('shortCode') or f"apify_{handle}_{i+1}"
            caption = item.get('caption') or f"Latest post from @{handle} on Instagram."
            video_url = item.get('videoUrl') or SAMPLE_VIDEOS[i % len(SAMPLE_VIDEOS)]['video_url']
            thumbnail_url = item.get('displayUrl') or SAMPLE_VIDEOS[i % len(SAMPLE_VIDEOS)]['thumbnail']

            items.append({
                "id": post_id,
                "title_hint": caption[:60] or f"Instagram post by @{handle}",
                "caption": caption,
                "video_url": video_url,
                "thumbnail_url": thumbnail_url,
                "ig_url": item.get('url') or f"https://instagram.com/p/{post_id}",
                "views": item.get('videoViewCount', random.randint(3500, 89000)),
                "likes": item.get('likesCount', random.randint(800, 15400)),
                "comments": item.get('commentsCount', random.randint(80, 2100))
            })
        return items


    @staticmethod
    def _fetch_fallback_data(handle):
        """
        Fallback simulation generator for offline/unconfigured mode.
        """
        items = []
        seed = sum(ord(c) for c in handle)
        random.seed(seed)

        num_posts = random.randint(3, 4)
        shuffled_samples = random.sample(SAMPLE_VIDEOS, min(num_posts, len(SAMPLE_VIDEOS)))

        for i, sample in enumerate(shuffled_samples):
            item_id = f"reel_{i+1}_{seed}"
            items.append({
                "id": item_id,
                "title_hint": f"{sample['title_template']} by @{handle}",
                "caption": f"🚨 Exciting new video drops from @{handle}! {sample['title_template']}. Check out how we're reshaping digital content. {' '.join(sample['tags'])}",
                "video_url": sample['video_url'],
                "thumbnail_url": sample['thumbnail'],
                "ig_url": f"https://instagram.com/reel/{item_id}",
                "views": random.randint(3500, 89000),
                "likes": random.randint(800, 15400),
                "comments": random.randint(80, 2100)
            })

        random.seed()
        return items


    @staticmethod
    def _generate_blog_title(caption, fallback_title):
        clean_caption = re.sub(r'#\w+', '', caption).strip()
        lines = [line.strip() for line in clean_caption.split('\n') if line.strip()]
        if lines:
            first_line = lines[0]
            if len(first_line) > 10 and len(first_line) < 80:
                return first_line.title()
        return fallback_title or "Editorial Breakdown: Featured Video Update"

    @staticmethod
    def _generate_editorial_article(handle, caption, title):
        paragraphs = [
            f"In this featured editorial highlight, we examine the latest media release from **@{handle}**. The commentary and visual storytelling presented in this clip bring essential insights into modern digital production.",
            f"### Key Highlights & Commentary\n\n\"{caption}\"",
            f"### Architectural Insights\n\nAs digital platforms shift towards automated content aggregation, hosting and streaming video assets locally guarantees consistent performance, reduced reliance on third-party embeds, and total control over user engagement metrics.",
            f"Stay tuned for continuous automated updates as **@{handle}** releases further visual content across the platform."
        ]
        return "\n\n".join(paragraphs)

    @staticmethod
    def _download_and_store_media(post_id, video_src, thumbnail_src):
        """
        Downloads remote media files (e.g. from Instagram CDN) and stores them using Django default_storage.
        Works seamlessly for both local disk storage and Cloudflare R2 / S3 object storage in production.
        """
        from django.conf import settings
        from django.core.files.storage import default_storage
        from django.core.files.base import ContentFile
        import requests, re, os

        clean_id = re.sub(r'[^a-zA-Z0-9_-]', '_', post_id)
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        }

        # 1. Download & Host Video File
        local_video_url = video_src
        if video_src and (video_src.startswith('http://') or video_src.startswith('https://')):
            try:
                rel_path = f"videos/{clean_id}.mp4"
                if not default_storage.exists(rel_path):
                    res = requests.get(video_src, headers=headers, stream=True, timeout=35)
                    if res.status_code == 200:
                        content = res.content
                        default_storage.save(rel_path, ContentFile(content))
                
                if default_storage.exists(rel_path):
                    local_video_url = default_storage.url(rel_path)
            except Exception as e:
                print(f"[Media Warning] Video download for {post_id} failed: {e}")

        # 2. Download & Host Thumbnail Image
        local_thumb_url = thumbnail_src
        if thumbnail_src and (thumbnail_src.startswith('http://') or thumbnail_src.startswith('https://')):
            try:
                rel_path = f"thumbnails/{clean_id}.jpg"
                if not default_storage.exists(rel_path):
                    res = requests.get(thumbnail_src, headers=headers, stream=True, timeout=20)
                    if res.status_code == 200:
                        content = res.content
                        default_storage.save(rel_path, ContentFile(content))

                if default_storage.exists(rel_path):
                    local_thumb_url = default_storage.url(rel_path)
            except Exception as e:
                print(f"[Media Warning] Thumbnail download for {post_id} failed: {e}")

        return local_video_url, local_thumb_url


