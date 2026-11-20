"""Quản trị products: thao tác update."""

from flask import jsonify
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.helpers import integer_value, json_body, required_text
from app.errors import ApiError
from app.models import Product, ProductUnit, ProduceBatch
from app.products import product_data
from app.products.categories import PRODUCT_CATEGORIES


@admin_api.patch("/products/<int:product_id>")
@require_role("admin")
def update_product(product_id: int):
    """Sửa hoặc ẩn sản phẩm; nhận các trường cần đổi, trả sản phẩm đã cập nhật."""
    product = db.session.get(Product, product_id)
    if product is None:
        raise ApiError(404, "not_found", "Không tìm thấy sản phẩm.")
    data = json_body()
    if not data or set(data) - {"name", "category", "description", "price_vnd", "image_url", "is_visible", "unit"}:
        raise ApiError(400, "invalid_input", "Trường cập nhật không hợp lệ.")
    if "name" in data:
        product.name = required_text(data, "name", 180)
    if "category" in data:
        product.category = required_text(data, "category", 80)
        if product.category not in PRODUCT_CATEGORIES:
            raise ApiError(400, "invalid_input", "Danh mục không hợp lệ.")
    if "unit" in data:
        selected_unit = required_text(data, "unit", 10)
        if selected_unit != product.unit:
            unit_record = db.session.query(ProductUnit).filter_by(code=selected_unit).first()
            if unit_record is None or not unit_record.is_active:
                raise ApiError(400, "invalid_input", "Đơn vị không tồn tại hoặc đã tắt.")
            if db.session.query(ProduceBatch.id).filter(ProduceBatch.product_id == product.id, ProduceBatch.remaining_quantity > 0).first():
                raise ApiError(409, "product_has_stock", "Cần xử lý hết tồn kho trước khi đổi đơn vị sản phẩm.")
            product.unit = selected_unit
    if "price_vnd" in data:
        product.price_vnd = integer_value(data["price_vnd"], "price_vnd", 0)
    if "description" in data:
        if not isinstance(data["description"], str) or len(data["description"]) > 5000:
            raise ApiError(400, "invalid_input", "description không hợp lệ.")
        product.description = data["description"]
    if "image_url" in data:
        if data["image_url"] is not None and (not isinstance(data["image_url"], str) or len(data["image_url"]) > 500):
            raise ApiError(400, "invalid_input", "image_url không hợp lệ.")
        product.image_url = data["image_url"]
    if "is_visible" in data:
        if not isinstance(data["is_visible"], bool):
            raise ApiError(400, "invalid_input", "is_visible phải là boolean.")
        product.is_visible = data["is_visible"]
    db.session.commit()
    return jsonify(product_data(product))
