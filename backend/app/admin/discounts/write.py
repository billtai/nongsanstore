"""Quản trị discounts: thao tác write."""

from datetime import datetime, timezone
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from app import db
from app.admin import admin_api
from app.admin.discounts.data import discount_data
from app.auth import require_role
from app.helpers import integer_value, json_body, required_text
from app.errors import ApiError
from app.models import DiscountCode


@admin_api.post("/discounts")
@admin_api.patch("/discounts/<int:discount_id>")
@require_role("admin")
def write_discount(discount_id=None):
    """Thêm/sửa mã; nhận code/kind/value và giới hạn, trả mã. Ví dụ POST /discounts."""
    data = json_body()
    item = db.session.get(DiscountCode, discount_id) if discount_id else DiscountCode()
    if item is None:
        raise ApiError(404, "not_found", "Không tìm thấy mã.")
    if "code" in data or not discount_id:
        next_code = required_text(data, "code", 50).upper()
        if discount_id and next_code != item.code and item.used_count:
            raise ApiError(409, "discount_in_use", "Mã đã được dùng trong đơn; không thể đổi tên mã.")
        item.code = next_code
    if "kind" in data or not discount_id:
        item.kind = required_text(data, "kind", 10)
        if item.kind not in ("fixed", "percent"):
            raise ApiError(400, "invalid_input", "Loại mã không hợp lệ.")
    if "value" in data or not discount_id:
        item.value = integer_value(data.get("value"), "value", 1)
    if item.kind == "percent" and item.value > 100:
        raise ApiError(400, "invalid_input", "Phần trăm tối đa 100.")
    for key in ("min_subtotal_vnd", "usage_limit"):
        if key in data:
            setattr(item, key, integer_value(data[key], key, 1 if key == "usage_limit" else 0) if data[key] is not None else None)
    if item.min_subtotal_vnd is None:
        item.min_subtotal_vnd = 0
    for key in ("starts_at", "ends_at"):
        if key in data:
            try:
                moment = datetime.fromisoformat(data[key]) if data[key] else None
                setattr(item, key, moment.replace(tzinfo=timezone.utc) if moment and moment.tzinfo is None else moment)
            except (TypeError, ValueError):
                raise ApiError(400, "invalid_input", f"{key} không hợp lệ.") from None
    if item.starts_at and item.ends_at and item.starts_at > item.ends_at:
        raise ApiError(400, "invalid_input", "Thời gian kết thúc phải sau bắt đầu.")
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            raise ApiError(400, "invalid_input", "is_active phải là boolean.")
        item.is_active = data["is_active"]
    if item.usage_limit is not None and item.usage_limit < (item.used_count or 0):
        raise ApiError(400, "invalid_input", "Giới hạn nhỏ hơn số lần đã dùng.")
    db.session.add(item)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "discount_exists", "Mã đã tồn tại.") from None
    return jsonify(discount_data(item)), 200 if discount_id else 201
