"""Tra các đơn đã áp dụng mã giảm giá theo trang tại database."""

from flask import jsonify

from app import db
from app.admin import admin_api
from app.auth import require_role
from app.errors import ApiError
from app.helpers import page_args
from app.models import DiscountCode, Order


@admin_api.get("/discounts/<int:discount_id>/orders")
@require_role("admin")
def discount_orders(discount_id: int):
    """Trả đơn dùng mã; đầu vào ID mã/page/limit, đầu ra danh sách phân trang. Ví dụ GET /discounts/2/orders?page=1."""
    discount = db.session.get(DiscountCode, discount_id)
    if discount is None:
        raise ApiError(404, "not_found", "Không tìm thấy mã giảm giá.")
    page, limit = page_args()
    result      = db.session.query(Order).filter(Order.discount_code == discount.code).order_by(Order.created_at.desc(), Order.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    return jsonify({
        "items" : [{
            "id"             : order.id,
            "order_code"     : order.order_code,
            "customer_id"    : order.customer_id,
            "recipient_name" : order.recipient_name,
            "status"         : order.status,
            "discount_vnd"   : order.discount_vnd,
            "total_vnd"      : order.total_vnd,
            "created_at"     : order.created_at.isoformat(),
        } for order in result.items],
        "page"  : page,
        "limit" : limit,
        "total" : result.total,
    })
