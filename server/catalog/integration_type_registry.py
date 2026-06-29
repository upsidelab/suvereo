from enthusiast_common.integrations import BaseSourceIntegrationType


class IntegrationTypeRegistry:
    """Maps BaseIntegrationType subclasses to their sync manager instances.

    Managers self-register via the vertical's AppConfig.ready() so no explicit
    settings entry is needed beyond installing the vertical in INSTALLED_APPS.
    """

    _managers: dict[type, BaseSourceIntegrationType] = {}

    def register(self, manager: type) -> None:
        """Register a sync manager class under its declared HANDLES_TYPE."""
        self._managers[manager.HANDLES_TYPE] = manager()

    def get_for(self, integration_type: type | None) -> BaseSourceIntegrationType | None:
        """Return the manager instance for the given integration type, or None."""
        return self._managers.get(integration_type)
