from rest_framework import serializers

from account.models import User

from .services import ServiceAccountNameService


class AccountSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    email = serializers.EmailField()
    is_admin = serializers.BooleanField(source="is_superuser")


class UserSerializer(serializers.Serializer):
    id = serializers.IntegerField(read_only=True)
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    is_admin = serializers.BooleanField(source="is_superuser")
    password = serializers.CharField(write_only=True)


class UserUpdateSerializer(serializers.Serializer):
    email = serializers.EmailField()
    is_active = serializers.BooleanField()
    is_admin = serializers.BooleanField(source="is_superuser")


class UserUpdatePasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True)


class CreateUpdateServiceAccountSerializer(serializers.Serializer):
    name = serializers.CharField(write_only=True)
    is_active = serializers.BooleanField(default=True)
    is_admin = serializers.BooleanField(default=False, source="is_superuser")
    data_set_ids = serializers.ListField(child=serializers.IntegerField(), required=False)

    def create(self, validated_data):
        email = self._build_service_account_email(validated_data.get("name"))
        is_active = validated_data.get("is_active")
        is_superuser = validated_data.get("is_superuser")
        # NOTE: data_set_ids is accepted but not persisted — DataSet.users is gone and no replacement
        # backing store is seeded yet (see "Migration strategy" in permissions-implementation-plan.md).
        service_account = User.objects.create_service_account(
            email=email, is_active=is_active, is_superuser=is_superuser
        )
        return service_account

    def update(self, instance, validated_data):
        instance.email = self._build_service_account_email(validated_data.get("name"))
        instance.is_active = validated_data.get("is_active")
        instance.is_superuser = validated_data.get("is_superuser")
        instance.save()
        # NOTE: data_set_ids is accepted but not persisted — see create() above.
        return instance

    def _build_service_account_email(self, name):
        service = ServiceAccountNameService()
        return service.generate_service_account_email(name)


class ServiceAccountSerializer(serializers.ModelSerializer):
    data_set_ids = serializers.SerializerMethodField()
    is_admin = serializers.BooleanField(source="is_superuser")

    class Meta:
        model = User
        fields = ["id", "email", "date_joined", "data_set_ids", "is_active", "is_admin"]

    def get_data_set_ids(self, obj):
        # NOTE: Stubbed: DataSet.users is gone and no replacement backing store is seeded yet
        # (see "Migration strategy" in specs/permissions-implementation-plan.md).
        return []


class TokenResponseSerializer(serializers.Serializer):
    token = serializers.CharField()


class AvailabilityResponseSerializer(serializers.Serializer):
    is_available = serializers.BooleanField()
