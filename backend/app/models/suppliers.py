"""Nhà cung cấp và đơn nhập hàng; đơn đã nhận gắn với các lô kho."""

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import relationship

from app import db
from app.models.base import now_utc


class Supplier(db.Model):
    """Lưu thông tin liên hệ nhà cung cấp; ví dụ một trang trại có nhiều đơn nhập."""

    __tablename__ = "suppliers"

    id           = db.Column(db.Integer, primary_key=True)
    name         = db.Column(db.String(180), nullable=False)
    contact_name = db.Column(db.String(120), nullable=False, default="")
    phone        = db.Column(db.String(30), nullable=False, default="")
    email        = db.Column(db.String(180), nullable=False, default="")
    address      = db.Column(db.String(255), nullable=False, default="")
    tax_code     = db.Column(db.String(30), nullable=False, default="")
    notes        = db.Column(db.Text, nullable=False, default="")
    is_active    = db.Column(db.Boolean, nullable=False, default=True)
    created_at   = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    purchases    = relationship("PurchaseOrder", back_populates="supplier")

    __table_args__ = (Index("ix_suppliers_name", "name"),)


class PurchaseOrder(db.Model):
    """Đơn mua từ nhà cung cấp; chỉ trạng thái received mới tạo tồn kho."""

    __tablename__ = "purchase_orders"

    id            = db.Column(db.Integer, primary_key=True)
    supplier_id   = db.Column(db.Integer, ForeignKey("suppliers.id"), nullable=False, index=True)
    status        = db.Column(db.String(20), nullable=False, default="draft")
    expected_date = db.Column(db.Date)
    notes         = db.Column(db.Text, nullable=False, default="")
    total_vnd     = db.Column(db.BigInteger, nullable=False, default=0)
    created_at    = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    ordered_at    = db.Column(db.DateTime(timezone=True))
    received_at   = db.Column(db.DateTime(timezone=True))
    supplier      = relationship("Supplier", back_populates="purchases")
    items         = relationship("PurchaseOrderItem", back_populates="purchase", cascade="all, delete-orphan", order_by="PurchaseOrderItem.id")

    __table_args__ = (
        CheckConstraint("status IN ('draft', 'ordered', 'received', 'cancelled')", name="ck_purchase_status"),
        CheckConstraint("total_vnd >= 0", name="ck_purchase_total"),
        Index("ix_purchase_orders_status_created", "status", "created_at"),
    )


class PurchaseOrderItem(db.Model):
    """Một sản phẩm và giá vốn trong đơn nhập, lưu ảnh chụp tên/đơn vị khi đặt."""

    __tablename__ = "purchase_order_items"

    id             = db.Column(db.Integer, primary_key=True)
    purchase_id    = db.Column(db.Integer, ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False, index=True)
    product_id     = db.Column(db.Integer, ForeignKey("products.id"), nullable=False)
    product_name   = db.Column(db.String(180), nullable=False)
    unit           = db.Column(db.String(10), nullable=False)
    quantity       = db.Column(db.Numeric(12, 3), nullable=False)
    unit_cost_vnd  = db.Column(db.Integer, nullable=False)
    line_total_vnd = db.Column(db.BigInteger, nullable=False)
    batch_id       = db.Column(db.Integer, ForeignKey("produce_batches.id"))
    purchase       = relationship("PurchaseOrder", back_populates="items")
    product        = relationship("Product")
    batch          = relationship("ProduceBatch")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="ck_purchase_item_quantity"),
        CheckConstraint("unit_cost_vnd >= 0 AND line_total_vnd >= 0", name="ck_purchase_item_cost"),
    )
