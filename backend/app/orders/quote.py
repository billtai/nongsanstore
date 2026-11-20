"""orders: quote; tách xử lý theo thao tác API."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from uuid import uuid4
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
from app.orders.quote_token import quote_serializer


@order_api.post("/quote")
@require_role("customer", "admin")
def quote_order():
    """Báo giá theo giá hiện tại; nhận items/discount_code, trả tiền tạm tính và giảm giá."""
    data     = json_body()
    lines    = prepared_items(data)
    flags    = [raw.get("preorder", False) for raw in data["items"]]
    if any(flags) and not all(flags):
        raise ApiError(400, "mixed_order", "Vui lòng đặt riêng sản phẩm có sẵn và sản phẩm đặt trước.")
    ids      = [product.id for product, _, _ in lines]
    stocks   = dict(db.session.query(ProduceBatch.product_id, func.sum(ProduceBatch.remaining_quantity)).filter(ProduceBatch.product_id.in_(ids), ProduceBatch.is_visible.is_(True)).group_by(ProduceBatch.product_id).all())
    for raw, (product, quantity, _) in zip(data["items"], lines):
        preorder  = raw.get("preorder", False)
        if type(preorder) is not bool:
            raise ApiError(400, "invalid_input", "Trạng thái đặt trước không hợp lệ.")
        available = stocks.get(product.id, Decimal("0"))
        if preorder and available > 0:
            raise ApiError(409, "stock_changed", f"Sản phẩm {product.name} đã có hàng. Vui lòng cập nhật giỏ hàng.")
        if not preorder and available < quantity:
            raise ApiError(409, "insufficient_stock", f"Sản phẩm {product.id} không đủ tồn kho.")
    subtotal = sum(line_total for _, _, line_total in lines)
    discount = 0
    code_raw = data.get("discount_code")
    if code_raw is not None:
        code_text = required_text(data, "discount_code", 50).upper()
        code      = db.session.query(DiscountCode).filter_by(code=code_text).first()
        if code is None:
            raise ApiError(400, "invalid_discount", "Mã giảm giá không hợp lệ.")
        discount = calculate_discount(code, subtotal)
    quote_items = [{"product_id": product.id, "name": product.name, "quantity": str(quantity), "unit": product.unit, "unit_price_vnd": product.price_vnd, "line_total_vnd": line_total, "preorder": raw.get("preorder", False)} for raw, (product, quantity, line_total) in zip(data["items"], lines)]
    quote_id    = quote_serializer().dumps({"nonce": uuid4().hex, "customer_id": g.user.id, "items": [{"product_id": item["product_id"], "quantity": item["quantity"], "preorder": item["preorder"]} for item in quote_items], "discount_code": code_text if code_raw is not None else None, "subtotal_vnd": subtotal, "discount_vnd": discount})
    return jsonify({"quote_id": quote_id, "expires_in": 900, "items": quote_items, "is_preorder": any(item["preorder"] for item in quote_items), "subtotal_vnd": subtotal, "discount_vnd": discount, "total_vnd": subtotal - discount, "shipping_fee_vnd": None, "payment_method": "cod", "currency": "VND"})

