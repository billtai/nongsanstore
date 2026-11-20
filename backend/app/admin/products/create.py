"""Quản trị products: thao tác create."""

from flask import jsonify
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.helpers import integer_value, json_body, required_text
from app.errors import ApiError
from app.models import Product, ProductUnit
from app.products import product_data
from app.products.categories import PRODUCT_CATEGORIES


@admin_api.post("/products")
@require_role("admin")
def create_product():
    """Tạo sản phẩm; nhận name/unit/price_vnd và mô tả/ảnh tùy chọn; trả sản phẩm."""
    data        = json_body()
    name        = required_text(data, "name", 180)
    unit        = required_text(data, "unit", 10)
    price       = integer_value(data.get("price_vnd"), "price_vnd", 0)
    description = data.get("description", "")
    image_url   = data.get("image_url")
    unit_record = db.session.query(ProductUnit).filter_by(code=unit).first()
    if unit_record is None or not unit_record.is_active:
        raise ApiError(400, "invalid_input", "Đơn vị không tồn tại hoặc đã tắt.")
    if not isinstance(description, str) or len(description) > 5000 or (image_url is not None and (not isinstance(image_url, str) or len(image_url) > 500)):
        raise ApiError(400, "invalid_input", "unit, description hoặc image_url không hợp lệ.")
    category = required_text(data, "category", 80)
    if category not in PRODUCT_CATEGORIES:
        raise ApiError(400, "invalid_input", "Danh mục không hợp lệ.")
    product = Product(name=name, category=category, unit=unit, price_vnd=price, description=description, image_url=image_url)
    db.session.add(product)
    db.session.commit()
    return jsonify(product_data(product)), 201
