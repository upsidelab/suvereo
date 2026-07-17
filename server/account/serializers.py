from rest_framework import serializers

from account.authorization import set_application_admin
from account.models import User

from .services import ServiceAccountNameService


class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_admin = serializers.BooleanField(read_only=True)


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    is_admin = serializers.BooleanField()
    password = serializers.CharField(write_only=True)


class UserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    is_admin = serializers.BooleanField()


class UserUpdatePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class CreateUpdateServiceAccountSerializer(serializers.Serializer):
    name = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(default=True)
    is_admin = serializers.BooleanField(default=False)
    data_set_ids = serializers.ListField(child=serializers.IntegerField(), required=False)

    def create(self, validated_data):
        email = self._build_service_account_email(validated_data.get("name"))
        service_account = User.objects.create_service_account(
            email=email, is_active=validated_data.get("is_active")
        )
        set_application_admin(service_account, validated_data.get("is_admin", False))
        service_account.data_sets.add(*validated_data.get("data_set_ids", []))
        return service_account

    def update(self, instance, validated_data):
        instance.email = self._build_service_account_email(validated_data.get("name"))
        instance.is_active = validated_data.get("is_active")
        instance.save()
        set_application_admin(instance, validated_data.get("is_admin", instance.is_admin))
        instance.data_sets.set(validated_data.get("data_set_ids", []))
        return instance

    def _build_service_account_email(self, name):
        service = ServiceAccountNameService()
        return service.generate_service_account_email(name)


class ServiceAccountSerializer(serializers.ModelSerializer):
    data_set_ids = serializers.SerializerMethodField()
    is_admin = serializers.BooleanField(read_only=True)

    class Meta:
        model = User
        fields = ["id", "email", "date_joined", "data_set_ids", "is_active", "is_admin"]

    def get_data_set_ids(self, obj):
        return list(obj.data_sets.values_list("id", flat=True))


class TokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField()


class AvailabilityResponseSerializer(serializers.Serializer):
    is_available = serializers.BooleanField()
