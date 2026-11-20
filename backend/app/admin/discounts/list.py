"""Quản trị discounts: thao tác list."""

from flask import jsonify, request
from app import db
from app.admin import admin_api
from app.admin.discounts.data import discount_data
from app.auth import require_role
from app.helpers import page_args
from app.errors import ApiError
from app.models import DiscountCode


@admin_api.get("/discounts")
@require_role("admin")
def admin_discounts():
    """Tìm và lọc mã tại DB; nhận q/active/page/limit, trả trang mã."""
    page, limit = page_args()
    query       = db.session.query(DiscountCode)
    search      = request.args.get("q", "").strip()
    active      = request.args.get("active")
    if search:
        query = query.filter(DiscountCode.code.ilike(f"%{search}%"))
    if active is not None:
        if active not in ("true", "false"):
            raise ApiError(400, "invalid_input", "active không hợp lệ.")
        query = query.filter_by(is_active=active == "true")
    result = query.order_by(DiscountCode.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    return jsonify({"items": [discount_data(item) for item in result.items], "page": page, "limit": limit, "total": result.total})
