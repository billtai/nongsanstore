"""Thêm trạng thái và tham chiếu giao dịch MoMo Test cho đơn hàng.

Revision ID: 0008_momo_test
Revises: 0007_product_units
"""

from alembic import op
import sqlalchemy as sa

revision      = "0008_momo_test"
down_revision = "0007_product_units"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm dữ liệu thanh toán; đầu vào schema hiện tại, đầu ra orders hỗ trợ MoMo; ví dụ đơn COD cũ giữ unpaid."""
    op.add_column("orders", sa.Column("payment_status", sa.String(20), nullable=False, server_default="unpaid"))
    op.add_column("orders", sa.Column("momo_order_id", sa.String(80)))
    op.add_column("orders", sa.Column("momo_request_id", sa.String(80)))
    op.add_column("orders", sa.Column("momo_pay_url", sa.Text()))
    op.add_column("orders", sa.Column("momo_trans_id", sa.String(80)))
    op.create_unique_constraint("uq_orders_momo_order_id", "orders", ["momo_order_id"])
    op.drop_constraint("ck_order_cod", "orders", type_="check")
    op.create_check_constraint("ck_order_payment_method", "orders", "payment_method IN ('cod', 'momo')")
    op.create_check_constraint("ck_order_payment_status", "orders", "payment_status IN ('unpaid', 'pending', 'paid', 'failed')")


def downgrade():
    """Gỡ hỗ trợ MoMo khi không còn đơn MoMo; đầu vào schema mới, đầu ra ràng buộc COD cũ."""
    op.drop_constraint("ck_order_payment_status", "orders", type_="check")
    op.drop_constraint("ck_order_payment_method", "orders", type_="check")
    op.create_check_constraint("ck_order_cod", "orders", "payment_method = 'cod'")
    op.drop_constraint("uq_orders_momo_order_id", "orders", type_="unique")
    for column in ("momo_trans_id", "momo_pay_url", "momo_request_id", "momo_order_id", "payment_status"):
        op.drop_column("orders", column)
