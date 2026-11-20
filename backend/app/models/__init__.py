"""Xuất các model cho API và Alembic; ví dụ: from app.models import Product."""

from app.models.users import Customer
from app.models.products import Product, ProduceBatch, ProductImage
from app.models.units import ProductUnit
from app.models.discounts import DiscountCode
from app.models.orders import Order, OrderItem, OrderBatchAllocation, OrderStatusHistory
from app.models.suppliers import Supplier, PurchaseOrder, PurchaseOrderItem

__all__ = ["Customer", "ProductUnit", "Product", "ProduceBatch", "ProductImage", "DiscountCode", "Order", "OrderItem", "OrderBatchAllocation", "OrderStatusHistory", "Supplier", "PurchaseOrder", "PurchaseOrderItem"]
