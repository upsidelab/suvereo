from dataclasses import replace
from typing import Any

from enthusiast_common.evaluation.mocks import BaseMock

from ..connectors import ECommercePlatformConnector
from ..connectors.errors import ECommerceConnectorError
from ..structures import ProductDetails, ProductUpdateDetails
from .catalog_product import CatalogProduct

ADMIN_URL = "https://shop.example/admin/orders/{order_id}"
ORDER_ID = "ORD-{number}"


class ECommerceConnectorMock(BaseMock[ECommercePlatformConnector]):
    """A connector backed by in-memory orders and the ``data["catalog"]`` products; declared behaviour still wins."""

    INTERFACE = ECommercePlatformConnector
    ERRORS = {"ECommerceConnectorError": ECommerceConnectorError}

    def __init__(self, *args: Any, **kwargs: Any):
        super().__init__(*args, **kwargs)
        self._catalog = CatalogProduct.load_all(self.data.get("catalog", []))
        #: An empty catalog accepts any SKU for the whole run, whatever products are created later.
        self._open_catalog = not self._catalog
        self._restore()

    def reset(self) -> None:
        """Forget recorded calls and return orders, products and stock to the starting catalog."""
        super().reset()
        with self._lock:
            self._restore()

    def _restore(self) -> None:
        self.products: dict[str, ProductDetails] = {p.sku: p.details() for p in self._catalog}
        self.stock: dict[str, int] = {p.sku: p.stock for p in self._catalog}
        self.orders: dict[str, dict[str, Any]] = {}

    def _default(self, method: str, *args: Any, **kwargs: Any) -> Any:
        handler = getattr(self, f"_handle_{method}", None)
        if handler is None:
            return super()._default(method, *args, **kwargs)
        with self._lock:
            return handler(**self._bind(method, args, kwargs))

    def _handle_create_empty_order(self, email=None, address=None) -> str:
        return self._new_order([], email, address)

    def _handle_create_order_with_items(self, items, email=None, address=None) -> str:
        if unknown := [sku for sku, _ in items if not self._known(sku)]:
            raise ECommerceConnectorError(f"Unknown SKU(s): {', '.join(unknown)}.", status_code=404)
        return self._new_order([(sku, int(quantity)) for sku, quantity in items], email, address)

    def _handle_add_to_order(self, order_id, sku, quantity) -> bool:
        if order_id not in self.orders or not self._known(sku):
            return False
        self.orders[order_id]["items"].append((sku, int(quantity)))
        return True

    def _handle_get_product_by_sku(self, sku) -> ProductDetails | None:
        return self.products.get(sku)

    def _handle_create_product(self, product_details) -> str:
        if product_details.sku in self.products:
            raise ECommerceConnectorError(f"A product with SKU {product_details.sku} already exists.", status_code=409)
        self.products[product_details.sku] = product_details
        self.stock.setdefault(product_details.sku, 0)
        return product_details.entry_id or product_details.sku

    def _handle_update_product(self, sku, product_details: ProductUpdateDetails) -> bool:
        changes = {k: v for k, v in vars(product_details).items() if v is not None}
        new_sku = changes.get("sku", sku)
        if sku not in self.products or (new_sku != sku and new_sku in self.products):
            return False
        self.products[new_sku] = replace(self.products.pop(sku), **changes)
        self.stock[new_sku] = self.stock.pop(sku, 0)
        return True

    def _handle_update_stock(self, sku, quantity) -> bool:
        if sku not in self.products:
            return False
        self.stock[sku] = self.stock.get(sku, 0) + int(quantity)
        return True

    def _handle_get_admin_url_for_order_id(self, order_id) -> str:
        return ADMIN_URL.format(order_id=order_id)

    def _new_order(self, items: list[tuple[str, int]], email: Any, address: Any) -> str:
        order_id = ORDER_ID.format(number=len(self.orders) + 1)
        self.orders[order_id] = {"items": items, "email": email, "address": address}
        return order_id

    def _known(self, sku: str) -> bool:
        return self._open_catalog or sku in self.products
