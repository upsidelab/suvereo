from rest_framework import serializers

from account.models import User
from account.services import ServiceAccountNameService

from .users import OnlyAdminsManageAdminsMixin


class CreateUpdateServiceAccountSerializer(OnlyAdminsManageAdminsMixin, serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    name = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(default=True)
    is_admin = serializers.BooleanField(default=False, source="is_superuser")

    def validate_name(self, name):
        if not ServiceAccountNameService().is_service_account_name_available(name, exclude_user=self.instance):
            raise serializers.ValidationError("A service account with this name already exists.")
        return name

    def create(self, validated_data):
        return User.objects.create_service_account(
            email=self._build_service_account_email(validated_data["name"]),
            is_active=validated_data["is_active"],
            is_superuser=validated_data["is_superuser"],
        )

    def update(self, instance, validated_data):
        if "name" in validated_data:
            instance.email = self._build_service_account_email(validated_data.pop("name"))
        for attribute, value in validated_data.items():
            setattr(instance, attribute, value)
        instance.save()
        return instance

    def _build_service_account_email(self, name):
        service = ServiceAccountNameService()
        return service.generate_service_account_email(name)


class ServiceAccountSerializer(serializers.ModelSerializer):
    is_admin = serializers.BooleanField(source="is_superuser")

    class Meta:
        model = User
        fields = ["id", "email", "date_joined", "is_active", "is_admin"]


class TokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField()


class AvailabilityResponseSerializer(serializers.Serializer):
    is_available = serializers.BooleanField()
