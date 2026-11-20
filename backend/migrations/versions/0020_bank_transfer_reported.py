"""Ghi nhận thời điểm khách báo đã chuyển khoản QR.

Revision ID: 0020_bank_transfer_reported
Revises: 0019_batch_created_index
"""

from alembic import op
import sqlalchemy as sa

revision      = "0020_bank_transfer_reported"
down_revision = "0019_batch_created_index"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm thời điểm khách báo chuyển khoản; đầu vào schema 0019, đầu ra schema 0020. Ví dụ: NULL nếu chưa báo."""
    op.add_column("orders", sa.Column("bank_transfer_reported_at", sa.DateTime(timezone=True)))


def downgrade():
    """Bỏ thời điểm báo chuyển khoản; đầu vào schema 0020, đầu ra schema 0019. Ví dụ: rollback migration."""
    op.drop_column("orders", "bank_transfer_reported_at")
