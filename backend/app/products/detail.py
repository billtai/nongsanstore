"""products: detail; tách xử lý theo thao tác API."""

from flask import jsonify, request
from sqlalchemy import func
from app import db
from app.helpers import page_args
from app.errors import ApiError
from app.models import ProduceBatch, Product
from app.products import product_api
from app.products.data import batch_data, product_data


@product_api.get("/<int:product_id>")
def get_product(product_id: int):
    """Xem sản phẩm đang bán; đầu vào product_id, đầu ra giá và tồn."""
    product = db.session.get(Product, product_id)
    if product is None or not product.is_visible:
        raise ApiError(404, "not_found", "Không tìm thấy sản phẩm.")
    stock = db.session.query(func.coalesce(func.sum(ProduceBatch.remaining_quantity), 0)).filter_by(product_id=product_id, is_visible=True).scalar()
    return jsonify(product_data(product, stock))


@product_api.get("/by-slug/<string:slug>")
def get_product_by_slug(slug: str):
    """Tra sản phẩm công khai theo slug; đầu vào slug URL, đầu ra sản phẩm và tồn; ví dụ /by-slug/ca-rot-da-lat."""
    product = db.session.query(Product).filter_by(slug=slug, is_visible=True).first()
    if product is None:
        raise ApiError(404, "not_found", "Không tìm thấy sản phẩm.")
    stock = db.session.query(func.coalesce(func.sum(ProduceBatch.remaining_quantity), 0)).filter_by(product_id=product.id, is_visible=True).scalar()
    return jsonify(product_data(product, stock))

