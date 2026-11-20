"""Quản trị customers: thao tác orders."""

from flask import jsonify
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.helpers import page_args
from app.errors import ApiError
from app.models import Customer, Order
from app.orders import order_data


@admin_api.get("/customers/<int:customer_id>/orders")
@require_role("admin")
def customer_orders(customer_id: int):
    """Xem lịch sử mua của một khách; nhận page/limit, trả đơn phân trang."""
    customer = db.session.get(Customer, customer_id)
    if customer is None or customer.role != "customer":
        raise ApiError(404, "not_found", "Không tìm thấy khách hàng.")
    page, limit = page_args()
    result      = db.session.query(Order).filter_by(customer_id=customer_id).order_by(Order.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    return jsonify({"items": [order_data(row, include_internal=True) for row in result.items], "page": page, "limit": limit, "total": result.total})
