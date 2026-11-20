"""Quản trị orders: thao tác detail."""

from flask import jsonify
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.errors import ApiError
from app.models import Order
from app.orders import order_data


@admin_api.get("/orders/<int:order_id>")
@require_role("admin")
def admin_order(order_id: int):
    """Xem mọi đơn và lịch sử; đầu vào order_id, đầu ra snapshot đơn."""
    order = db.session.get(Order, order_id)
    if order is None:
        raise ApiError(404, "not_found", "Không tìm thấy đơn hàng.")
    return jsonify(order_data(order, include_internal=True))
