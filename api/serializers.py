# Actually, starting with Authentication is much better! It is the "front door" of your application. Since your signup.dart and login_screen.dart already collect data, building the backend for these first ensures that every user has a secure account before they even see your video content.

# Here is how we bring your Auth screens to life using Django:

# 1. The Strategy
# We will use JSON Web Tokens (JWT).

# When a user logs in, Django sends a "Token" (a long secret string).

# Flutter saves this token.

# Every time the user wants to watch a video, the app shows that token to Django to prove who they are.

# 2. Create the Serializer
# In Django, a Serializer converts your User data into JSON format so Flutter can read it. Create a new file called api/serializers.py:
from django.contrib.auth.models import User
from rest_framework import serializers
from .models import LiveProgram

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'password']

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password']  # hashes automatically
        )
        return user

class LiveProgramSerializer(serializers.ModelSerializer):
    class Meta:
        model = LiveProgram
        fields = '__all__'