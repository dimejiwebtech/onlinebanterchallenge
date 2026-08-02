from django.urls import path
from . import views

urlpatterns = [
    path('', views.home_view, name='home'),
    path('scan/', views.scan_view, name='scan_post'),
    path('scan/<str:handle>/', views.scan_view, name='scan_handle'),
    path('profile/<str:handle>/', views.profile_detail_view, name='profile_detail'),
    path('post/<slug:slug>/', views.post_detail_view, name='post_detail'),
    path('dashboard/', views.admin_dashboard_view, name='admin_dashboard'),
]
