"""Chỉ mục thời gian nhập lô cho cảnh báo tồn lâu.

Revision ID: 0019_batch_created_index
Revises: 0018_orders_created_index
"""

from alembic import op

revision      = "0019_batch_created_index"
down_revision = "0018_orders_created_index"
branch_labels = None
depends_on    = None


def upgrade():
    """Tạo chỉ mục created_at; đầu vào bảng produce_batches, đầu ra lọc lô nhập quá 72 giờ nhanh hơn. Ví dụ: tìm 10 lô cũ nhất còn tồn."""
    op.create_index("ix_batches_created_at", "produce_batches", ["created_at"])


def downgrade():
    """Gỡ chỉ mục; đầu vào schema 0019, đầu ra schema 0018. Ví dụ: rollback thống kê tồn kho."""
    op.drop_index("ix_batches_created_at", table_name="produce_batches")
