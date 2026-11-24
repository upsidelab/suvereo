from typing import Any

from django.core.management.base import BaseCommand, CommandParser

from account.models import User


class Command(BaseCommand):
    help = (
        "Creates the initial super user account. This command has no effect if there are existing users in the system."
    )

    def add_arguments(self, parser: CommandParser) -> None:
        parser.add_argument("-e", "--email", default=None, help="the email for the superuser account to be created")
        parser.add_argument("-p", "--password", default=None, help="the initial password for the superuser")

    def handle(self, *args: Any, **options: Any) -> None:
        if not User.objects.exists():
            User.objects.create_superuser(email=options["email"], password=options["password"])
