from enum import StrEnum

from .permission_codenames import PERMISSIONS

PERMISSION_ENTITIES: dict[str, type[StrEnum]] = {
    name: permission_set
    for name, permission_set in vars(PERMISSIONS).items()
    if isinstance(permission_set, type) and issubclass(permission_set, StrEnum)
}

# The public permissions vocabulary, derived rather than maintained from PERMISSIONS
PUBLIC_CODES: dict[str, str] = {
    str(member): f"{entity_name.lower()}.{member.name.lower()}"
    for entity_name, permission_set in PERMISSION_ENTITIES.items()
    for member in permission_set
}

INTERNAL_CODES: dict[str, str] = {public: internal for internal, public in PUBLIC_CODES.items()}


def entity_label(entity_name: str) -> str:
    """The display name for a permission entity - "AGENTIC_EXECUTION" reads as "Agentic execution"."""
    return entity_name.replace("_", " ").capitalize()


def permission_label(permission) -> str:
    """The `app_label.codename` form of a `Permission` row, matching what `has_perm` expects."""
    return f"{permission.content_type.app_label}.{permission.codename}"
