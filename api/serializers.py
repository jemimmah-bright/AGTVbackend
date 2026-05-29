# Authentication & Serializers for AGTV Backend

from django.contrib.auth.models import User
from rest_framework import serializers
from .models import LiveProgram, UserProfile, CommodityPrice, VideoDownload


# =========================
# USER PROFILE SERIALIZER
# =========================
class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['phone_number', 'profile_image', 'full_name', 'created_at', 'updated_at']


# =========================
# USER SERIALIZER
# =========================
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    profile = UserProfileSerializer(read_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password', 'first_name', 'last_name', 'profile']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user


# =========================
# COMMODITY PRICE SERIALIZER
# =========================
class CommodityPriceSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommodityPrice
        fields = ['id', 'commodity_name', 'price', 'currency', 'updated_at']


# =========================
# LIVE PROGRAM SERIALIZER
# =========================
class LiveProgramSerializer(serializers.ModelSerializer):
    uploaded_by_username = serializers.CharField(source='uploaded_by.username', read_only=True)
    likes_count = serializers.SerializerMethodField()
    viewers_count = serializers.SerializerMethodField()
    user_liked = serializers.SerializerMethodField()

    class Meta:
        model = LiveProgram
        fields = [
            'id', 'title', 'category', 'video_file', 'is_live', 'hls_playlist_url',
            'uploaded_by', 'uploaded_by_username', 'created_at', 'updated_at',
            'likes_count', 'viewers_count', 'user_liked'
        ]

    def get_likes_count(self, obj):
        return obj.liked_by.count()

    def get_viewers_count(self, obj):
        return obj.viewed_by.count()

    def get_user_liked(self, obj):
        request = self.context.get('request')
        if request and request.user.is_authenticated:
            return obj.liked_by.filter(id=request.user.id).exists()
        return False


# =========================
# VIDEO DOWNLOAD SERIALIZER
# =========================
class VideoDownloadSerializer(serializers.ModelSerializer):
    username = serializers.CharField(source='user.username', read_only=True)
    video_title = serializers.CharField(source='video.title', read_only=True)

    class Meta:
        model = VideoDownload
        fields = ['id', 'username', 'video', 'video_title', 'downloaded_at']