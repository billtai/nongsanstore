"""Giữ loại đơn đặt trước sau khi trạng thái thay đổi.

Revision ID: 0015_preorder_classification
Revises: 0014_preorders
"""

from alembic import op
import sqlalchemy as sa

revision      = "0015_preorder_classification"
down_revision = "0014_preorders"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm và điền loại đơn; đầu vào schema 0014, đầu ra cờ is_preorder. Ví dụ: đơn có dòng đặt trước được đánh dấu true."""
    op.add_column("orders", sa.Column("is_preorder", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.execute("UPDATE orders SET is_preorder = true WHERE EXISTS (SELECT 1 FROM order_items WHERE order_items.order_id = orders.id AND order_items.is_preorder = true)")
    op.create_index("ix_orders_preorder_created", "orders", ["is_preorder", "id"])


def downgrade():
    """Gỡ loại đơn; đầu vào schema 0015, đầu ra schema 0014. Ví dụ: rollback trước khi dùng bộ lọc loại đơn."""
    op.drop_index("ix_orders_preorder_created", table_name="orders")
    op.drop_column("orders", "is_preorder")
