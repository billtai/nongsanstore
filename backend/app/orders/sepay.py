"""Cổng thanh toán SePay Sandbox: ký form Checkout và xác thực IPN."""

import base64
import hashlib
import hmac
import os
from decimal import Decimal, InvalidOperation

from flask import jsonify, request

from app import db
from app.errors import ApiError
from app.helpers import json_body
from app.models import Order
from app.orders import order_api


CHECKOUT_URL = "https://pay-sandbox.sepay.vn/v1/checkout/init"
SIGN_FIELDS  = ("order_amount", "merchant", "currency", "operation", "order_description", "order_invoice_number", "customer_id", "payment_method", "success_url", "error_url", "cancel_url")


def sepay_settings():
    """Đọc Merchant Sandbox; đầu vào ID và Secret Key, đầu ra dict hoặc None.

    Ví dụ: có Merchant ID và Secret Key thì khách mở được trang QR Sandbox.
    """
    names  = ("SEPAY_MERCHANT_ID", "SEPAY_SECRET_KEY")
    values = {name: os.getenv(name, "").strip() for name in names}
    if not all(values.values()) or not values["SEPAY_MERCHANT_ID"].startswith("SP-TEST-") or not values["SEPAY_SECRET_KEY"].startswith("spsk_test_"):
        return None
    return values


def sepay_checkout(order: Order):
    """Ký form Checkout từ dữ liệu đơn; đầu vào đơn SePay, đầu ra action và fields.

    Ví dụ: đơn #12 giá 40000 VND tạo invoice NS12... và form POST tới Sandbox.
    """
    settings = sepay_settings()
    if settings is None or order.payment_method != "sepay" or not order.sepay_payment_code:
        return None
    fields = {
        "order_amount"         : str(order.total_vnd),
        "merchant"             : settings["SEPAY_MERCHANT_ID"],
        "currency"             : "VND",
        "operation"            : "PURCHASE",
        "order_description"    : f"Thanh toan don hang {order.order_code}",
        "order_invoice_number" : order.sepay_payment_code,
        "payment_method"       : "BANK_TRANSFER",
    }
    callback = os.getenv("SEPAY_RETURN_URL", "").strip()
    if callback.startswith("https://") and "{order_id}" in callback:
        for name in ("success_url", "error_url", "cancel_url"):
            fields[name] = callback.format(order_id=order.order_code)
    signed    = ",".join(f"{name}={fields[name]}" for name in SIGN_FIELDS if fields.get(name) and fields[name] != "0")
    signature = hmac.new(settings["SEPAY_SECRET_KEY"].encode(), signed.encode(), hashlib.sha256).digest()
    fields["signature"] = base64.b64encode(signature).decode()
    return {"action": CHECKOUT_URL, "fields": fields}


@order_api.post("/sepay/ipn")
def sepay_ipn():
    """Xác nhận IPN Cổng thanh toán; đầu vào X-Secret-Key và JSON, đầu ra success JSON.

    Ví dụ: ORDER_PAID, CAPTURED, APPROVED, đúng invoice và 40000 VND đổi đơn thành paid.
    """
    settings = sepay_settings()
    ipn_secret = os.getenv("SEPAY_IPN_SECRET_KEY", "").strip()
    if settings is None or not ipn_secret:
        raise ApiError(503, "sepay_unavailable", "SePay Sandbox chưa được cấu hình đầy đủ.")
    if not hmac.compare_digest(request.headers.get("X-Secret-Key", ""), ipn_secret):
        raise ApiError(401, "invalid_ipn", "Xác thực IPN SePay không hợp lệ.")
    data        = json_body()
    order_data  = data.get("order")
    transaction = data.get("transaction")
    if not isinstance(order_data, dict) or not isinstance(transaction, dict) or data.get("notification_type") not in ("ORDER_PAID", "TRANSACTION_VOID"):
        raise ApiError(400, "invalid_ipn", "Dữ liệu IPN SePay không hợp lệ.")
    if data["notification_type"] != "ORDER_PAID":
        return jsonify({"success": True, "matched": False})
    transaction_id = transaction.get("id")
    invoice        = order_data.get("order_invoice_number")
    try:
        amount = Decimal(str(order_data.get("order_amount")))
        paid   = Decimal(str(transaction.get("transaction_amount")))
    except (InvalidOperation, TypeError):
        raise ApiError(400, "invalid_ipn", "Số tiền IPN SePay không hợp lệ.") from None
    if not isinstance(invoice, str) or not isinstance(transaction_id, str) or not transaction_id or order_data.get("order_currency") != "VND" or transaction.get("transaction_currency") != "VND" or transaction.get("transaction_type") != "PAYMENT" or transaction.get("transaction_status") != "APPROVED" or order_data.get("order_status") != "CAPTURED":
        raise ApiError(400, "invalid_ipn", "Trạng thái giao dịch SePay không hợp lệ.")
    try:
        order = db.session.query(Order).filter_by(sepay_payment_code=invoice).with_for_update().first()
        if order is None or order.payment_method != "sepay" or order.status == "cancelled" or amount != order.total_vnd or paid != order.total_vnd:
            db.session.rollback()
            return jsonify({"success": True, "matched": False})
        if order.payment_status == "paid":
            db.session.rollback()
            return jsonify({"success": True, "matched": order.sepay_transaction_id == transaction_id})
        if order.payment_status != "pending":
            db.session.rollback()
            return jsonify({"success": True, "matched": False})
        if db.session.query(Order.id).filter_by(sepay_transaction_id=transaction_id).first() is not None:
            raise ApiError(409, "transaction_used", "Giao dịch SePay đã gắn với đơn khác.")
        order.payment_status       = "paid"
        order.sepay_transaction_id = transaction_id
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({"success": True, "matched": True})
