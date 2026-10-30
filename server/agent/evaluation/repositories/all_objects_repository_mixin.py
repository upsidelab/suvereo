from django.db.models import Model, QuerySet


class AllObjectsRepositoryMixin:
    model: type[Model]

    def get_by_id(self, pk: int) -> Model | None:
        try:
            return self.model.all_objects.get(pk=pk)
        except self.model.DoesNotExist:
            return None

    def list(self) -> list[Model]:
        return list(self.model.all_objects.all())

    def filter(self, **kwargs) -> QuerySet:
        return self.model.all_objects.filter(**kwargs)

    def delete(self, pk: int) -> bool:
        deleted, _ = self.model.all_objects.filter(pk=pk).delete()
        return deleted > 0
