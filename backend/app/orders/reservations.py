"""Giữ hàng cho đơn đặt trước theo thứ tự tạo đơn và giải phóng sau 24 giờ."""

from datetime import timedelta
from decimal import Decimal, ROUND_HALF_UP

from app import db
from app.models import Order, OrderBatchAllocation, OrderStatusHistory, ProduceBatch, Product
from app.models.base import now_utc


def release_reservation(order: Order, reason: str, actor_id: int | None = None):
    """Hủy đơn và hoàn tồn đã giữ; đầu vào: đơn, lý do, người thao tác; đầu ra: tồn lô và lịch sử đã cập nhật. Ví dụ: hết 24 giờ hoàn lại 1 kg."""
    allocations = [allocation for item in order.items for allocation in item.allocations]
    batch_ids   = sorted({allocation.batch_id for allocation in allocations})
    batches     = {batch.id: batch for batch in db.session.query(ProduceBatch).filter(ProduceBatch.id.in_(batch_ids)).order_by(ProduceBatch.id).with_for_update().all()}
    for allocation in allocations:
        batches[allocation.batch_id].remaining_quantity += allocation.quantity
    previous     = order.status
    order.status = "cancelled"
    db.session.add(OrderStatusHistory(order_id=order.id, from_status=previous, to_status="cancelled", actor_id=actor_id or order.customer_id, reason=reason))


def expire_reservations():
    """Hủy các đề xuất quá 24 giờ; đầu vào: thời gian UTC hiện tại, đầu ra: số đơn đã hủy. Ví dụ: đề xuất hôm qua 09:00 hết hạn hôm nay 09:00."""
    deadline = now_utc() - timedelta(days=1)
    expired  = db.session.query(Order).filter(Order.status == "awaiting_price_approval", Order.price_proposed_at <= deadline).order_by(Order.id).with_for_update().all()
    product_ids = set()
    for order in expired:
        product_ids.update(item.product_id for item in order.items)
        release_reservation(order, "Hết 24 giờ xác nhận giá; hàng đã được mở bán lại.")
    if expired:
        db.session.flush()
        for product_id in sorted(product_ids):
            allocate_waiting_preorders(product_id)
    return len(expired)


def allocate_waiting_preorders(product_id: int | None = None):
    """Ưu tiên giữ lô cho đơn cũ nhất khi hàng về; đầu vào: sản phẩm vừa nhập hoặc None, đầu ra: số đơn được gửi giá. Ví dụ: nhập 1 kg cho đơn chờ 1 kg thì tồn bán lẻ còn 0."""
    query = db.session.query(Order).filter(Order.status == "preordered", Order.is_preorder.is_(True))
    if product_id is not None:
        query = query.filter(Order.items.any(product_id=product_id))
    orders  = query.order_by(Order.created_at, Order.id).with_for_update().all()
    count   = 0
    for order in orders:
        items       = sorted(order.items, key=lambda item: item.product_id)
        product_ids = [item.product_id for item in items]
        products    = {product.id: product for product in db.session.query(Product).filter(Product.id.in_(product_ids)).order_by(Product.id).with_for_update().all()}
        batches     = db.session.query(ProduceBatch).filter(ProduceBatch.product_id.in_(product_ids), ProduceBatch.is_visible.is_(True), ProduceBatch.remaining_quantity > 0).order_by(ProduceBatch.product_id, ProduceBatch.harvest_date, ProduceBatch.id).with_for_update().all()
        by_product  = {}
        for batch in batches:
            by_product.setdefault(batch.product_id, []).append(batch)
        if any(products.get(item.product_id) is None or not products[item.product_id].is_visible for item in items):
            continue
        subtotal = 0
        complete = True
        for item in items:
            # Giữ từng phần theo thứ tự đơn; chỉ gửi giá khi mọi sản phẩm đã đủ.
            # Ví dụ: đơn chờ 2 kg, nhập 1 kg trước thì 1 kg này không được bán lẻ.
            remaining = item.quantity - sum((allocation.quantity for allocation in item.allocations), Decimal("0"))
            for batch in by_product.get(item.product_id, []):
                taken = min(remaining, batch.remaining_quantity)
                if taken <= 0:
                    continue
                batch.remaining_quantity -= taken
                item.allocations.append(OrderBatchAllocation(batch_id=batch.id, quantity=taken))
                remaining -= taken
                if remaining == 0:
                    break
            if remaining > 0:
                complete = False
        if not complete:
            db.session.flush()
            continue
        for item in items:
            item.proposed_unit_price_vnd = products[item.product_id].price_vnd
            item.proposed_line_total_vnd = int((item.quantity * item.proposed_unit_price_vnd).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
            subtotal += item.proposed_line_total_vnd
        order.proposed_subtotal_vnd = subtotal
        order.proposed_discount_vnd = min(order.initial_discount_vnd or 0, subtotal)
        order.proposed_total_vnd    = subtotal - order.proposed_discount_vnd
        order.price_proposed_at     = now_utc()
        order.status                = "awaiting_price_approval"
        db.session.add(OrderStatusHistory(order_id=order.id, from_status="preordered", to_status=order.status, actor_id=order.customer_id, reason="Hàng đã về; giữ hàng và chờ khách xác nhận giá trong 24 giờ."))
        count += 1
    return count
