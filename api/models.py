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
# LIVE PROGRAM MODEL
# =========================
class LiveProgram(models.Model):
    title = models.CharField(max_length=200)
    category = models.CharField(max_length=100)
    video_file = models.FileField(upload_to='videos/live/')
    # uploaded_at = models.DateTimeField(auto_now_add=True)
# to control what shows on the Live TV screen
    is_live = models.BooleanField(default=False) 
    hls_playlist_url = models.CharField(max_length=500, blank=True, null=True)

    def __save__(self, *args, **kwargs):
        # Logic to ensure only ONE video is live at a time
        if self.is_live:
            LiveProgram.objects.filter(is_live=True).update(is_live=False)
        super().save(*args, **kwargs)

# =========================
# SIGNAL TO CONVERT VIDEO TO HLS
# =========================
@receiver(post_save, sender=LiveProgram)
def convert_to_hls(sender, instance, created, **kwargs):
    if created:
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
        except Exception as e:
            print(f"FFmpeg Error: {e}")