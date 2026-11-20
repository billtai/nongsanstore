"""Add product categories.

Revision ID: 0005_product_category
Revises: 0004_product_latest_index
"""

from alembic import op
import sqlalchemy as sa

revision      = "0005_product_category"
down_revision = "0004_product_latest_index"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm danh mục cho sản phẩm hiện có; đầu vào bảng products, đầu ra category; ví dụ rau mẫu vào Rau củ quả."""
    op.add_column("products", sa.Column("category", sa.String(80), nullable=False, server_default="Rau củ quả"))
    op.create_index("ix_products_visible_category_created", "products", ["is_visible", "category", "created_at", "id"], unique=False)


def downgrade():
    """Gỡ danh mục; đầu vào bảng products, đầu ra bảng không có category; ví dụ quay về 0004."""
    op.drop_index("ix_products_visible_category_created", table_name="products")
    op.drop_column("products", "category")
