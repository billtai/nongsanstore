"""products: data; tách xử lý theo thao tác API."""

from flask import jsonify, request
from sqlalchemy import func
from app import db
from app.helpers import page_args
from app.errors import ApiError
from app.models import ProduceBatch, Product
from app.products import product_api


def product_data(product: Product, stock=0):
    """Đổi Product thành JSON; đầu vào sản phẩm/tồn, đầu ra dữ liệu công khai."""
    return {"id": product.id, "slug": product.slug, "name": product.name, "category": product.category, "description": product.description, "unit": product.unit, "price_vnd": product.price_vnd, "image_url": product.image_url, "images": [{"id": image.id, "image_url": image.image_url} for image in product.images], "is_visible": product.is_visible, "stock": str(stock)}



def batch_data(batch: ProduceBatch, include_product_name: bool = False):
    """Đổi lô thành JSON; đầu vào lô và cờ admin, đầu ra tồn cùng đơn vị khi admin xem. Ví dụ batch_data(batch, True) trả product_name và unit."""
    data = {"id": batch.id, "product_id": batch.product_id, "batch_code": batch.batch_code, "growing_region": batch.growing_region, "origin": batch.origin, "harvest_date": batch.harvest_date.isoformat(), "remaining_quantity": str(batch.remaining_quantity), "is_visible": batch.is_visible}
    if include_product_name:
        data["product_name"] = batch.product.name
        data["unit"]         = batch.product.unit
    return data

