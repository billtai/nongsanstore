"""Add unique public product slugs.

Revision ID: 0003_product_slug
Revises: 0002_product_images
"""

import re
import unicodedata

from alembic import op
import sqlalchemy as sa

revision      = "0003_product_slug"
down_revision = "0002_product_images"
branch_labels = None
depends_on    = None


def upgrade():
    """Thêm slug và điền dữ liệu cũ; đầu vào bảng products, đầu ra slug duy nhất; ví dụ tên trùng thêm hậu tố -2."""
    op.add_column("products", sa.Column("slug", sa.String(220), nullable=True))
    connection = op.get_bind()
    rows       = connection.execute(sa.text("SELECT id, name FROM products ORDER BY id")).all()
    used       = set()
    for product_id, name in rows:
        normalized = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
        base       = re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", normalized.encode("ascii", "ignore").decode("ascii").lower())).strip("-") or "san-pham"
        slug       = base
        suffix     = 2
        while slug in used:
            slug   = f"{base}-{suffix}"
            suffix += 1
        used.add(slug)
        connection.execute(sa.text("UPDATE products SET slug = :slug WHERE id = :id"), {"slug" : slug, "id" : product_id})
    op.alter_column("products", "slug", nullable=False)
    op.create_index("ix_products_slug", "products", ["slug"], unique=True)


def downgrade():
    """Gỡ slug; đầu vào bảng products, đầu ra bảng không có slug; ví dụ quay về migration 0002."""
    op.drop_index("ix_products_slug", table_name="products")
    op.drop_column("products", "slug")
