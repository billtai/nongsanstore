"""Chỉ mục cho báo cáo doanh thu theo ngày.

Revision ID: 0022_orders_status_created_index
Revises: 0021_bank_manual_confirmation
"""

from alembic import op

revision      = "0022_orders_status_created_index"
down_revision = "0021_bank_manual_confirmation"
branch_labels = None
depends_on    = None


def upgrade():
    """Tạo chỉ mục status/created_at; đầu vào bảng orders, đầu ra lọc đơn đã giao nhanh hơn. Ví dụ: báo cáo doanh thu năm nay."""
    op.create_index("ix_orders_status_created_at", "orders", ["status", "created_at"])


def downgrade():
    """Gỡ chỉ mục; đầu vào schema 0022, đầu ra schema 0021. Ví dụ: rollback migration báo cáo."""
    op.drop_index("ix_orders_status_created_at", table_name="orders")
