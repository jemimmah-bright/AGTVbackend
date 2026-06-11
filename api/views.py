import random
from django.utils import timezone
from django.db.models import Sum
from django.core.mail import send_mail
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status, generics
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.authtoken.models import Token
from rest_framework.parsers import MultiPartParser, FormParser

from .serializers import UserSerializer, LiveProgramSerializer
from .models import PasswordResetOTP, LiveProgram

User = get_user_model()


# =========================
# REGISTER VIEW
# =========================
class RegisterView(APIView):

    def post(self, request):
        data = request.data.copy()
        email = data.get("email", "").strip()
        username = data.get("username", "").strip()

        # Sanitize username (remove spaces, only allow valid chars)
        if not username or " " in username:
            if username:
                sanitized = "".join(c for c in username.replace(" ", "_") if c.isalnum() or c in ["_", "@", ".", "+", "-"])
                username = sanitized
            else:
                username = email.split("@")[0]

        if not username:
            username = email.split("@")[0] or "user"

        # Ensure unique username
        base_username = username
        counter = 1
        while User.objects.filter(username__iexact=username).exists():
            username = f"{base_username}_{User.objects.count() + counter}"
            counter += 1

        data["username"] = username

        serializer = UserSerializer(data=data)

        if serializer.is_valid():
            user = serializer.save()

            # Save full name details
            full_name = request.data.get("username", "").strip()
            if full_name:
                parts = full_name.split(" ", 1)
                user.first_name = parts[0]
                if len(parts) > 1:
                    user.last_name = parts[1]
                user.save()

                if hasattr(user, 'profile'):
                    user.profile.full_name = full_name
                    user.profile.save()

            token = Token.objects.create(user=user)

            return Response({
                "token": token.key,
                "message": "User registered successfully"
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class AdminRegisterView(APIView):

    def post(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        username = request.data.get("username") or (email.split("@")[0] if email else None)

        if not email or not password:
            return Response(
                {"error": "Email and password are required for admin registration."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email__iexact=email).exists():
            return Response(
                {"error": "An account with this email already exists."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(username__iexact=username).exists():
            username = f"{username}_{User.objects.count() + 1}"

        user = User.objects.create_superuser(
            username=username,
            email=email,
            password=password,
        )
        token = Token.objects.create(user=user)

        return Response({
            "token": token.key,
            "username": user.username,
            "email": user.email,
            "is_admin": True,
            "message": "Admin registered successfully"
        }, status=status.HTTP_201_CREATED)


# =========================
# LOGIN VIEW
# =========================
class LoginView(APIView):

    def post(self, request):
        username = request.data.get("username") or request.data.get("email")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Email/username and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if not user and '@' in username:
            # Allow login with email as well as username
            user_obj = User.objects.filter(email__iexact=username).first()
            if user_obj:
                user = authenticate(username=user_obj.username, password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                "token": token.key,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "is_admin": user.is_staff or user.is_superuser,
                "message": "Login successful"
            }, status=status.HTTP_200_OK)

        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )


# =========================
# LOGOUT VIEW
# =========================
class LogoutView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Delete the token to log out the user
        request.user.auth_token.delete()
        return Response({"message": "Logout successful"}, status=status.HTTP_200_OK)


# =========================
# REQUEST OTP VIEW
# =========================
class RequestOTPView(APIView):

    def post(self, request):
        email = request.data.get("email")

        if not email:
            return Response(
                {"error": "Email is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Case-insensitive query and get the first matched user safely
        user = User.objects.filter(email__iexact=email).first()
        if not user:
            return Response(
                {"error": "No account found with this email"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Delete any existing OTP codes for this user
        PasswordResetOTP.objects.filter(user=user).delete()

        otp_code = str(random.randint(1000, 9999))

        # Save the new OTP code to the database
        PasswordResetOTP.objects.create(user=user, otp=otp_code)

        email_sent = False
        try:
            send_mail(
                subject='Your AGtv Verification Code',
                message=f"Your verification code is: {otp_code}. It expires in 2 minutes.",
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
            )
            email_sent = True
        except Exception as e:
            # Print connection warning for local developers
            print(f"SMTP Email Sending Failed: {e}")

        # If email was sent successfully, return normal success
        if email_sent:
            return Response(
                {"message": "OTP sent to your email"},
                status=status.HTTP_200_OK
            )
        else:
            # If email fails, WE STILL KEEP THE OTP IN THE DATABASE!
            # If DEBUG is True, we return it in the response for easy local testing in Postman
            from django.conf import settings
            response_data = {
                "message": "OTP generated (Failed to send email. Check your server console or see below for the code)",
                "warning": "SMTP server is unreachable or credentials are not configured. The OTP is recorded in the database.",
            }
            if settings.DEBUG:
                response_data["otp"] = otp_code
            return Response(response_data, status=status.HTTP_200_OK)


# =========================
# VERIFY OTP ONLY
# =========================
class VerifyOTPView(APIView):

    def post(self, request):
        email = request.data.get('email')
        otp_entered = request.data.get('otp')

        if not email or not otp_entered:
            return Response({"error": "Email and OTP are required"}, status=400)

        # Case-insensitive email query
        otp_record = PasswordResetOTP.objects.filter(
            user__email__iexact=email,
            otp=otp_entered
        ).last()

        if not otp_record:
            return Response({"error": "Invalid code"}, status=400)

        now = timezone.now()
        timediff = (now - otp_record.created_at).total_seconds()

        if timediff > 120:
            otp_record.delete()
            return Response({"error": "Code expired"}, status=400)

        return Response({"message": "OTP verified"}, status=200)


# =========================
# VERIFY OTP & RESET PASSWORD
# =========================
class VerifyAndResetView(APIView):

    def post(self, request):
        email = request.data.get('email')
        otp_entered = request.data.get('otp')
        new_password = request.data.get('new_password')

        if not new_password or not email or not otp_entered:
            return Response({"error": "Email, OTP, and new password are required"}, status=400)

        # Case-insensitive email query
        otp_record = PasswordResetOTP.objects.filter(
            user__email__iexact=email,
            otp=otp_entered
        ).last()

        if not otp_record:
            return Response({"error": "Invalid code"}, status=400)

        now = timezone.now()
        timediff = (now - otp_record.created_at).total_seconds()

        if timediff > 120:
            otp_record.delete()
            return Response({"error": "Code expired. Request a new one."}, status=400)

        user = otp_record.user
        user.set_password(new_password)
        user.save()

        otp_record.delete()

        return Response(
            {"message": "Success! Password updated."},
            status=status.HTTP_200_OK
        )


# =========================
# VIDEO UPLOAD
# =========================
class VideoUploadView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = LiveProgramSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================
# SET LIVE STREAM
# =========================
class SetLiveView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]

    def post(self, request, pk):
        try:
            live_program = LiveProgram.objects.get(pk=pk)
            live_program.is_live = True
            live_program.save()
            return Response({"message": "Live stream set successfully"}, status=status.HTTP_200_OK)
        except LiveProgram.DoesNotExist:
            return Response({"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =========================
# CURRENT LIVE STREAM
# =========================
class CurrentLiveStreamView(APIView):

    def get(self, request):
        # Get the latest program marked as Live
        live_program = LiveProgram.objects.filter(is_live=True).first()
        if not live_program:
            # Fallback to the latest uploaded video in the database
            live_program = LiveProgram.objects.all().order_by('-id').first()
            
        if live_program:
            serializer = LiveProgramSerializer(live_program, context={'request': request})
            return Response(serializer.data)
        return Response({"error": "No live stream found"}, status=404)


# =========================
# VIDEO LIST
# =========================
class VideoListView(APIView):

    def get(self, request):
        # Return all videos from newest to oldest
        videos = LiveProgram.objects.all().order_by('-id')
        serializer = LiveProgramSerializer(videos, many=True, context={'request': request})
        return Response(serializer.data)

# =========================
# VIDEO DETAIL (RENAME/DELETE)
# =========================
class VideoDetailUpdateDeleteView(generics.RetrieveUpdateDestroyAPIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    queryset = LiveProgram.objects.all()
    serializer_class = LiveProgramSerializer

# =========================
# VIDEO LIKE VIEW
# =========================
class VideoLikeView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            video = LiveProgram.objects.get(pk=pk)
            if video.liked_by.filter(id=request.user.id).exists():
                video.liked_by.remove(request.user)
                liked = False
            else:
                video.liked_by.add(request.user)
                liked = True
            video.likes_count = video.liked_by.count()
            video.save()
            return Response({
                "liked": liked,
                "likes_count": video.likes_count
            }, status=status.HTTP_200_OK)
        except LiveProgram.DoesNotExist:
            return Response({"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =========================
# VIDEO SHARE VIEW
# =========================
class VideoShareView(APIView):
    def post(self, request, pk):
        try:
            video = LiveProgram.objects.get(pk=pk)
            video.shares_count += 1
            video.save()
            return Response({
                "shares_count": video.shares_count
            }, status=status.HTTP_200_OK)
        except LiveProgram.DoesNotExist:
            return Response({"error": "Video not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# =========================
# ADMIN ANALYTICS
# =========================
class AdminAnalyticsView(APIView):
    permission_classes = [IsAuthenticated, IsAdminUser]
    
    def get(self, request):
        try:
            # Live viewers connected
            live_viewers = LiveProgram.objects.filter(is_live=True).aggregate(Sum('viewers_count'))['viewers_count__sum'] or 0
            
            # Total registered users
            total_users = User.objects.count()
            
            # Total likes mapped across all programs
            total_likes = LiveProgram.objects.aggregate(Sum('likes_count'))['likes_count__sum'] or 0
            
            # Total shares mapped across all programs
            total_shares = LiveProgram.objects.aggregate(Sum('shares_count'))['shares_count__sum'] or 0

            # Find active live video stats
            live_video = LiveProgram.objects.filter(is_live=True).first()
            live_likes = live_video.liked_by.count() if live_video else 0
            live_shares = live_video.shares_count if live_video else 0

            # System health mapped through basic ORM reachability connection
            system_health = "Excellent" if total_users is not None else "Degraded"

            return Response({
                "live_now": live_viewers,
                "total_users": total_users,
                "total_likes": total_likes,
                "total_shares": total_shares,
                "live_likes": live_likes,
                "live_shares": live_shares,
                "system_health": system_health,
                # Mock weekly/monthly growth trends specifically mapped for Flutter charts
                "viewers_over_time": [40, 110, 220, 240, 310, 360, 450], 
                "users_growth": [2800, 3100, 3300, 3500] 
            }, status=200)
        except Exception as e:
            return Response({"error": str(e)}, status=500)
