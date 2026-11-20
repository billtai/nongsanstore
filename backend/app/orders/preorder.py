"""Khách duyệt hoặc từ chối giá mới của đơn đặt trước."""

from decimal import Decimal

from flask import g, jsonify

from app import db
from app.auth import require_role
from app.errors import ApiError
from app.models import Order, OrderStatusHistory
from app.models.base import now_utc
from app.orders import order_api
from app.orders.data import order_data
from app.orders.reservations import allocate_waiting_preorders, release_reservation


@order_api.post("/<order_code>/price-approval")
@require_role("customer")
def approve_preorder_price(order_code: str):
    """Khách chấp thuận giá đã gửi và giữ hàng; đầu vào: mã đơn thuộc khách, đầu ra: đơn confirmed với giá mới. Ví dụ: chấp thuận 2 kg giá 30.000đ/kg sẽ giữ 2 kg và ghi 60.000đ."""
    try:
        order = db.session.query(Order).filter_by(order_code=order_code, customer_id=g.user.id).with_for_update().first()
        if order is None:
            raise ApiError(404, "not_found", "Không tìm thấy đơn hàng.")
        if not order.is_preorder or order.status != "awaiting_price_approval" or order.proposed_total_vnd is None:
            raise ApiError(409, "invalid_transition", "Đơn chưa có giá mới để xác nhận.")
        if not order.items or any(sum((allocation.quantity for allocation in item.allocations), Decimal("0")) != item.quantity for item in order.items):
            raise ApiError(409, "reservation_missing", "Hàng đặt trước chưa được giữ đủ. Vui lòng liên hệ cửa hàng.")
        for item in order.items:
            item.unit_price_vnd = item.proposed_unit_price_vnd
            item.line_total_vnd = item.proposed_line_total_vnd
        order.subtotal_vnd    = order.proposed_subtotal_vnd
        order.discount_vnd    = order.proposed_discount_vnd
        order.total_vnd       = order.proposed_total_vnd
        order.price_approved_at = now_utc()
        order.status          = "confirmed"
        db.session.add(OrderStatusHistory(order_id=order.id, from_status="awaiting_price_approval", to_status="confirmed", actor_id=g.user.id, reason="Khách đã chấp thuận giá khi hàng về."))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(order_data(order))


@order_api.post("/<order_code>/price-rejection")
@order_api.post("/<order_code>/cancel")
@require_role("customer")
def reject_preorder_price(order_code: str):
    """Khách hủy đơn đặt trước và hoàn tồn đã giữ; đầu vào: mã đơn thuộc khách, đầu ra: đơn cancelled. Ví dụ: hủy đơn giữ 1 kg trả 1 kg về kho."""
    try:
        order = db.session.query(Order).filter_by(order_code=order_code, customer_id=g.user.id).with_for_update().first()
        if order is None:
            raise ApiError(404, "not_found", "Không tìm thấy đơn hàng.")
        if not order.is_preorder or order.status not in ("preordered", "awaiting_price_approval"):
            raise ApiError(409, "invalid_transition", "Đơn đặt trước này không thể hủy.")
        reason = "Khách hủy đơn đặt trước." if order.status == "preordered" else "Khách không đồng ý giá khi hàng về."
        release_reservation(order, reason, g.user.id)
        db.session.flush()
        for item in order.items:
            allocate_waiting_preorders(item.product_id)
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(order_data(order))
