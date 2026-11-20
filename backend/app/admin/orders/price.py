"""Quản trị gửi giá hiện tại cho khách duyệt khi hàng đặt trước đã về."""

from decimal import Decimal, ROUND_HALF_UP

from flask import g, jsonify

from app import db
from app.admin import admin_api
from app.auth import require_role
from app.errors import ApiError
from app.models import Order, OrderStatusHistory, ProduceBatch, Product
from app.models.base import now_utc
from app.orders.data import order_data
from app.orders.reservations import allocate_waiting_preorders, expire_reservations


@admin_api.post("/orders/<int:order_id>/price-proposal")
@require_role("admin")
def propose_preorder_price(order_id: int):
    """Gửi giá hiện tại khi đủ hàng; đầu vào: ID đơn đặt trước, đầu ra: giá mới chờ khách duyệt. Ví dụ: 2 kg tăng 20.000đ/kg làm tổng đề xuất tăng 40.000đ."""
    try:
        order = db.session.query(Order).filter_by(id=order_id).with_for_update().first()
        if order is None:
            raise ApiError(404, "not_found", "Không tìm thấy đơn hàng.")
        if not order.is_preorder or order.status not in ("preordered", "awaiting_price_approval"):
            raise ApiError(409, "invalid_transition", "Đơn này không chờ báo giá đặt trước.")
        if order.status == "preordered":
            allocate_waiting_preorders()
            db.session.flush()
            if order.status != "awaiting_price_approval":
                raise ApiError(409, "insufficient_stock", "Chưa đủ hàng cho đơn đặt trước này.")
        items       = sorted(order.items, key=lambda item: item.product_id)
        product_ids = [item.product_id for item in items]
        products    = {product.id: product for product in db.session.query(Product).filter(Product.id.in_(product_ids)).order_by(Product.id).with_for_update().all()}
        subtotal = 0
        for item in items:
            product = products.get(item.product_id)
            if product is None or not product.is_visible:
                raise ApiError(409, "product_unavailable", f"Sản phẩm {item.product_name} không còn hiển thị.")
            item.proposed_unit_price_vnd = product.price_vnd
            item.proposed_line_total_vnd = int((item.quantity * product.price_vnd).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            subtotal += item.proposed_line_total_vnd
        # Giữ nguyên số tiền ưu đãi đã hứa lúc đặt, tối đa bằng tiền hàng mới.
        # Ví dụ: giảm 10.000đ ban đầu thì đề xuất mới vẫn giảm 10.000đ.
        discount                    = min(order.initial_discount_vnd or 0, subtotal)
        order.proposed_subtotal_vnd = subtotal
        order.proposed_discount_vnd = discount
        order.proposed_total_vnd    = subtotal - discount
        # Gửi lại giá không kéo dài hạn 24 giờ tính từ lúc hàng được giữ.
        # Ví dụ: cập nhật giá sau 2 giờ vẫn còn 22 giờ để khách xác nhận.
        order.price_proposed_at     = order.price_proposed_at or now_utc()
        previous                    = order.status
        order.status                = "awaiting_price_approval"
        db.session.add(OrderStatusHistory(order_id=order.id, from_status=previous, to_status=order.status, actor_id=g.user.id, reason="Đã gửi giá khi hàng về để khách xác nhận."))
        db.session.commit()
    except Exception:
        db.session.rollback()
        raise
    return jsonify(order_data(order, include_internal=True))
