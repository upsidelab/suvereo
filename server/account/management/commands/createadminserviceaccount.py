from typing import Any

from django.core.management.base import BaseCommand, CommandParser
from rest_framework.authtoken.models import Token

from account.serializers import CreateUpdateServiceAccountSerializer


class Command(BaseCommand):
    help = "Creates service account with admin permission and outputs it's token."

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("-n", "--name", required=True, help="name of service account")

    def handle(self, *args: Any, **options: Any) -> None:
        serializer = CreateUpdateServiceAccountSerializer(data={"name": options["name"], "is_admin": True})
        serializer.is_valid(raise_exception=True)
        service_account = serializer.save()
        token, _ = Token.objects.get_or_create(user=service_account)
        self.stdout.write(f"Service Account token: {token.key}")
