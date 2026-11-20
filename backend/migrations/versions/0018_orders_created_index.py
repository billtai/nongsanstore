"""Chỉ mục thời gian tạo đơn cho báo cáo quản trị.

Revision ID: 0018_orders_created_index
Revises: 0017_preorder_expiry_index
"""

from alembic import op

revision      = "0018_orders_created_index"
down_revision = "0017_preorder_expiry_index"
branch_labels = None
depends_on    = None


def upgrade():
    """Tạo chỉ mục created_at; đầu vào bảng orders, đầu ra thống kê theo kỳ nhanh hơn. Ví dụ: đếm đơn tháng hiện tại."""
    op.create_index("ix_orders_created_at", "orders", ["created_at"])


def downgrade():
    """Gỡ chỉ mục; đầu vào schema 0018, đầu ra schema 0017. Ví dụ: rollback báo cáo."""
    op.drop_index("ix_orders_created_at", table_name="orders")
