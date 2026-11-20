"""Merge the product and order quote migration branches.

Revision ID: 0006_merge_product_and_quote
Revises: 0005_product_category, 0003_order_quote
"""

revision      = "0006_merge_product_and_quote"
down_revision = ("0005_product_category", "0003_order_quote")
branch_labels = None
depends_on    = None


def upgrade():
    """Hợp nhất hai nhánh migration; đầu vào hai revision, đầu ra một head; ví dụ flask db upgrade."""
    pass


def downgrade():
    """Tách lại hai nhánh migration; đầu vào head hợp nhất, đầu ra hai revision cha; ví dụ downgrade về nhánh trước."""
    pass
