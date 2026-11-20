"""Initial schema for the agricultural store.

Revision ID: 0001_initial
Revises:
"""

from alembic import op
import sqlalchemy as sa

revision      = "0001_initial"
down_revision = None
branch_labels = None
depends_on    = None


def upgrade():
    """Tạo bảng và ràng buộc ban đầu; chỉ chạy khi người vận hành gọi flask db upgrade."""
    op.create_table(
        "customers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("phone", sa.String(30), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("role IN ('customer', 'admin')", name="ck_customer_role"),
    )
    op.create_index("ix_customers_email", "customers", ["email"])
    op.create_table(
        "products",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("description", sa.Text(), nullable=False),
        sa.Column("unit", sa.String(10), nullable=False),
        sa.Column("price_vnd", sa.Integer(), nullable=False),
        sa.Column("image_url", sa.String(500)),
        sa.Column("is_visible", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("unit IN ('kg', 'bó', 'hộp')", name="ck_product_unit"),
        sa.CheckConstraint("price_vnd >= 0", name="ck_product_price"),
    )
    op.create_table(
        "produce_batches",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("batch_code", sa.String(80), nullable=False, unique=True),
        sa.Column("growing_region", sa.String(180), nullable=False),
        sa.Column("origin", sa.String(255), nullable=False),
        sa.Column("harvest_date", sa.Date(), nullable=False),
        sa.Column("remaining_quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("remaining_quantity >= 0", name="ck_batch_quantity"),
    )
    op.create_index("ix_produce_batches_product_id", "produce_batches", ["product_id"])
    op.create_table(
        "discount_codes",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(50), nullable=False, unique=True),
        sa.Column("kind", sa.String(10), nullable=False),
        sa.Column("value", sa.Integer(), nullable=False),
        sa.Column("min_subtotal_vnd", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(timezone=True)),
        sa.Column("ends_at", sa.DateTime(timezone=True)),
        sa.Column("usage_limit", sa.Integer()),
        sa.Column("used_count", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.CheckConstraint("kind IN ('fixed', 'percent')", name="ck_discount_kind"),
        sa.CheckConstraint("value > 0", name="ck_discount_value"),
        sa.CheckConstraint("kind != 'percent' OR value <= 100", name="ck_discount_percent"),
        sa.CheckConstraint("min_subtotal_vnd >= 0", name="ck_discount_minimum"),
        sa.CheckConstraint("usage_limit IS NULL OR usage_limit > 0", name="ck_discount_limit"),
        sa.CheckConstraint("used_count >= 0", name="ck_discount_used"),
    )
    op.create_table(
        "orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("customer_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("recipient_name", sa.String(120), nullable=False),
        sa.Column("recipient_phone", sa.String(30), nullable=False),
        sa.Column("delivery_address", sa.String(500), nullable=False),
        sa.Column("status", sa.String(30), nullable=False),
        sa.Column("payment_method", sa.String(10), nullable=False),
        sa.Column("subtotal_vnd", sa.Integer(), nullable=False),
        sa.Column("discount_vnd", sa.Integer(), nullable=False),
        sa.Column("total_vnd", sa.Integer(), nullable=False),
        sa.Column("discount_code", sa.String(50)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("status IN ('pending', 'confirmed', 'preparing', 'delivering', 'completed', 'cancelled')", name="ck_order_status"),
        sa.CheckConstraint("payment_method = 'cod'", name="ck_order_cod"),
        sa.CheckConstraint("subtotal_vnd >= 0 AND discount_vnd >= 0 AND total_vnd >= 0", name="ck_order_money"),
    )
    op.create_index("ix_orders_customer_id", "orders", ["customer_id"])
    op.create_index("ix_order_customer_created", "orders", ["customer_id", "created_at"])
    op.create_table(
        "order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("product_name", sa.String(180), nullable=False),
        sa.Column("unit", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_price_vnd", sa.Integer(), nullable=False),
        sa.Column("line_total_vnd", sa.Integer(), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_order_item_quantity"),
    )
    op.create_index("ix_order_items_order_id", "order_items", ["order_id"])
    op.create_table(
        "order_batch_allocations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("item_id", sa.Integer(), sa.ForeignKey("order_items.id"), nullable=False),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("produce_batches.id"), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.CheckConstraint("quantity > 0", name="ck_allocation_quantity"),
    )
    op.create_table(
        "order_status_history",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("order_id", sa.Integer(), sa.ForeignKey("orders.id"), nullable=False),
        sa.Column("from_status", sa.String(30)),
        sa.Column("to_status", sa.String(30), nullable=False),
        sa.Column("actor_id", sa.Integer(), sa.ForeignKey("customers.id"), nullable=False),
        sa.Column("reason", sa.String(500)),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade():
    """Gỡ schema nếu người vận hành yêu cầu downgrade; thao tác này xóa dữ liệu."""
    op.drop_table("order_status_history")
    op.drop_table("order_batch_allocations")
    op.drop_index("ix_order_items_order_id", table_name="order_items")
    op.drop_table("order_items")
    op.drop_index("ix_order_customer_created", table_name="orders")
    op.drop_index("ix_orders_customer_id", table_name="orders")
    op.drop_table("orders")
    op.drop_table("discount_codes")
    op.drop_index("ix_produce_batches_product_id", table_name="produce_batches")
    op.drop_table("produce_batches")
    op.drop_table("products")
    op.drop_index("ix_customers_email", table_name="customers")
    op.drop_table("customers")
