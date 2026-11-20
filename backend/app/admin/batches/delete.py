"""Quản trị batches: thao tác delete."""

from flask import jsonify
from sqlalchemy.exc import IntegrityError
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.errors import ApiError
from app.models import ProduceBatch


@admin_api.delete("/batches/<int:batch_id>")
@require_role("admin")
def delete_batch(batch_id: int):
    """Xóa lô chưa được dùng trong đơn; nhận batch_id, trả ok hoặc 409."""
    batch = db.session.get(ProduceBatch, batch_id)
    if batch is None:
        raise ApiError(404, "not_found", "Không tìm thấy lô.")
    db.session.delete(batch)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "batch_in_use", "Lô đã được dùng trong đơn hàng.") from None
    return jsonify({"ok": True})
