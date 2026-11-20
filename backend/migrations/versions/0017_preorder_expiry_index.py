"""Tăng tốc tìm đơn đặt trước quá hạn.

Revision ID: 0017_preorder_expiry_index
Revises: 0016_preorder_price_approval
"""

from alembic import op

revision      = "0017_preorder_expiry_index"
down_revision = "0016_preorder_price_approval"
branch_labels = None
depends_on    = None


def upgrade():
    """Tạo chỉ mục hạn duyệt; đầu vào: bảng orders, đầu ra: truy vấn status và thời hạn nhanh hơn. Ví dụ: dọn đơn chờ quá 24 giờ."""
    op.create_index("ix_orders_price_expiry", "orders", ["status", "price_proposed_at"])


def downgrade():
    """Gỡ chỉ mục; đầu vào: schema 0017, đầu ra: schema 0016. Ví dụ: rollback migration."""
    op.drop_index("ix_orders_price_expiry", table_name="orders")
