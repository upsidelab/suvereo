from dataclasses import dataclass
from importlib import import_module
from typing import List, Optional, Type

from rest_framework import serializers
from suvereo_common.entities import EntityField


@dataclass
class EntityRegistration:
    slug: str
    label: str
    model: type
    fields: List[EntityField]
    serializer: Type[serializers.ModelSerializer]


class EntityRegistry:
    """Holds the DomainEntity models a domain definition registered, each with a generated serializer.

    Built once at startup from ``CATALOG_ENTITY_PLUGINS`` (see ``AppConfig.ready``).
    """

    def __init__(self):
        self._by_slug: dict[str, EntityRegistration] = {}

    def reset(self) -> None:
        self._by_slug = {}

    def build_from_settings(self) -> "EntityRegistry":
        from django.conf import settings

        self.reset()
        for path in settings.CATALOG_ENTITY_PLUGINS:
            self.register_model(self._import_class(path))
        return self

    def register_model(self, model: type) -> None:
        meta = model.get_entity_meta()
        self._by_slug[meta.slug] = EntityRegistration(
            slug=meta.slug,
            label=meta.label,
            model=model,
            fields=list(getattr(meta, "list_fields", [])),
            serializer=self._build_serializer(model, meta),
        )

    @staticmethod
    def _import_class(dotted_path: str) -> type:
        module_path, class_name = dotted_path.rsplit(".", 1)
        return getattr(import_module(module_path), class_name)

    @staticmethod
    def _build_serializer(model: type, meta) -> Type[serializers.ModelSerializer]:
        field_names = ["id"] + [field.name for field in getattr(meta, "list_fields", [])]
        meta_cls = type("Meta", (), {"model": model, "fields": field_names})
        return type(f"{model.__name__}Serializer", (serializers.ModelSerializer,), {"Meta": meta_cls})

    def all(self) -> List[EntityRegistration]:
        return list(self._by_slug.values())

    def get(self, slug: str) -> Optional[EntityRegistration]:
        return self._by_slug.get(slug)


entity_registry = EntityRegistry()
