from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import datetime
import subprocess
import os
from django.db.models.signals import post_save
from django.dispatch import receiver

User = get_user_model()


# =========================
# USER PROFILE MODEL
# =========================
class UserProfile(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    phone_number = models.CharField(max_length=15, blank=True, null=True)
    profile_image = models.ImageField(upload_to='profiles/', blank=True, null=True)
    full_name = models.CharField(max_length=200, blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} - Profile"


# =========================
# PASSWORD RESET OTP MODEL
# =========================
class PasswordResetOTP(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    otp = models.CharField(max_length=6)
    created_at = models.DateTimeField(default=timezone.now)
    is_used = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.user.email} - {self.otp}"


# =========================
# COMMODITY PRICE MODEL
# =========================
class CommodityPrice(models.Model):
    COMMODITY_CHOICES = [
        ('Maize', 'Maize'),
        ('Coffee', 'Coffee'),
        ('Milk', 'Milk'),
        ('Vanilla', 'Vanilla'),
        ('Beans', 'Beans'),
    ]
    
    commodity_name = models.CharField(max_length=50, choices=COMMODITY_CHOICES)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=3, default='UGX')
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Commodity Prices"
        unique_together = ('commodity_name',)

    def __str__(self):
        return f"{self.commodity_name} - {self.price} {self.currency}"


# =========================
# LIVE PROGRAM MODEL (IMPROVED)
# =========================
class LiveProgram(models.Model):
    CATEGORY_CHOICES = [
        ('News', 'News'),
        ('Sports', 'Sports'),
        ('Crops', 'Crops'),
        ('Livestock', 'Livestock'),
    ]
    
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='News')
    video_file = models.FileField(upload_to='videos/live/', blank=True, null=True)
    is_live = models.BooleanField(default=False)
    hls_playlist_url = models.CharField(max_length=500, blank=True, null=True)
    
    # Track who uploaded the video
    uploaded_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='uploaded_videos')
    
    # Timestamps
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    # Analytics - Track users who liked and viewed
    liked_by = models.ManyToManyField(User, related_name='liked_videos', blank=True)
    viewed_by = models.ManyToManyField(User, related_name='watched_videos', blank=True)
    
    # Aggregate counts for fast querying
    likes_count = models.IntegerField(default=0)
    viewers_count = models.IntegerField(default=0)
    shares_count = models.IntegerField(default=0)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        # Logic to ensure only ONE video is live at a time
        if self.is_live:
            LiveProgram.objects.filter(is_live=True).exclude(id=self.id).update(is_live=False)
        super().save(*args, **kwargs)


# =========================
# VIDEO DOWNLOAD TRACKING MODEL
# =========================
class VideoDownload(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='downloads')
    video = models.ForeignKey(LiveProgram, on_delete=models.CASCADE, related_name='downloads')
    downloaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'video')

    def __str__(self):
        return f"{self.user.username} - {self.video.title}"

# =========================
# SIGNAL TO CREATE USER PROFILE
# =========================
@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.get_or_create(user=instance)


@receiver(post_save, sender=User)
def save_user_profile(sender, instance, **kwargs):
    instance.profile.save()


# =========================
# SIGNAL TO CONVERT VIDEO TO HLS
# =========================
@receiver(post_save, sender=LiveProgram)
def convert_to_hls(sender, instance, created, **kwargs):
    if created and instance.video_file:
        input_path = instance.video_file.path

        # Create folder for HLS output
        output_dir = os.path.join(os.path.dirname(input_path), f"hls_{instance.id}")
        os.makedirs(output_dir, exist_ok=True)

        output_hls = os.path.join(output_dir, "playlist.m3u8")

        cmd = [
            'ffmpeg', '-i', input_path,
            '-profile:v', 'baseline',
            '-level', '3.0',
            '-s', '1280x720',
            '-start_number', '0',
            '-hls_time', '10',
            '-hls_list_size', '0',
            '-f', 'hls',
            output_hls
        ]

        try:
            subprocess.Popen(cmd)
            print(f"HLS Conversion started for {instance.title}")
            
            # Save the relative URL to access the HLS stream
            relative_playlist_path = f"videos/live/hls_{instance.id}/playlist.m3u8"
            instance.hls_playlist_url = f"/media/{relative_playlist_path}"
            instance.save()
        except Exception as e:
            print(f"FFmpeg Error: {e}")