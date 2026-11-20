"""Quản trị batches: thao tác update."""

from datetime import date
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.helpers import integer_value, json_body, quantity_value, required_text
from app.errors import ApiError
from app.models import ProduceBatch, Product
from app.products import batch_data
from app.orders.reservations import allocate_waiting_preorders, expire_reservations


@admin_api.patch("/batches/<int:batch_id>")
@require_role("admin")
def update_batch(batch_id: int):
    """Sửa thông tin lô; nhận các trường form, trả lô mới. Ví dụ PATCH /batches/1."""
    batch = db.session.get(ProduceBatch, batch_id)
    if batch is None:
        raise ApiError(404, "not_found", "Không tìm thấy lô.")
    data = json_body()
    if "is_visible" in data:
        if not isinstance(data["is_visible"], bool):
            raise ApiError(400, "invalid_input", "is_visible phải là boolean.")
        batch.is_visible = data["is_visible"]
    if "product_id" in data:
        product_id = integer_value(data["product_id"], "product_id", 1)
        if product_id != batch.product_id:
            raise ApiError(400, "invalid_input", "Không thể đổi sản phẩm của lô đã tạo.")
    if "batch_code" in data:
        raise ApiError(400, "invalid_input", "Mã lô đã tạo không thể sửa.")
    for key, maximum in (("growing_region", 180), ("origin", 255)):
        if key in data:
            setattr(batch, key, required_text(data, key, maximum))
    if "harvest_date" in data:
        try:
            batch.harvest_date = date.fromisoformat(required_text(data, "harvest_date", 10))
        except ValueError:
            raise ApiError(400, "invalid_input", "Ngày thu hoạch không hợp lệ.") from None
    if "quantity" in data:
        batch.remaining_quantity = quantity_value(data["quantity"], db.session.get(Product, batch.product_id).unit)
    try:
        db.session.flush()
        expire_reservations()
        allocate_waiting_preorders(batch.product_id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "batch_exists", "Mã lô đã tồn tại.") from None
    return jsonify(batch_data(batch))
