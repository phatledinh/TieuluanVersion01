"""
Serializers for User Service.
Handles registration, login response, and user CRUD.
"""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

User = get_user_model()


# ---------------------------------------------------------------------------
# Registration
# ---------------------------------------------------------------------------

class RegisterSerializer(serializers.ModelSerializer):
    """
    POST /api/auth/register/
    Creates a new Customer user by default.
    """

    password = serializers.CharField(
        write_only=True,
        min_length=6,
        style={'input_type': 'password'},
    )
    password_confirm = serializers.CharField(
        write_only=True,
        style={'input_type': 'password'},
    )

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'password', 'password_confirm',
            'first_name', 'last_name', 'phone', 'address', 'role',
        ]
        read_only_fields = ['id']
        extra_kwargs = {
            'email': {'required': True},
            'role': {'required': False},
        }

    def validate(self, attrs):
        if attrs['password'] != attrs.pop('password_confirm'):
            raise serializers.ValidationError(
                {'password_confirm': 'Passwords do not match.'}
            )
        return attrs

    def validate_email(self, value):
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError('Email already registered.')
        return value

    def create(self, validated_data):
        # Default role is customer; only admin can create staff/admin
        role = validated_data.pop('role', User.Role.CUSTOMER)

        request = self.context.get('request')
        if request and hasattr(request, 'user') and request.user.is_authenticated:
            # Admin can assign any role
            if request.user.role == 'admin':
                pass  # keep the role as specified
            else:
                role = User.Role.CUSTOMER
        else:
            role = User.Role.CUSTOMER

        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
            phone=validated_data.get('phone', ''),
            address=validated_data.get('address', ''),
            role=role,
        )
        return user


# ---------------------------------------------------------------------------
# JWT Login - Custom claims to include role
# ---------------------------------------------------------------------------

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """
    POST /api/auth/login/
    Returns JWT tokens with user role embedded in claims.
    """

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        token['role'] = user.role
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Add extra response data
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'role': self.user.role,
            'first_name': self.user.first_name,
            'last_name': self.user.last_name,
        }
        return data


# ---------------------------------------------------------------------------
# User CRUD
# ---------------------------------------------------------------------------

class UserSerializer(serializers.ModelSerializer):
    """
    GET /api/users/          - List users
    GET /api/users/{id}/     - Retrieve user
    PUT /api/users/{id}/     - Update user
    DELETE /api/users/{id}/  - Delete user (admin only)
    """

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'address', 'is_active', 'date_joined',
        ]
        read_only_fields = ['id', 'username', 'date_joined']
        extra_kwargs = {
            'role': {'required': False},
        }


class UserProfileSerializer(serializers.ModelSerializer):
    """Serializer for the current user's own profile (limited fields)."""

    class Meta:
        model = User
        fields = [
            'id', 'username', 'email', 'first_name', 'last_name',
            'role', 'phone', 'address', 'date_joined',
        ]
        read_only_fields = ['id', 'username', 'role', 'date_joined']
