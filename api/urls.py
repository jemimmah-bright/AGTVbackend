from django.urls import path
from .views import CurrentLiveStreamView
from .views import RegisterView, LoginView, RequestOTPView
from .views import VerifyAndResetView
from .views import VerifyOTPView
from .views import VideoUploadView , CurrentLiveStreamView

urlpatterns = [
    path('register/', RegisterView.as_view(), name='register'),
    path('login/', LoginView.as_view(), name='login'),
    path('send-otp/', RequestOTPView.as_view(), name='send-otp'),
    path('verify-reset/', VerifyAndResetView.as_view(), name='verify-reset'),
    path('verify-otp/', VerifyOTPView.as_view(), name='verify-otp'),
    path('upload/', VideoUploadView.as_view(), name='video-upload'),
    path('live-now/', CurrentLiveStreamView.as_view(), name='live-now'),
    path('live-now/', CurrentLiveStreamView.as_view(), name='live-now'),
    

    
]