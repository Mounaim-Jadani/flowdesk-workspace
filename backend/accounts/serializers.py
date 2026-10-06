"""
Serializers for user authentication and profile management.
"""
from rest_framework import serializers
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password

User = get_user_model()


class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Custom JWT token serializer with additional user data."""

    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        # Add custom claims
        token['username'] = user.username
        token['email'] = user.email
        return token

    def validate(self, attrs):
        data = super().validate(attrs)
        # Add user info to response
        from presence.utils import get_active_deep_work
        session = get_active_deep_work(self.user)
        deep_work = None
        if session:
            deep_work = {
                'active': True,
                'ends_at': session.ends_at.isoformat()
            }
            
        data['user'] = {
            'id': self.user.id,
            'username': self.user.username,
            'email': self.user.email,
            'display_name': self.user.get_display_name(),
            'avatar': self.user.avatar.url if self.user.avatar else None,
            'deep_work': deep_work,
        }
        return data


class UserRegistrationSerializer(serializers.ModelSerializer):
    """Serializer for user registration."""

    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password],
        style={'input_type': 'password'}
    )
    password_confirm = serializers.CharField(
        write_only=True,
        required=True,
        style={'input_type': 'password'}
    )

    class Meta:
        model = User
        fields = ('email', 'username', 'password', 'password_confirm', 'display_name')
        extra_kwargs = {
            'display_name': {'required': False},
        }

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('A user with this email already exists.')
        return value.lower()

    def validate_username(self, value):
        if User.objects.filter(username__iexact=value).exists():
            raise serializers.ValidationError('A user with this username already exists.')
        if len(value) < 3:
            raise serializers.ValidationError('Username must be at least 3 characters.')
        if not value.isalnum() and '_' not in value:
            raise serializers.ValidationError('Username can only contain letters, numbers, and underscores.')
        return value

    def validate(self, attrs):
        if attrs['password'] != attrs['password_confirm']:
            raise serializers.ValidationError({'password_confirm': 'Passwords do not match.'})
        return attrs

    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(**validated_data)
        return user


class UserSerializer(serializers.ModelSerializer):
    """Serializer for user profile display."""

    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    deep_work = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'display_name', 'avatar_url',
            'bio', 'is_online', 'last_seen', 'created_at', 'deep_work'
        )
        read_only_fields = ('id', 'email', 'created_at')

    def get_display_name(self, obj):
        return obj.get_display_name()

    def get_avatar_url(self, obj):
        if obj.avatar:
            request = self.context.get('request')
            if request:
                return request.build_absolute_uri(obj.avatar.url)
            return obj.avatar.url
        return None

    def get_deep_work(self, obj):
        from presence.utils import get_active_deep_work
        session = get_active_deep_work(obj)
        if session:
            return {
                'active': True,
                'ends_at': session.ends_at.isoformat()
            }
        return None


class UserUpdateSerializer(serializers.ModelSerializer):
    """Serializer for updating user profile."""

    class Meta:
        model = User
        fields = ('username', 'display_name', 'bio', 'avatar',
                  'email_notifications', 'push_notifications')
        extra_kwargs = {
            'username': {'required': False},
        }

    def validate_username(self, value):
        user = self.context['request'].user
        if User.objects.exclude(pk=user.pk).filter(username__iexact=value).exists():
            raise serializers.ValidationError('This username is already taken.')
        return value


class PasswordChangeSerializer(serializers.Serializer):
    """Serializer for password change."""

    current_password = serializers.CharField(required=True)
    new_password = serializers.CharField(required=True, validators=[validate_password])
    new_password_confirm = serializers.CharField(required=True)

    def validate_current_password(self, value):
        user = self.context['request'].user
        if not user.check_password(value):
            raise serializers.ValidationError('Current password is incorrect.')
        return value

    def validate(self, attrs):
        if attrs['new_password'] != attrs['new_password_confirm']:
            raise serializers.ValidationError({'new_password_confirm': 'Passwords do not match.'})
        return attrs


class UserMinimalSerializer(serializers.ModelSerializer):
    """Minimal serializer for user references in other objects."""

    display_name = serializers.SerializerMethodField()
    avatar_url = serializers.SerializerMethodField()
    deep_work = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ('id', 'username', 'display_name', 'avatar_url', 'is_online', 'deep_work')

    def get_display_name(self, obj):
        return obj.get_display_name()

    def get_avatar_url(self, obj):
        return obj.avatar.url if obj.avatar else None

    def get_deep_work(self, obj):
        from presence.utils import get_active_deep_work
        session = get_active_deep_work(obj)
        if session:
            return {
                'active': True,
                'ends_at': session.ends_at.isoformat()
            }
        return None
