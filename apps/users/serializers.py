from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from rest_framework import serializers

from .trial import get_trial_ends_at

User = get_user_model()


class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    email = serializers.EmailField(
        required=True,
        validators=[],
        error_messages={'blank': 'El email es obligatorio.'},
    )

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email', 'password',
            'first_name', 'last_name', 'bio', 'avatar',
            'birth_date', 'birth_time', 'birth_place',
            'plan', 'plan_expires_at',
        )
        read_only_fields = ('id', 'plan', 'plan_expires_at')

    def create(self, validated_data):
        password = validated_data.pop('password')
        if settings.TRIAL_MODE:
            validated_data.update(
                plan=User.Plan.PREMIUM,
                plan_expires_at=get_trial_ends_at(),
                is_trial_grant=True,
            )
        user = User(**validated_data)
        user.set_password(password)
        user.save()
        return user

    def validate_email(self, value):
        if User.objects.filter(email__iexact=value).exists():
            raise serializers.ValidationError('Ya existe una cuenta con este email.')
        return value.lower()

    def validate(self, attrs):
        try:
            validate_password(attrs['password'], user=User(**attrs))
        except DjangoValidationError as error:
            raise serializers.ValidationError({'password': list(error.messages)}) from error
        return attrs


class UserSerializer(serializers.ModelSerializer):
    zodiac_sign = serializers.SerializerMethodField()
    plan = serializers.SerializerMethodField()
    email = serializers.EmailField(required=True, validators=[])

    class Meta:
        model = User
        fields = (
            'id', 'username', 'email',
            'first_name', 'last_name', 'bio', 'avatar',
            'birth_date', 'birth_time', 'birth_place',
            'address_as',
            'zodiac_sign', 'plan', 'plan_expires_at',
        )
        read_only_fields = ('id', 'username', 'zodiac_sign', 'plan', 'plan_expires_at')

    def get_plan(self, obj):
        return User.Plan.PREMIUM if obj.is_premium else User.Plan.FREE

    def get_zodiac_sign(self, obj):
        return obj.get_zodiac_sign()

    def validate_email(self, value):
        users_with_email = User.objects.filter(email__iexact=value)
        if self.instance is not None:
            users_with_email = users_with_email.exclude(pk=self.instance.pk)
        if users_with_email.exists():
            raise serializers.ValidationError('Ya existe una cuenta con este email.')
        return value.lower()
