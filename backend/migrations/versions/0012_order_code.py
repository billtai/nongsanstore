"""Thêm mã đơn công khai không chứa số thứ tự nội bộ.

Revision ID: 0012_order_code
Revises: 0011_sepay_bank_qr
"""

from secrets import token_hex

from alembic import op
import sqlalchemy as sa

revision      = "0012_order_code"
down_revision = "0011_sepay_bank_qr"
branch_labels = None
depends_on    = None


def upgrade():
    """Tạo mã ngẫu nhiên cho đơn cũ rồi bắt buộc duy nhất. Đầu vào: bảng orders 0011; đầu ra: order_code; ví dụ VN-A1B2..."""
    op.add_column("orders", sa.Column("order_code", sa.String(32), nullable=True))
    connection = op.get_bind()
    order_ids  = connection.execute(sa.text("SELECT id FROM orders")).scalars()
    for order_id in order_ids:
        connection.execute(
            sa.text("UPDATE orders SET order_code = :code WHERE id = :id"),
            {"code" : f"VN-{token_hex(12).upper()}", "id" : order_id},
        )
    with op.batch_alter_table("orders") as batch:
        batch.alter_column("order_code", existing_type=sa.String(32), nullable=False)
        batch.create_index("ix_orders_order_code", ["order_code"], unique=True)


def downgrade():
    """Gỡ mã công khai. Đầu vào: bảng orders 0012; đầu ra: schema 0011; ví dụ rollback migration."""
    with op.batch_alter_table("orders") as batch:
        batch.drop_index("ix_orders_order_code")
        batch.drop_column("order_code")
