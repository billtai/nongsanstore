"""Thêm nhà cung cấp và đơn nhập hàng.

Revision ID: 0009_suppliers_purchases
Revises: 0008_momo_test
"""

from alembic import op
import sqlalchemy as sa

revision      = "0009_suppliers_purchases"
down_revision = "0008_momo_test"
branch_labels = None
depends_on    = None


def upgrade():
    """Tạo ba bảng; đầu vào schema 0008, đầu ra có thể đặt và nhận hàng từ nhà cung cấp."""
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(180), nullable=False),
        sa.Column("contact_name", sa.String(120), nullable=False, server_default=""),
        sa.Column("phone", sa.String(30), nullable=False, server_default=""),
        sa.Column("email", sa.String(180), nullable=False, server_default=""),
        sa.Column("address", sa.String(255), nullable=False, server_default=""),
        sa.Column("tax_code", sa.String(30), nullable=False, server_default=""),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_suppliers_name", "suppliers", ["name"])
    op.create_table(
        "purchase_orders",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("supplier_id", sa.Integer(), sa.ForeignKey("suppliers.id"), nullable=False),
        sa.Column("status", sa.String(20), nullable=False, server_default="draft"),
        sa.Column("expected_date", sa.Date()),
        sa.Column("notes", sa.Text(), nullable=False, server_default=""),
        sa.Column("total_vnd", sa.BigInteger(), nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("ordered_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True)),
        sa.CheckConstraint("status IN ('draft', 'ordered', 'received', 'cancelled')", name="ck_purchase_status"),
        sa.CheckConstraint("total_vnd >= 0", name="ck_purchase_total"),
    )
    op.create_index("ix_purchase_orders_supplier_id", "purchase_orders", ["supplier_id"])
    op.create_index("ix_purchase_orders_status_created", "purchase_orders", ["status", "created_at"])
    op.create_table(
        "purchase_order_items",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("purchase_id", sa.Integer(), sa.ForeignKey("purchase_orders.id", ondelete="CASCADE"), nullable=False),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id"), nullable=False),
        sa.Column("product_name", sa.String(180), nullable=False),
        sa.Column("unit", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Numeric(12, 3), nullable=False),
        sa.Column("unit_cost_vnd", sa.Integer(), nullable=False),
        sa.Column("line_total_vnd", sa.BigInteger(), nullable=False),
        sa.Column("batch_id", sa.Integer(), sa.ForeignKey("produce_batches.id")),
        sa.CheckConstraint("quantity > 0", name="ck_purchase_item_quantity"),
        sa.CheckConstraint("unit_cost_vnd >= 0 AND line_total_vnd >= 0", name="ck_purchase_item_cost"),
    )
    op.create_index("ix_purchase_order_items_purchase_id", "purchase_order_items", ["purchase_id"])


def downgrade():
    """Gỡ bảng đơn nhập và nhà cung cấp; ví dụ rollback từ 0009 về 0008."""
    op.drop_table("purchase_order_items")
    op.drop_table("purchase_orders")
    op.drop_table("suppliers")
