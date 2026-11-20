"""Keep the confirmed quote ID to prevent duplicate orders.

Revision ID: 0003_order_quote
Revises: 0002_product_images
"""

from alembic import op
import sqlalchemy as sa

revision      = "0003_order_quote"
down_revision = "0002_product_images"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm mã báo giá duy nhất cho đơn mới; đơn cũ được phép NULL."""
    op.add_column("orders", sa.Column("quote_id", sa.String(1024), nullable=True))
    op.create_unique_constraint("uq_orders_quote_id", "orders", ["quote_id"])


def downgrade():
    """Bỏ ràng buộc chống đặt trùng theo mã báo giá."""
    op.drop_constraint("uq_orders_quote_id", "orders", type_="unique")
    op.drop_column("orders", "quote_id")
