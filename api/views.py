import random
from django.utils import timezone
from django.core.mail import send_mail
from django.contrib.auth import authenticate, get_user_model
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
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
        serializer = UserSerializer(data=request.data)

        if serializer.is_valid():
            user = serializer.save()
            token = Token.objects.create(user=user)

            return Response({
                "token": token.key,
                "message": "User registered successfully"
            }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================
# LOGIN VIEW
# =========================
class LoginView(APIView):

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")

        if not username or not password:
            return Response(
                {"error": "Username and password are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = authenticate(username=username, password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)

            return Response({
                "token": token.key,
                "username": user.username,
                "email": user.email,
                "first_name": user.first_name,
                "message": "Login successful"
            }, status=status.HTTP_200_OK)

        return Response(
            {"error": "Invalid credentials"},
            status=status.HTTP_401_UNAUTHORIZED
        )


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

        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            return Response(
                {"error": "No account found with this email"},
                status=status.HTTP_404_NOT_FOUND
            )

        PasswordResetOTP.objects.filter(user=user).delete()

        otp_code = str(random.randint(1000, 9999))

        PasswordResetOTP.objects.create(user=user, otp=otp_code)

        send_mail(
            subject='Your AGtv Verification Code',
            message=f"Your verification code is: {otp_code}. It expires in 2 minutes.",
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )

        return Response(
            {"message": "OTP sent to your email"},
            status=status.HTTP_200_OK
        )


# =========================
# VERIFY OTP ONLY
# =========================
class VerifyOTPView(APIView):

    def post(self, request):
        email = request.data.get('email')
        otp_entered = request.data.get('otp')

        otp_record = PasswordResetOTP.objects.filter(
            user__email=email,
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

        if not new_password:
            return Response({"error": "New password is required"}, status=400)

        otp_record = PasswordResetOTP.objects.filter(
            user__email=email,
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

    parser_classes = (MultiPartParser, FormParser)

    def post(self, request):
        serializer = LiveProgramSerializer(data=request.data)

        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


# =========================
# CURRENT LIVE STREAM
# =========================
class CurrentLiveStreamView(APIView):

    def get(self, request):
        # Get the latest program marked as Live
        live_program = LiveProgram.objects.filter(is_live=True).first()
        if live_program:
            serializer = LiveProgramSerializer(live_program)
            return Response(serializer.data)
        return Response({"error": "No live stream found"}, status=404)