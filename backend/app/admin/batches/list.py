"""Quản trị batches: thao tác list."""

from flask import jsonify, request
from sqlalchemy import or_
from sqlalchemy.orm import joinedload
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.helpers import integer_value, page_args
from app.errors import ApiError
from app.models import ProduceBatch, Product
from app.products import batch_data


@admin_api.get("/batches")
@require_role("admin")
def admin_batches():
    """Liệt kê lô, lọc product_id và phân trang; trả thông tin nguồn gốc/tồn."""
    page, limit = page_args()
    query       = db.session.query(ProduceBatch).options(joinedload(ProduceBatch.product))
    if "product_id" in request.args:
        query = query.filter_by(product_id=integer_value(request.args["product_id"], "product_id", 1))
    visible = request.args.get("visible")
    if visible is not None:
        if visible not in ("true", "false"):
            raise ApiError(400, "invalid_input", "visible phải là true hoặc false.")
        query = query.filter(ProduceBatch.is_visible.is_(visible == "true"))
    search = request.args.get("q", "").strip()
    if search:
        query = query.join(Product).filter(or_(ProduceBatch.batch_code.ilike(f"%{search}%"), Product.name.ilike(f"%{search}%")))
    result = query.order_by(ProduceBatch.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    return jsonify({"items": [batch_data(row, True) for row in result.items], "page": page, "limit": limit, "total": result.total})
