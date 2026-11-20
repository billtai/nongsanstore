"""QR chuyển khoản trực tiếp và webhook biến động số dư ngân hàng SePay."""

import hmac
import os
import re
from datetime import datetime, timezone
from urllib.parse import urlencode

from flask import g, jsonify, request

from app import db
from app.auth import require_role
from app.errors import ApiError
from app.helpers import json_body
from app.models import Order
from app.orders import order_api
from app.orders.data import order_data


def bank_settings():
    """Đọc tài khoản nhận từ env; đầu vào SEPAY_BANK_*, đầu ra dict hoặc None.

    Ví dụ: ACB/22810217/TỐNG THÀNH TÀI cho phép tạo QR trong trang đơn.
    """
    names  = ("SEPAY_BANK_CODE", "SEPAY_ACCOUNT_NUMBER", "SEPAY_ACCOUNT_NAME")
    values = {name: os.getenv(name, "").strip() for name in names}
    if not all(values.values()) or not re.fullmatch(r"[A-Za-z0-9]+", values["SEPAY_ACCOUNT_NUMBER"]):
        return None
    return values


def bank_transfer_data(order: Order):
    """Tạo URL QR VietQR từ snapshot đơn; đầu vào đơn sepay_bank, đầu ra dict hoặc None.

    Ví dụ: đơn 12 trả QR có 40000 VND và mã NS12... riêng của đơn.
    """
    if order.payment_method != "sepay_bank" or not order.sepay_payment_code:
        return None
    params = {
        "acc"      : order.sepay_account_number,
        "bank"     : order.sepay_bank_code,
        "amount"   : order.total_vnd,
        "des"      : order.sepay_payment_code,
        "template" : "compact",
    }
    return {
        "bank_code"      : order.sepay_bank_code,
        "account_number" : order.sepay_account_number,
        "account_name"   : order.sepay_account_name,
        "amount_vnd"     : order.total_vnd,
        "payment_code"   : order.sepay_payment_code,
        "qr_url"         : f"https://vietqr.app/img?{urlencode(params)}",
    }


@order_api.post("/<order_code>/sepay/bank-transfer-reported")
@require_role("customer")
def report_bank_transfer(order_code: str):
    """Ghi nhận khách báo đã chuyển khoản; đầu vào mã đơn của chính khách, đầu ra đơn cập nhật.

    Ví dụ: POST /orders/VN-ABC/sepay/bank-transfer-reported lưu thời điểm báo, vẫn chờ webhook xác nhận tiền.
    """
    try:
        order = db.session.query(Order).filter_by(order_code=order_code, customer_id=g.user.id).with_for_update().first()
        if order is None:
            raise ApiError(404, "not_found", "Không tìm thấy đơn hàng.")
        if order.payment_method != "sepay_bank":
            raise ApiError(409, "invalid_payment_method", "Đơn này không thanh toán qua QR ngân hàng.")
        if order.status == "cancelled":
            raise ApiError(409, "order_cancelled", "Đơn đã hủy.")
        if order.payment_status == "pending" and order.bank_transfer_reported_at is None:
            order.bank_transfer_reported_at = datetime.now(timezone.utc)
            db.session.commit()
        return jsonify(order_data(order))
    except Exception:
        db.session.rollback()
        raise
@order_api.post("/sepay/bank-webhook")
def sepay_bank_webhook():
    """Xác thực webhook tiền vào; đầu vào header Apikey và JSON SePay, đầu ra matched.

    Ví dụ: ID 92704, đúng tài khoản, mã đơn và số tiền đánh dấu đơn paid một lần.
    """
    api_key = os.getenv("SEPAY_BANK_WEBHOOK_API_KEY", "").strip()
    if not api_key:
        raise ApiError(503, "sepay_unavailable", "Chưa cấu hình khóa webhook ngân hàng SePay.")
    if not hmac.compare_digest(request.headers.get("Authorization", ""), f"Apikey {api_key}"):
        raise ApiError(401, "invalid_webhook", "Khóa webhook ngân hàng không hợp lệ.")
    data           = json_body()
    transaction_id = data.get("id")
    amount         = data.get("transferAmount")
    account        = data.get("accountNumber")
    content        = data.get("content")
    if type(transaction_id) is not int or transaction_id <= 0 or type(amount) is not int or amount <= 0 or not isinstance(account, str) or not isinstance(content, str) or data.get("transferType") != "in":
        raise ApiError(400, "invalid_webhook", "Giao dịch SePay không hợp lệ.")

    # Chỉ nhận mã chuyển khoản nguyên vẹn; mã VN-... mới và NS... cũ đều còn dùng để đối chiếu.
    # Ví dụ: "THANH TOAN VN-A1B2..." khớp; thêm chữ/số sau mã sẽ không khớp.
    codes = set(re.findall(r"(?<![A-Z0-9])(?:VN-[A-F0-9]{24}|NS[0-9]+[A-F0-9]{16})(?![A-Z0-9])", content.upper()))
    if len(codes) != 1:
        return jsonify({"success": True, "matched": False})
    try:
        order = db.session.query(Order).filter_by(sepay_payment_code=next(iter(codes))).with_for_update().first()
        if order is None or order.payment_method != "sepay_bank" or order.sepay_account_number != account or order.total_vnd != amount or order.status == "cancelled":
            db.session.rollback()
            return jsonify({"success": True, "matched": False})
        existing = db.session.query(Order.id).filter_by(sepay_transaction_id=str(transaction_id)).first()
        if existing is not None and existing.id != order.id:
            raise ApiError(409, "transaction_used", "Giao dịch đã gắn với đơn khác.")
        if order.payment_status == "paid":
            if order.bank_payment_confirmed_at and order.sepay_transaction_id is None:
                order.sepay_transaction_id = str(transaction_id)
                db.session.commit()
                return jsonify({"success": True, "matched": True})
            db.session.rollback()
            return jsonify({"success": True, "matched": order.sepay_transaction_id == str(transaction_id)})
        if order.payment_status != "pending":
            db.session.rollback()
            return jsonify({"success": True, "matched": False})
        order.payment_status       = "paid"
        order.sepay_transaction_id = str(transaction_id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify({"success": True, "matched": True})
