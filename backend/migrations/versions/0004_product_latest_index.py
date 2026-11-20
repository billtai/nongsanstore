"""Index for the newest visible products.

Revision ID: 0004_product_latest_index
Revises: 0003_product_slug
"""

from alembic import op

revision      = "0004_product_latest_index"
down_revision = "0003_product_slug"
branch_labels = None
depends_on    = None


def upgrade():
    """Tăng tốc lấy sản phẩm công khai mới nhất; đầu vào bảng products, đầu ra index; ví dụ GET /products?limit=3."""
    op.create_index("ix_products_visible_created_id", "products", ["is_visible", "created_at", "id"], unique=False)


def downgrade():
    """Gỡ index danh sách mới nhất; đầu vào bảng products, đầu ra bảng không có index này; ví dụ quay về 0003."""
    op.drop_index("ix_products_visible_created_id", table_name="products")
