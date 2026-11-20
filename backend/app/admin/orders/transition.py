"""Quản trị orders: thao tác transition."""

from flask import g, jsonify
from app import db
from app.admin import admin_api
from app.admin.orders.constants import TRANSITIONS
from app.auth import require_role
from app.helpers import json_body, required_text
from app.errors import ApiError
from app.models import Order, OrderStatusHistory, ProduceBatch
from app.orders import order_data
from app.orders.reservations import allocate_waiting_preorders


@admin_api.post("/orders/<int:order_id>/transitions")
@require_role("admin")
def transition_order(order_id: int):
    """Chuyển trạng thái hợp lệ; khi hủy trả tồn từng lô trong cùng transaction."""
    data      = json_body()
    to_status = required_text(data, "to_status", 30)
    reason    = data.get("reason")
    if reason is not None and (not isinstance(reason, str) or len(reason) > 500):
        raise ApiError(400, "invalid_input", "reason không hợp lệ.")
    try:
        order = db.session.query(Order).filter_by(id=order_id).with_for_update().first()
        if order is None:
            raise ApiError(404, "not_found", "Không tìm thấy đơn hàng.")
        if to_status not in TRANSITIONS[order.status]:
            raise ApiError(409, "invalid_transition", "Không thể chuyển trạng thái này.")
        if order.payment_method in ("momo", "sepay", "sepay_bank") and order.payment_status == "pending":
            raise ApiError(409, "payment_pending", "Đang chờ xác nhận thanh toán.")
        if order.payment_method in ("momo", "sepay", "sepay_bank") and order.payment_status == "paid" and to_status == "cancelled":
            raise ApiError(409, "refund_required", "Đơn đã thanh toán cần quy trình hoàn tiền trước khi hủy.")
        if order.payment_method in ("momo", "sepay", "sepay_bank") and order.payment_status != "paid" and to_status != "cancelled":
            raise ApiError(409, "payment_unpaid", "Chưa thể xử lý đơn chưa thanh toán.")
        previous = order.status
        if to_status == "cancelled":
            order.status = "cancelled"
            # Khóa lô trước khi hoàn lại đúng lượng đã cấp cho đơn.
            allocations = [allocation for item in order.items for allocation in item.allocations]
            batch_ids   = sorted({allocation.batch_id for allocation in allocations})
            batches     = {batch.id: batch for batch in db.session.query(ProduceBatch).filter(ProduceBatch.id.in_(batch_ids)).order_by(ProduceBatch.id).with_for_update().all()}
            for allocation in allocations:
                batches[allocation.batch_id].remaining_quantity += allocation.quantity
            if order.is_preorder:
                db.session.flush()
                for product_id in sorted({item.product_id for item in order.items}):
                    allocate_waiting_preorders(product_id)
        order.status = to_status
        db.session.add(OrderStatusHistory(order_id=order.id, from_status=previous, to_status=to_status, actor_id=g.user.id, reason=reason))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(order_data(order, include_internal=True))
