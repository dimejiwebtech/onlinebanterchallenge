from django.test import TestCase, Client
from django.urls import reverse
from .models import InstagramProfile, BlogPost, ScanLog
from .scanner_service import InstagramScannerService

class BlogScannerTestCase(TestCase):
    def setUp(self):
        self.client = Client()

    def test_on_the_fly_scanner_service(self):
        """Test on-the-fly Instagram handle scanning."""
        success, message, posts = InstagramScannerService.scan_handle('onlinebanters')
        self.assertTrue(success)
        self.assertGreater(len(posts), 0)
        self.assertTrue(InstagramProfile.objects.filter(handle='onlinebanters').exists())
        self.assertTrue(BlogPost.objects.filter(profile__handle='onlinebanters').exists())

    def test_homepage_view(self):
        """Test home feed rendering."""
        InstagramScannerService.scan_handle('fidelis')
        response = self.client.get(reverse('home'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'VibeBanter')
        self.assertContains(response, '@fidelis')

    def test_scan_url_route(self):
        """Test on-the-fly scanner GET URL route /scan/<handle>/."""
        response = self.client.get(reverse('scan_handle', kwargs={'handle': 'techvibes'}))
        self.assertEqual(response.status_code, 302)
        self.assertTrue(InstagramProfile.objects.filter(handle='techvibes').exists())
