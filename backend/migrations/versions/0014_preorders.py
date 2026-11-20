"""Lưu dòng đặt trước và trạng thái chờ hàng.

Revision ID: 0014_preorders
Revises: 0013_batch_visibility
"""

from alembic import op
import sqlalchemy as sa

revision      = "0014_preorders"
down_revision = "0013_batch_visibility"
branch_labels = None
depends_on    = None


def upgrade():
    """Bổ sung cờ đặt trước và trạng thái đơn. Đầu vào: schema 0013; đầu ra: đơn có thể chờ hàng. Ví dụ: sản phẩm tồn 0 tạo dòng is_preorder=true."""
    op.add_column("order_items", sa.Column("is_preorder", sa.Boolean(), nullable=False, server_default=sa.false()))
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("ck_order_status", type_="check")
        batch.create_check_constraint("ck_order_status", "status IN ('preordered', 'pending', 'confirmed', 'preparing', 'delivering', 'completed', 'cancelled')")


def downgrade():
    """Gỡ đặt trước khi không còn đơn chờ hàng. Đầu vào: schema 0014; đầu ra: schema 0013. Ví dụ: rollback thử nghiệm."""
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("ck_order_status", type_="check")
        batch.create_check_constraint("ck_order_status", "status IN ('pending', 'confirmed', 'preparing', 'delivering', 'completed', 'cancelled')")
    op.drop_column("order_items", "is_preorder")
