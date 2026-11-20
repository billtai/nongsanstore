"""Quản trị products: thao tác list."""

from flask import jsonify, request
from sqlalchemy import func
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.helpers import page_args
from app.errors import ApiError
from app.models import ProduceBatch, Product
from app.products import product_data


@admin_api.get("/products")
@require_role("admin")
def admin_products():
    """Liệt kê cả sản phẩm ẩn; nhận q/visible/page/limit, trả trang sản phẩm."""
    page, limit = page_args()
    query       = db.session.query(Product)
    search      = request.args.get("q", "").strip()
    visible     = request.args.get("visible")
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if visible is not None:
        if visible not in ("true", "false"):
            raise ApiError(400, "invalid_input", "visible phải là true hoặc false.")
        query = query.filter_by(is_visible=visible == "true")
    result      = query.order_by(Product.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    product_ids = [row.id for row in result.items]
    stocks      = dict(db.session.query(ProduceBatch.product_id, func.sum(ProduceBatch.remaining_quantity)).filter(ProduceBatch.product_id.in_(product_ids), ProduceBatch.is_visible.is_(True)).group_by(ProduceBatch.product_id).all()) if product_ids else {}
    return jsonify({"items": [product_data(row, stocks.get(row.id, 0)) for row in result.items], "page": page, "limit": limit, "total": result.total})
