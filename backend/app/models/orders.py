"""Bảng dữ liệu orders; giữ nguyên tên bảng và ràng buộc migration."""

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import relationship

from app import db
from app.models.base import now_utc


class Order(db.Model):
    __tablename__ = "orders"

    id                 = db.Column(db.Integer, primary_key=True)
    order_code         = db.Column(db.String(32), nullable=False, unique=True, index=True)
    customer_id        = db.Column(db.Integer, ForeignKey("customers.id"), nullable=False, index=True)
    recipient_name     = db.Column(db.String(120), nullable=False)
    recipient_phone    = db.Column(db.String(30), nullable=False)
    delivery_address   = db.Column(db.String(500), nullable=False)
    status             = db.Column(db.String(30), nullable=False, default="pending")
    is_preorder        = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    payment_method     = db.Column(db.String(10), nullable=False, default="cod")
    payment_status     = db.Column(db.String(20), nullable=False, default="unpaid")
    momo_order_id      = db.Column(db.String(80), unique=True)
    momo_request_id    = db.Column(db.String(80))
    momo_pay_url       = db.Column(db.Text)
    momo_trans_id      = db.Column(db.String(80))
    sepay_payment_code = db.Column(db.String(40), unique=True)
    sepay_transaction_id = db.Column(db.String(80), unique=True)
    sepay_bank_code    = db.Column(db.String(30))
    sepay_account_number = db.Column(db.String(40))
    sepay_account_name = db.Column(db.String(120))
    bank_transfer_reported_at = db.Column(db.DateTime(timezone=True))
    bank_payment_confirmed_at = db.Column(db.DateTime(timezone=True))
    bank_payment_confirmed_by = db.Column(db.Integer, ForeignKey("customers.id"))
    subtotal_vnd       = db.Column(db.Integer, nullable=False)
    discount_vnd       = db.Column(db.Integer, nullable=False, default=0)
    total_vnd          = db.Column(db.Integer, nullable=False)
    discount_code      = db.Column(db.String(50))
    initial_subtotal_vnd = db.Column(db.Integer)
    initial_discount_vnd = db.Column(db.Integer)
    initial_total_vnd    = db.Column(db.Integer)
    proposed_subtotal_vnd = db.Column(db.Integer)
    proposed_discount_vnd = db.Column(db.Integer)
    proposed_total_vnd    = db.Column(db.Integer)
    price_proposed_at    = db.Column(db.DateTime(timezone=True))
    price_approved_at    = db.Column(db.DateTime(timezone=True))
    quote_id           = db.Column(db.String(1024), unique=True)
    created_at         = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    customer           = relationship("Customer", foreign_keys=[customer_id])
    items              = relationship("OrderItem", back_populates="order", lazy="selectin")
    status_history     = relationship("OrderStatusHistory", back_populates="order", lazy="selectin", order_by="OrderStatusHistory.id")

    __table_args__ = (
        CheckConstraint("status IN ('preordered', 'awaiting_price_approval', 'pending', 'confirmed', 'preparing', 'delivering', 'completed', 'cancelled')", name="ck_order_status"),
        CheckConstraint("payment_method IN ('cod', 'momo', 'sepay', 'sepay_bank')", name="ck_order_payment_method"),
        CheckConstraint("payment_status IN ('unpaid', 'pending', 'paid', 'failed')", name="ck_order_payment_status"),
        CheckConstraint("subtotal_vnd >= 0 AND discount_vnd >= 0 AND total_vnd >= 0", name="ck_order_money"),
        Index("ix_order_customer_created", "customer_id", "created_at"),
        Index("ix_orders_created_at", "created_at"),
        Index("ix_orders_status_created_at", "status", "created_at"),
        Index("ix_orders_preorder_created", "is_preorder", "id"),
        Index("ix_orders_price_expiry", "status", "price_proposed_at"),
    )


class OrderItem(db.Model):
    __tablename__ = "order_items"

    id           = db.Column(db.Integer, primary_key=True)
    order_id     = db.Column(db.Integer, ForeignKey("orders.id"), nullable=False, index=True)
    product_id   = db.Column(db.Integer, ForeignKey("products.id"), nullable=False)
    product_name = db.Column(db.String(180), nullable=False)
    unit         = db.Column(db.String(10), nullable=False)
    quantity     = db.Column(db.Numeric(12, 3), nullable=False)
    unit_price_vnd = db.Column(db.Integer, nullable=False)
    line_total_vnd = db.Column(db.Integer, nullable=False)
    is_preorder  = db.Column(db.Boolean, nullable=False, default=False, server_default="false")
    initial_unit_price_vnd = db.Column(db.Integer)
    initial_line_total_vnd = db.Column(db.Integer)
    proposed_unit_price_vnd = db.Column(db.Integer)
    proposed_line_total_vnd = db.Column(db.Integer)
    order        = relationship("Order", back_populates="items")
    allocations  = relationship("OrderBatchAllocation", back_populates="item", lazy="selectin")

    __table_args__ = (CheckConstraint("quantity > 0", name="ck_order_item_quantity"),)


class OrderBatchAllocation(db.Model):
    __tablename__ = "order_batch_allocations"

    id       = db.Column(db.Integer, primary_key=True)
    item_id  = db.Column(db.Integer, ForeignKey("order_items.id"), nullable=False)
    batch_id = db.Column(db.Integer, ForeignKey("produce_batches.id"), nullable=False)
    quantity = db.Column(db.Numeric(12, 3), nullable=False)
    item     = relationship("OrderItem", back_populates="allocations")

    __table_args__ = (CheckConstraint("quantity > 0", name="ck_allocation_quantity"),)


class OrderStatusHistory(db.Model):
    __tablename__ = "order_status_history"

    id         = db.Column(db.Integer, primary_key=True)
    order_id   = db.Column(db.Integer, ForeignKey("orders.id"), nullable=False)
    from_status = db.Column(db.String(30))
    to_status   = db.Column(db.String(30), nullable=False)
    actor_id    = db.Column(db.Integer, ForeignKey("customers.id"), nullable=False)
    reason      = db.Column(db.String(500))
    created_at  = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    order       = relationship("Order", back_populates="status_history")
