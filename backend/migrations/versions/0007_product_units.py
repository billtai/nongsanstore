"""Manage product units in a table.

Revision ID: 0007_product_units
Revises: 0006_merge_product_and_quote
"""

from alembic import op
import sqlalchemy as sa

revision      = "0007_product_units"
down_revision = "0006_merge_product_and_quote"
branch_labels = None
depends_on    = None


def upgrade():
    """Tạo đơn vị và chuyển ràng buộc sản phẩm sang FK; ví dụ kg/hộp/bó hiện có vẫn dùng được."""
    units = op.create_table(
        "product_units",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("code", sa.String(10), nullable=False, unique=True),
        sa.Column("allows_fraction", sa.Boolean(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
    )
    op.bulk_insert(units, [
        {"code" : "kg", "allows_fraction" : True, "is_active" : True},
        {"code" : "hộp", "allows_fraction" : False, "is_active" : True},
        {"code" : "bó", "allows_fraction" : False, "is_active" : True},
    ])
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("ck_product_unit", type_="check")
        batch.create_foreign_key("fk_products_unit", "product_units", ["unit"], ["code"])


def downgrade():
    """Khôi phục ba đơn vị cố định; chỉ chạy khi sản phẩm không dùng đơn vị mới."""
    with op.batch_alter_table("products") as batch:
        batch.drop_constraint("fk_products_unit", type_="foreignkey")
        batch.create_check_constraint("ck_product_unit", "unit IN ('kg', 'bó', 'hộp')")
    op.drop_table("product_units")
