from django.urls import path
from .views import RegisterView, LoginView, LogoutView, RequestOTPView, AdminRegisterView
from .views import VerifyAndResetView, VerifyOTPView
from .views import VideoUploadView, CurrentLiveStreamView, VideoListView, VideoDetailUpdateDeleteView, SetLiveView, AdminAnalyticsView, VideoLikeView, VideoShareView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('admin/register/', AdminRegisterView.as_view(), name='admin-register'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('send-otp/', RequestOTPView.as_view(), name='send-otp'),
    path('verify-reset/', VerifyAndResetView.as_view(), name='verify-reset'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('upload/', VideoUploadView.as_view(), name='video-upload'),
    path('live-now/', CurrentLiveStreamView.as_view(), name='live-now'),
    path('videos/', VideoListView.as_view(), name='video-list'),
    path('videos/<int:pk>/', VideoDetailUpdateDeleteView.as_view(), name='video-detail'),
    path('videos/<int:pk>/set-live/', SetLiveView.as_view(), name='video-set-live'),
    path('videos/<int:pk>/like/', VideoLikeView.as_view(), name='video-like'),
    path('videos/<int:pk>/share/', VideoShareView.as_view(), name='video-share'),
    path('admin/stats/', AdminAnalyticsView.as_view(), name='admin-stats'),
]