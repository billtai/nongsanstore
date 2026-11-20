"""Quản trị orders: thao tác list."""

from flask import jsonify, request
from sqlalchemy import or_
from app import db
from app.admin import admin_api
from app.admin.orders.constants import TRANSITIONS
from app.auth import require_role
from app.helpers import integer_value, order_date_range, page_args
from app.errors import ApiError
from app.models import Customer, Order, OrderItem
from app.orders import order_data


@admin_api.get("/orders")
@require_role("admin")
def admin_orders():
    """Liệt kê đơn quản trị; nhận kind/status/q/date/customer_id/page/limit, trả đơn phân trang. Ví dụ: q=cà rốt&date=2026-11-18 tìm đơn chứa sản phẩm trong ngày."""
    page, limit = page_args()
    query       = db.session.query(Order)
    kind        = request.args.get("kind")
    if kind not in (None, "regular", "preorder"):
        raise ApiError(400, "invalid_input", "kind không hợp lệ.")
    if kind:
        query = query.filter(Order.is_preorder.is_(kind == "preorder"))
    search = request.args.get("q", "").strip()
    if search:
        if len(search) > 120:
            raise ApiError(400, "invalid_input", "Từ khóa tìm kiếm quá dài.")
        query = query.join(Customer, Order.customer_id == Customer.id).filter(or_(Customer.name.ilike(f"%{search}%"), Order.recipient_name.ilike(f"%{search}%"), Order.order_code.ilike(f"%{search}%"), Order.items.any(OrderItem.product_name.ilike(f"%{search}%"))))
    if "date" in request.args:
        start, end = order_date_range(request.args["date"])
        query      = query.filter(Order.created_at >= start, Order.created_at < end)
    if "status" in request.args:
        status = request.args["status"]
        if status not in TRANSITIONS:
            raise ApiError(400, "invalid_input", "status không hợp lệ.")
        query = query.filter(Order.status == status)
    if "customer_id" in request.args:
        query = query.filter(Order.customer_id == integer_value(request.args["customer_id"], "customer_id", 1))
    result = query.order_by(Order.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    return jsonify({"items": [order_data(row, include_internal=True) for row in result.items], "page": page, "limit": limit, "total": result.total})
