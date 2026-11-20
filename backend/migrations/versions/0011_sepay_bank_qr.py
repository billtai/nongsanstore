"""Thêm QR chuyển khoản trực tiếp cho webhook ngân hàng SePay.

Revision ID: 0011_sepay_bank_qr
Revises: 0010_sepay_bank_transfer
"""

from alembic import op
import sqlalchemy as sa

revision      = "0011_sepay_bank_qr"
down_revision = "0010_sepay_bank_transfer"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm snapshot tài khoản nhận; đầu vào schema 0010, đầu ra đơn QR ngân hàng; ví dụ sepay_bank."""
    op.add_column("orders", sa.Column("sepay_bank_code", sa.String(30)))
    op.add_column("orders", sa.Column("sepay_account_number", sa.String(40)))
    op.add_column("orders", sa.Column("sepay_account_name", sa.String(120)))
    op.drop_constraint("ck_order_payment_method", "orders", type_="check")
    op.create_check_constraint("ck_order_payment_method", "orders", "payment_method IN ('cod', 'momo', 'sepay', 'sepay_bank')")


def downgrade():
    """Gỡ QR ngân hàng; đầu vào schema 0011, đầu ra schema 0010 nếu không còn đơn sepay_bank."""
    op.drop_constraint("ck_order_payment_method", "orders", type_="check")
    op.create_check_constraint("ck_order_payment_method", "orders", "payment_method IN ('cod', 'momo', 'sepay')")
    for name in ("sepay_account_name", "sepay_account_number", "sepay_bank_code"):
        op.drop_column("orders", name)
