from django.db import transaction
from rest_framework import serializers
from rest_framework.exceptions import PermissionDenied
from rest_framework.validators import UniqueValidator

from account.models import User
from account.services import RefreshTokenRevocationService


def unique_email_field():
    return serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="An account with this email already exists.",
            )
        ]
    )


class OnlyAdminsManageAdminsMixin:
    def validate(self, attrs):
        request = self.context.get("request")
        if request is not None and not request.user.is_superuser:
            if attrs.get("is_superuser"):
                raise PermissionDenied("Only an admin can grant admin access.")
            if self.instance is not None and self.instance.is_superuser:
                raise PermissionDenied("Only an admin can modify an admin account.")
        return super().validate(attrs)


class UserSerializer(OnlyAdminsManageAdminsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = unique_email_field()
    is_active = serializers.BooleanField()
    is_admin = serializers.BooleanField(source="is_superuser")
    password = serializers.CharField(write_only=True)

    def create(self, validated_data):
        return User.objects.create_user(
            email=validated_data["email"],
            password=validated_data["password"],
            is_active=validated_data["is_active"],
            is_superuser=validated_data["is_superuser"],
        )


class UserUpdateSerializer(OnlyAdminsManageAdminsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = unique_email_field()
    is_active = serializers.BooleanField()
    is_admin = serializers.BooleanField(source="is_superuser")

    def update(self, instance, validated_data):
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        return instance


class UserUpdatePasswordSerializer(OnlyAdminsManageAdminsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    password = serializers.CharField(write_only=True)

    def update(self, instance, validated_data):
        with transaction.atomic():
            instance.set_password(validated_data["password"])
            instance.save()
            RefreshTokenRevocationService().revoke_all(instance)
        return instance


class UserSummarySerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "email", "is_service_account"]


class UserReferenceSerializer(serializers.Serializer):
    user_id = serializers.PrimaryKeyRelatedField(source="user", queryset=User.objects.all())
