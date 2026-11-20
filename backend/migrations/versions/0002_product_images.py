"""Add product detail images.

Revision ID: 0002_product_images
Revises: 0001_initial
"""

from alembic import op
import sqlalchemy as sa

revision      = "0002_product_images"
down_revision = "0001_initial"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm bảng ảnh chi tiết; ảnh chính vẫn ở products.image_url."""
    op.create_table(
        "product_images",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("product_id", sa.Integer(), sa.ForeignKey("products.id", ondelete="CASCADE"), nullable=False),
        sa.Column("image_url", sa.String(500), nullable=False),
    )
    op.create_index("ix_product_images_product_id", "product_images", ["product_id"])


def downgrade():
    """Gỡ bảng ảnh chi tiết; thao tác này xóa danh sách ảnh chi tiết."""
    op.drop_index("ix_product_images_product_id", table_name="product_images")
    op.drop_table("product_images")
