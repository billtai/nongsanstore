"""Quản trị batches: thao tác create."""

from datetime import date
from secrets import token_hex
from flask import jsonify
from sqlalchemy.exc import IntegrityError
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.helpers import integer_value, json_body, quantity_value, required_text
from app.errors import ApiError
from app.models import ProduceBatch, Product
from app.products import batch_data
from app.products.slug import slugify
from app.orders.reservations import allocate_waiting_preorders, expire_reservations


@admin_api.post("/batches")
@require_role("admin")
def create_batch():
    """Tạo lô và mã từ tên sản phẩm; nhận product_id/ngày/vùng/tồn, trả lô. Ví dụ Cà rốt -> CA-ROT-20261117-<mã duy nhất>."""
    data       = json_body()
    if "batch_code" in data:
        raise ApiError(400, "invalid_input", "Mã lô được tạo tự động từ tên sản phẩm.")
    product_id = integer_value(data.get("product_id"), "product_id", 1)
    product    = db.session.get(Product, product_id)
    if product is None:
        raise ApiError(404, "not_found", "Không tìm thấy sản phẩm.")
    growing_region = required_text(data, "growing_region", 180)
    origin         = required_text(data, "origin", 255)
    harvest_text   = required_text(data, "harvest_date", 10)
    try:
        harvest_date = date.fromisoformat(harvest_text)
    except ValueError:
        raise ApiError(400, "invalid_input", "harvest_date phải có dạng YYYY-MM-DD.") from None
    quantity = quantity_value(data.get("quantity"), product.unit)
    # Tên sản phẩm giúp nhận biết lô; ngày và hậu tố ngẫu nhiên giữ mã duy nhất khi nhập nhiều lô cùng ngày.
    # Ví dụ: Cà rốt Đà Lạt ngày 17/11/2026 -> CA-ROT-DA-LAT-20261117-A1B2C3D4E5F60708.
    batch_code = f"{slugify(product.name)[:54].strip('-').upper()}-{harvest_date:%Y%m%d}-{token_hex(8).upper()}"
    batch    = ProduceBatch(product_id=product_id, batch_code=batch_code, growing_region=growing_region, origin=origin, harvest_date=harvest_date, remaining_quantity=quantity)
    db.session.add(batch)
    try:
        db.session.flush()
        expire_reservations()
        allocate_waiting_preorders(product_id)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "batch_exists", "Không thể tạo mã lô duy nhất; hãy thử lại.") from None
    return jsonify(batch_data(batch)), 201
