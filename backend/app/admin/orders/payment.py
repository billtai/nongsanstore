"""Đối soát thủ công khoản chuyển QR khi webhook ngân hàng bị chậm hoặc lỗi."""

from datetime import datetime, timezone

from flask import g, jsonify

from app import db
from app.admin import admin_api
from app.auth import require_role
from app.errors import ApiError
from app.models import Order
from app.orders import order_data


@admin_api.post("/orders/<int:order_id>/confirm-bank-payment")
@require_role("admin")
def confirm_bank_payment(order_id: int):
    """Admin xác nhận đã thấy tiền trong tài khoản; đầu vào ID đơn QR, đầu ra đơn paid.

    Ví dụ: POST /admin/orders/12/confirm-bank-payment sau khi đối chiếu số tiền 235200 VND trong sao kê.
    """
    try:
        order = db.session.query(Order).filter_by(id=order_id).with_for_update().first()
        if order is None:
            raise ApiError(404, "not_found", "Không tìm thấy đơn hàng.")
        if order.payment_method != "sepay_bank":
            raise ApiError(409, "invalid_payment_method", "Đơn này không thanh toán qua QR ngân hàng.")
        if order.status == "cancelled":
            raise ApiError(409, "order_cancelled", "Không thể xác nhận thanh toán cho đơn đã hủy.")
        if order.payment_status == "paid":
            return jsonify(order_data(order, include_internal=True))
        if order.payment_status != "pending":
            raise ApiError(409, "invalid_payment_status", "Trạng thái thanh toán không hợp lệ.")
        order.payment_status           = "paid"
        order.bank_payment_confirmed_at = datetime.now(timezone.utc)
        order.bank_payment_confirmed_by = g.user.id
        db.session.commit()
        return jsonify(order_data(order, include_internal=True))
    except Exception:
        db.session.rollback()
        raise
