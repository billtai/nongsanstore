"""Thêm thanh toán chuyển khoản SePay.

Revision ID: 0010_sepay_bank_transfer
Revises: 0009_suppliers_purchases
"""

from alembic import op
import sqlalchemy as sa

revision      = "0010_sepay_bank_transfer"
down_revision = "0009_suppliers_purchases"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm thông tin chuyển khoản đã chốt trên đơn; đầu vào/đầu ra: schema; ví dụ đơn SePay có mã NS12ABCD."""
    op.add_column("orders", sa.Column("sepay_payment_code", sa.String(40)))
    op.add_column("orders", sa.Column("sepay_transaction_id", sa.String(80)))
    op.create_unique_constraint("uq_orders_sepay_payment_code", "orders", ["sepay_payment_code"])
    op.create_unique_constraint("uq_orders_sepay_transaction_id", "orders", ["sepay_transaction_id"])
    op.drop_constraint("ck_order_payment_method", "orders", type_="check")
    op.create_check_constraint("ck_order_payment_method", "orders", "payment_method IN ('cod', 'momo', 'sepay')")


def downgrade():
    """Gỡ schema SePay; đầu vào/đầu ra: schema; ví dụ quay về revision 0009 khi không còn đơn SePay."""
    op.drop_constraint("ck_order_payment_method", "orders", type_="check")
    op.create_check_constraint("ck_order_payment_method", "orders", "payment_method IN ('cod', 'momo')")
    op.drop_constraint("uq_orders_sepay_transaction_id", "orders", type_="unique")
    op.drop_constraint("uq_orders_sepay_payment_code", "orders", type_="unique")
    for name in ("sepay_transaction_id", "sepay_payment_code"):
        op.drop_column("orders", name)
