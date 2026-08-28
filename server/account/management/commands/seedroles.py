from django.contrib.auth.models import Permission
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from account.authorization import (
    DATASET_SCOPE_PERMISSIONS,
    GLOBAL_SCOPE_PERMISSIONS,
    PUBLIC_CODES,
    missing_dependencies,
    permission_label,
)
from account.models import DatasetRole, GlobalRole
from account.seeds import STARTER_DATA_SET_ROLES, STARTER_GLOBAL_ROLES, StarterRole

CREATED = "created"
MATCHES = "skipped, already matches"
DIFFERS = "skipped, differs from starter set"


class Command(BaseCommand):
    help = (
        "Creates the starter set of global and data set roles, so a fresh installation is usable "
        "without composing permission sets by hand. Safe to re-run: an existing role of the same "
        "name is never modified, only reported on."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="report what would happen without writing anything",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        role_sets = (
            ("Global roles", GlobalRole, STARTER_GLOBAL_ROLES, GLOBAL_SCOPE_PERMISSIONS),
            ("Data set roles", DatasetRole, STARTER_DATA_SET_ROLES, DATASET_SCOPE_PERMISSIONS),
        )

        for _, _, starter_roles, scope in role_sets:
            self._reject_unsatisfiable(starter_roles, scope)

        with transaction.atomic():
            for heading, model, starter_roles, _ in role_sets:
                self.stdout.write(self.style.MIGRATE_HEADING(heading))
                for starter in starter_roles:
                    self._report(starter.name, *self._apply(model, starter, dry_run))

            if dry_run:
                transaction.set_rollback(True)
                self.stdout.write("\nDry run - nothing was written.")

    def _reject_unsatisfiable(self, starter_roles: list[StarterRole], scope: list[str]) -> None:
        """Applies the rule the role editor applies, over every set before the first write."""
        for starter in starter_roles:
            granted = set(starter.permissions)

            out_of_scope = sorted(PUBLIC_CODES[code] for code in granted - set(scope))
            if out_of_scope:
                raise CommandError(
                    f"Starter role '{starter.name}' carries permissions outside its scope: {', '.join(out_of_scope)}."
                )

            unmet = missing_dependencies(granted, scope)
            if unmet:
                named = ", ".join(f"{entry['code']} (required by {', '.join(entry['required_by'])})" for entry in unmet)
                raise CommandError(f"Starter role '{starter.name}' is missing required permissions: {named}.")

    def _apply(self, model, starter: StarterRole, dry_run: bool) -> tuple[str, str]:
        existing = model.objects.filter(name=starter.name).first()
        if existing is None:
            if not dry_run:
                role = model.objects.create(name=starter.name, description=starter.description)
                role.permissions.set(self._permission_rows(starter.permissions))
            return CREATED, ""

        divergence = self._divergence(existing, starter)
        return (DIFFERS, divergence) if divergence else (MATCHES, "")

    def _divergence(self, existing, starter: StarterRole) -> str:
        """Names what an admin changed, to report rather than overwrite it."""
        differences = []
        if {permission_label(row) for row in existing.permissions.all()} != set(starter.permissions):
            differences.append("permissions")
        if existing.description != starter.description:
            differences.append("description")
        return " and ".join(differences)

    def _permission_rows(self, codenames: list[str]) -> list[Permission]:
        rows = []
        for codename in codenames:
            app_label, bare_codename = codename.split(".")
            rows.append(Permission.objects.get(content_type__app_label=app_label, codename=bare_codename))
        return rows

    def _report(self, name: str, outcome: str, detail: str) -> None:
        style = self.style.SUCCESS if outcome == CREATED else self.style.WARNING
        suffix = f" ({detail})" if detail else ""
        self.stdout.write(f"  {name}: {style(outcome)}{suffix}")
