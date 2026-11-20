"""orders: service; tách xử lý theo thao tác API."""

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


def calculate_discount(code: DiscountCode, subtotal: int) -> int:
    """Kiểm tra mã và tính giảm theo VND; ví dụ percent 10 trên 100000 trả 10000."""
    current = datetime.now(timezone.utc)
    if not code.is_active or (code.starts_at and current < code.starts_at) or (code.ends_at and current > code.ends_at):
        raise ApiError(400, "invalid_discount", "Mã giảm giá chưa hoặc không còn hiệu lực.")
    if code.usage_limit is not None and code.used_count >= code.usage_limit:
        raise ApiError(400, "invalid_discount", "Mã giảm giá đã hết lượt sử dụng.")
    if subtotal < code.min_subtotal_vnd:
        raise ApiError(400, "invalid_discount", "Đơn hàng chưa đạt giá trị tối thiểu của mã.")
    if code.kind == "percent" and code.value > 100:
        raise ApiError(400, "invalid_discount", "Mã phần trăm không hợp lệ.")
    if code.kind == "fixed":
        return min(code.value, subtotal)
    return min((subtotal * code.value) // 100, subtotal)



def prepared_items(data: dict, lock: bool = False):
    """Kiểm tra dòng hàng, lấy giá hiện tại; lock=True khóa sản phẩm để đặt đơn an toàn."""
    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not raw_items or len(raw_items) > 100:
        raise ApiError(400, "invalid_input", "items phải là danh sách 1-100 sản phẩm.")
    ids = []
    for raw in raw_items:
        if not isinstance(raw, dict):
            raise ApiError(400, "invalid_input", "Mỗi item phải là JSON object.")
        ids.append(integer_value(raw.get("product_id"), "product_id", 1))
    if len(ids) != len(set(ids)):
        raise ApiError(400, "invalid_input", "Không gửi trùng product_id.")
    query = db.session.query(Product).filter(Product.id.in_(ids)).order_by(Product.id)
    if lock:
        query = query.with_for_update()
    products = {product.id: product for product in query.all()}
    lines    = []
    for raw, product_id in zip(raw_items, ids):
        product    = products.get(product_id)
        if product is None or not product.is_visible:
            raise ApiError(404, "not_found", f"Sản phẩm {product_id} không có sẵn.")
        quantity   = quantity_value(raw.get("quantity"), product.unit)
        line_total = int((quantity * product.price_vnd).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        lines.append((product, quantity, line_total))
    return lines

