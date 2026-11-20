"""orders: detail; tách xử lý theo thao tác API."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from flask import g, jsonify, request
from sqlalchemy import func
from app import db
from app.auth import require_role
from app.helpers import integer_value, json_body, page_args, quantity_value, required_text
from app.errors import ApiError
from app.models import DiscountCode, Order, OrderBatchAllocation, OrderItem, OrderStatusHistory, ProduceBatch, Product
from app.orders import order_api
from app.orders.data import order_data
from app.orders.service import calculate_discount, prepared_items


@order_api.get("/<order_code>")
@require_role("customer", "admin")
def get_my_order(order_code: str):
    """Xem đơn theo mã công khai và chủ sở hữu. Đầu vào: order_code; đầu ra: đơn hoặc 404. Ví dụ: GET /orders/VN-A1B2..."""
    order = db.session.query(Order).filter_by(order_code=order_code, customer_id=g.user.id).first()
    if order is None:
        raise ApiError(404, "not_found", "Không tìm thấy đơn hàng.")
    return jsonify(order_data(order))

