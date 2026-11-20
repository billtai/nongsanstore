"""Lưu dấu vết admin đối soát thủ công khoản chuyển ngân hàng.

Revision ID: 0021_bank_manual_confirmation
Revises: 0020_bank_transfer_reported
"""

from alembic import op
import sqlalchemy as sa

revision      = "0021_bank_manual_confirmation"
down_revision = "0020_bank_transfer_reported"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm người và thời điểm xác nhận; đầu vào schema 0020, đầu ra schema 0021. Ví dụ: admin đối soát đơn QR."""
    op.add_column("orders", sa.Column("bank_payment_confirmed_at", sa.DateTime(timezone=True)))
    op.add_column("orders", sa.Column("bank_payment_confirmed_by", sa.Integer(), sa.ForeignKey("customers.id")))


def downgrade():
    """Bỏ dấu vết xác nhận tay; đầu vào schema 0021, đầu ra schema 0020. Ví dụ: rollback migration."""
    op.drop_column("orders", "bank_payment_confirmed_by")
    op.drop_column("orders", "bank_payment_confirmed_at")
