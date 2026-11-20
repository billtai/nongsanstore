"""products: batches; tách xử lý theo thao tác API."""

from flask import jsonify, request
from sqlalchemy import func
from app import db
from app.helpers import page_args
from app.errors import ApiError
from app.models import ProduceBatch, Product
from app.products import product_api
from app.products.data import batch_data, product_data


@product_api.get("/<int:product_id>/batches")
def list_product_batches(product_id: int):
    """Xem lô của sản phẩm đang bán; nhận page/limit, trả nguồn gốc từng lô."""
    product = db.session.get(Product, product_id)
    if product is None or not product.is_visible:
        raise ApiError(404, "not_found", "Không tìm thấy sản phẩm.")
    page, limit = page_args()
    result      = db.session.query(ProduceBatch).filter_by(product_id=product_id, is_visible=True).order_by(ProduceBatch.harvest_date, ProduceBatch.id).paginate(page=page, per_page=limit, error_out=False)
    return jsonify({"items": [batch_data(batch) for batch in result.items], "page": page, "limit": limit, "total": result.total})

