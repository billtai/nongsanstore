"""orders: list; tách xử lý theo thao tác API."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from flask import g, jsonify, request
from sqlalchemy import func
from app import db
from app.auth import require_role
from app.helpers import integer_value, json_body, order_date_range, page_args, quantity_value, required_text
from app.errors import ApiError
from app.models import DiscountCode, Order, OrderBatchAllocation, OrderItem, OrderStatusHistory, ProduceBatch, Product
from app.orders import order_api
from app.orders.data import order_data
from app.orders.service import calculate_discount, prepared_items


@order_api.get("")
@order_api.get("/")
@require_role("customer", "admin")
def my_orders():
    """Liệt kê đơn của tài khoản; nhận kind/status/q/date/page/limit, trả danh sách phân trang. Ví dụ: q=cà rốt&date=2026-11-18 lọc theo tên món và ngày Việt Nam."""
    page, limit = page_args()
    query       = db.session.query(Order).filter_by(customer_id=g.user.id)
    status      = request.args.get("status")
    kind        = request.args.get("kind")
    if kind not in (None, "regular", "preorder"):
        raise ApiError(400, "invalid_input", "kind không hợp lệ.")
    if kind:
        query = query.filter(Order.is_preorder.is_(kind == "preorder"))
    if status:
        if status not in ("preordered", "awaiting_price_approval", "pending", "confirmed", "preparing", "delivering", "completed", "cancelled"):
            raise ApiError(400, "invalid_input", "status không hợp lệ.")
        query = query.filter_by(status=status)
    search = request.args.get("q", "").strip()
    if search:
        if len(search) > 120:
            raise ApiError(400, "invalid_input", "Tên sản phẩm quá dài.")
        query = query.filter(Order.items.any(OrderItem.product_name.ilike(f"%{search}%")))
    if "date" in request.args:
        start, end = order_date_range(request.args["date"])
        query      = query.filter(Order.created_at >= start, Order.created_at < end)
    result = query.order_by(Order.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    product_ids    = {item.product_id for order in result.items for item in order.items}
    product_images = dict(db.session.query(Product.id, Product.image_url).filter(Product.id.in_(product_ids)).all()) if product_ids else {}
    return jsonify({"items": [order_data(order, product_images=product_images) for order in result.items], "page": page, "limit": limit, "total": result.total})

