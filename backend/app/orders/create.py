"""orders: create; tách xử lý theo thao tác API."""

from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from secrets import token_hex
from flask import g, jsonify, request
from sqlalchemy import func
from sqlalchemy.exc import IntegrityError
from app import db
from app.auth import require_role
from app.helpers import integer_value, json_body, page_args, quantity_value, required_text
from app.errors import ApiError
from app.models import DiscountCode, Order, OrderBatchAllocation, OrderItem, OrderStatusHistory, ProduceBatch, Product
from app.orders import order_api
from app.orders.data import order_data
from app.orders.service import calculate_discount, prepared_items
from app.orders.quote_token import read_quote
from app.orders.momo import initiate_momo, momo_settings
from app.orders.sepay import sepay_settings
from app.orders.sepay_bank import bank_settings


@order_api.post("")
@order_api.post("/")
@order_api.post("/confirm")
@require_role("customer", "admin")
def create_order():
    """Xác nhận báo giá, tạo đơn COD hoặc MoMo Test và khóa tồn trong transaction.

    Đầu vào: quote_id, người nhận, địa chỉ, payment_method; đầu ra: đơn và pay_url nếu chọn MoMo.
    Ví dụ: payment_method=momo trả pay_url để trình duyệt chuyển tới cổng Test.
    """
    data              = json_body()
    quoted            = None
    if request.path.endswith("/confirm") and not data.get("quote_id"):
        raise ApiError(400, "invalid_input", "Thiếu quote_id.")
    if data.get("quote_id") is not None:
        quote_id = required_text(data, "quote_id", 1024)
        quoted   = read_quote(quote_id, g.user.id)
        data     = {**data, "items": quoted["items"], "discount_code": quoted["discount_code"]}
        existing = db.session.query(Order).filter_by(quote_id=quote_id, customer_id=g.user.id).first()
        if existing is not None:
            if existing.payment_method == "momo" and existing.payment_status == "pending":
                try:
                    initiate_momo(existing)
                except ApiError as error:
                    return jsonify({**order_data(existing), "payment_error": error.message}), 202
            return jsonify(order_data(existing))
    recipient_name    = required_text(data, "recipient_name", 120)
    recipient_phone   = required_text(data, "recipient_phone", 30)
    delivery_address  = required_text(data, "delivery_address", 500)
    payment_method = data.get("payment_method", "cod")
    if payment_method not in ("cod", "momo", "sepay", "sepay_bank"):
        raise ApiError(400, "invalid_input", "Phương thức thanh toán không hợp lệ.")
    if payment_method == "momo" and momo_settings() is None:
        raise ApiError(503, "momo_unavailable", "MoMo Test chưa được cấu hình đầy đủ.")
    sepay_config = sepay_settings() if payment_method == "sepay" else None
    if payment_method == "sepay" and sepay_config is None:
        raise ApiError(503, "sepay_unavailable", "SePay chưa được cấu hình đầy đủ.")
    bank_config = bank_settings() if payment_method == "sepay_bank" else None
    if payment_method == "sepay_bank" and bank_config is None:
        raise ApiError(503, "sepay_unavailable", "Chưa cấu hình tài khoản nhận SePay.")
    try:
        lines          = prepared_items(data, lock=True)
        preorder_flags = []
        for raw in data["items"]:
            flag = raw.get("preorder", False)
            if type(flag) is not bool:
                raise ApiError(400, "invalid_input", "Trạng thái đặt trước không hợp lệ.")
            preorder_flags.append(flag)
        has_preorder   = any(preorder_flags)
        if has_preorder and not all(preorder_flags):
            raise ApiError(400, "mixed_order", "Vui lòng đặt riêng sản phẩm có sẵn và sản phẩm đặt trước.")
        if has_preorder and payment_method != "cod":
            raise ApiError(400, "invalid_payment", "Đơn đặt trước chỉ hỗ trợ thanh toán khi nhận hàng.")
        subtotal       = sum(line_total for _, _, line_total in lines)
        discount       = 0
        code           = None
        if data.get("discount_code") is not None:
            code_text = required_text(data, "discount_code", 50).upper()
            code      = db.session.query(DiscountCode).filter_by(code=code_text).with_for_update().first()
            if code is None:
                raise ApiError(400, "invalid_discount", "Mã giảm giá không hợp lệ.")
            discount = calculate_discount(code, subtotal)
        if quoted and (subtotal != quoted["subtotal_vnd"] or discount != quoted["discount_vnd"]):
            raise ApiError(409, "quote_changed", "Giá hoặc khuyến mãi đã thay đổi. Vui lòng lấy báo giá mới.")
        if payment_method == "momo" and not 1000 <= subtotal - discount <= 50000000:
            raise ApiError(400, "invalid_payment", "Số tiền MoMo phải từ 1.000 đến 50.000.000 VND.")
        if payment_method in ("sepay", "sepay_bank") and subtotal - discount <= 0:
            raise ApiError(400, "invalid_payment", "Số tiền chuyển khoản phải lớn hơn 0 VND.")
        order = Order(order_code=f"VN-{token_hex(12).upper()}", customer_id=g.user.id, recipient_name=recipient_name, recipient_phone=recipient_phone, delivery_address=delivery_address, status="preordered" if has_preorder else "pending", is_preorder=has_preorder, payment_method=payment_method, payment_status="pending" if payment_method in ("momo", "sepay", "sepay_bank") else "unpaid", subtotal_vnd=subtotal, discount_vnd=discount, total_vnd=subtotal - discount, discount_code=code.code if code else None, quote_id=data.get("quote_id"))
        if has_preorder:
            order.initial_subtotal_vnd = subtotal
            order.initial_discount_vnd = discount
            order.initial_total_vnd    = subtotal - discount
        db.session.add(order)
        db.session.flush()
        if payment_method == "momo":
            order.momo_order_id   = f"NS{token_hex(16).upper()}"
            order.momo_request_id = order.momo_order_id
        if payment_method in ("sepay", "sepay_bank"):
            order.sepay_payment_code   = order.order_code
        if payment_method == "sepay_bank":
            order.sepay_bank_code      = bank_config["SEPAY_BANK_CODE"]
            order.sepay_account_number = bank_config["SEPAY_ACCOUNT_NUMBER"]
            order.sepay_account_name   = bank_config["SEPAY_ACCOUNT_NAME"]
        for (product, quantity, line_total), is_preorder in zip(lines, preorder_flags):
            batches   = db.session.query(ProduceBatch).filter(ProduceBatch.product_id == product.id, ProduceBatch.is_visible.is_(True), ProduceBatch.remaining_quantity > 0).order_by(ProduceBatch.harvest_date, ProduceBatch.id).with_for_update().all()
            available = sum((batch.remaining_quantity for batch in batches), Decimal("0"))
            if is_preorder and available > 0:
                raise ApiError(409, "stock_changed", f"Sản phẩm {product.name} đã có hàng. Vui lòng cập nhật giỏ hàng.")
            if not is_preorder and available < quantity:
                raise ApiError(409, "insufficient_stock", f"Sản phẩm {product.id} không đủ tồn kho.")
            item = OrderItem(order_id=order.id, product_id=product.id, product_name=product.name, unit=product.unit, quantity=quantity, unit_price_vnd=product.price_vnd, line_total_vnd=line_total, is_preorder=is_preorder)
            if is_preorder:
                item.initial_unit_price_vnd = product.price_vnd
                item.initial_line_total_vnd = line_total
            db.session.add(item)
            db.session.flush()
            if is_preorder:
                continue
            remainder = quantity
            for batch in batches:
                if remainder <= 0:
                    break
                taken = min(remainder, batch.remaining_quantity)
                batch.remaining_quantity -= taken
                db.session.add(OrderBatchAllocation(item_id=item.id, batch_id=batch.id, quantity=taken))
                remainder -= taken
        if code:
            code.used_count += 1
        db.session.add(OrderStatusHistory(order_id=order.id, from_status=None, to_status=order.status, actor_id=g.user.id))
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        if quoted:
            existing = db.session.query(Order).filter_by(quote_id=data["quote_id"], customer_id=g.user.id).first()
            if existing is not None:
                if existing.payment_method == "momo" and existing.payment_status == "pending":
                    try:
                        initiate_momo(existing)
                    except ApiError as error:
                        return jsonify({**order_data(existing), "payment_error": error.message}), 202
                return jsonify(order_data(existing))
        raise
    except Exception:
        db.session.rollback()
        raise
    if payment_method == "momo":
        try:
            initiate_momo(order)
        except ApiError as error:
            return jsonify({**order_data(order), "payment_error": error.message}), 202
    return jsonify(order_data(order)), 201

