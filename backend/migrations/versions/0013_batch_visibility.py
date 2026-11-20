"""Thêm trạng thái ẩn lô và chỉ mục tra đơn theo mã giảm giá.

Revision ID: 0013_batch_visibility
Revises: 0012_order_code
"""

from alembic import op
import sqlalchemy as sa

revision      = "0013_batch_visibility"
down_revision = "0012_order_code"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm cờ hiển thị mặc định true và index tra lịch sử; đầu vào schema 0012, đầu ra lô có thể ẩn. Ví dụ lô cũ vẫn hiện."""
    op.add_column("produce_batches", sa.Column("is_visible", sa.Boolean(), nullable=False, server_default=sa.true()))
    op.create_index("ix_orders_discount_code_created", "orders", ["discount_code", "created_at", "id"])


def downgrade():
    """Gỡ cờ và index; đầu vào schema 0013, đầu ra schema 0012. Ví dụ rollback bản triển khai."""
    op.drop_index("ix_orders_discount_code_created", table_name="orders")
    op.drop_column("produce_batches", "is_visible")
