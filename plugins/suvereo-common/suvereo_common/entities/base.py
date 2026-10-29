from dataclasses import dataclass
from typing import Optional


@dataclass(frozen=True)
class EntityField:
    """One column in an entity's read-only table view.

    ``name`` is the model attribute to show; ``label`` is the column header
    (defaults to ``name`` when omitted).
    """

    name: str
    label: Optional[str] = None


class DomainEntity:
    """Mixin that exposes a Django model as a read-only table in the UI.

    A plugin mixes this into its Django model alongside ``models.Model`` and
    the framework renders it as a generic table over the API with no per-model
    frontend work.

    Declare an inner ``EntityMeta`` (mirroring Django's ``Meta`` convention)::

        class MyEntity(DomainEntity, models.Model):
            ...
            class EntityMeta:
                slug = "my-entities"
                label = "My Entities"
                list_fields = [
                    EntityField("name"),
                    EntityField("created_at", label="Created"),
                ]
    """

    class EntityMeta:
        #: URL-safe identifier for the entity.
        slug: str
        #: Human-readable plural label.
        label: str
        #: Columns to show in the list view.
        list_fields: list[EntityField] = []

    @classmethod
    def get_entity_meta(cls) -> type["DomainEntity.EntityMeta"]:
        """Return this entity's ``EntityMeta``, or raise ``TypeError`` if absent."""
        meta = cls.__dict__.get("EntityMeta")
        if meta is None:
            raise TypeError(f"{cls.__name__} must declare an inner EntityMeta class to be a DomainEntity.")
        return meta
