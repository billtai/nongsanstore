"""Lưu giá dự kiến và đề xuất mới của đơn đặt trước.

Revision ID: 0016_preorder_price_approval
Revises: 0015_preorder_classification
"""

from alembic import op
import sqlalchemy as sa

revision      = "0016_preorder_price_approval"
down_revision = "0015_preorder_classification"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm trạng thái và hai mốc giá; đầu vào schema 0015, đầu ra giá so sánh cho đơn cũ và mới. Ví dụ: đơn cũ có initial_total_vnd bằng tổng lúc đặt."""
    for name in ("initial_subtotal_vnd", "initial_discount_vnd", "initial_total_vnd", "proposed_subtotal_vnd", "proposed_discount_vnd", "proposed_total_vnd"):
        op.add_column("orders", sa.Column(name, sa.Integer(), nullable=True))
    op.add_column("orders", sa.Column("price_proposed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("orders", sa.Column("price_approved_at", sa.DateTime(timezone=True), nullable=True))
    for name in ("initial_unit_price_vnd", "initial_line_total_vnd", "proposed_unit_price_vnd", "proposed_line_total_vnd"):
        op.add_column("order_items", sa.Column(name, sa.Integer(), nullable=True))
    op.execute("UPDATE orders SET initial_subtotal_vnd = subtotal_vnd, initial_discount_vnd = discount_vnd, initial_total_vnd = total_vnd WHERE is_preorder = true")
    op.execute("UPDATE order_items SET initial_unit_price_vnd = unit_price_vnd, initial_line_total_vnd = line_total_vnd WHERE is_preorder = true")
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("ck_order_status", type_="check")
        batch.create_check_constraint("ck_order_status", "status IN ('preordered', 'awaiting_price_approval', 'pending', 'confirmed', 'preparing', 'delivering', 'completed', 'cancelled')")


def downgrade():
    """Gỡ bước duyệt giá; đầu vào schema 0016, đầu ra schema 0015. Ví dụ: rollback khi không còn đơn đang chờ duyệt giá."""
    with op.batch_alter_table("orders") as batch:
        batch.drop_constraint("ck_order_status", type_="check")
        batch.create_check_constraint("ck_order_status", "status IN ('preordered', 'pending', 'confirmed', 'preparing', 'delivering', 'completed', 'cancelled')")
    for name in ("price_approved_at", "price_proposed_at", "proposed_total_vnd", "proposed_discount_vnd", "proposed_subtotal_vnd", "initial_total_vnd", "initial_discount_vnd", "initial_subtotal_vnd"):
        op.drop_column("orders", name)
    for name in ("proposed_line_total_vnd", "proposed_unit_price_vnd", "initial_line_total_vnd", "initial_unit_price_vnd"):
        op.drop_column("order_items", name)
