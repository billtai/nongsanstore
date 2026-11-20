"""products: list; tách xử lý theo thao tác API."""

from flask import jsonify, request
from sqlalchemy import exists, func, select
from app import db
from app.helpers import page_args
from app.errors import ApiError
from app.models import ProduceBatch, Product, ProductUnit
from app.products import product_api
from app.products.data import batch_data, product_data
from app.products.categories import PRODUCT_CATEGORIES


@product_api.get("")
@product_api.get("/")
def list_products():
    """Liệt kê hàng còn tồn trước; nhận q/unit/category/page/limit, trả items và total.

    Ví dụ: GET /products?limit=10 trả sản phẩm còn hàng trước sản phẩm hết hàng.
    """
    page, limit = page_args()
    query       = db.session.query(Product).filter(Product.is_visible.is_(True))
    search      = request.args.get("q", "").strip()
    unit        = request.args.get("unit")
    category    = request.args.get("category", "").strip()
    if search:
        query = query.filter(Product.name.ilike(f"%{search}%"))
    if unit:
        if db.session.query(ProductUnit).filter_by(code=unit).first() is None:
            raise ApiError(400, "invalid_input", "Đơn vị không tồn tại.")
        query = query.filter(Product.unit == unit)
    if category:
        query = query.filter(Product.category == category)
    # Sắp xếp trên database trước khi phân trang; một lô có tồn dương nghĩa là sản phẩm còn hàng.
    # Ví dụ: lô còn 0 và lô còn 2 của cùng sản phẩm vẫn xếp sản phẩm đó ở nhóm còn hàng.
    in_stock = exists(select(ProduceBatch.id).where(ProduceBatch.product_id == Product.id, ProduceBatch.is_visible.is_(True), ProduceBatch.remaining_quantity > 0))
    result   = query.order_by(in_stock.desc(), Product.created_at.desc(), Product.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    product_ids = [product.id for product in result.items]
    stocks      = dict(db.session.query(ProduceBatch.product_id, func.sum(ProduceBatch.remaining_quantity)).filter(ProduceBatch.product_id.in_(product_ids), ProduceBatch.is_visible.is_(True)).group_by(ProduceBatch.product_id).all()) if product_ids else {}
    return jsonify({"items": [product_data(product, stocks.get(product.id, 0)) for product in result.items], "page": page, "limit": limit, "total": result.total})


@product_api.get("/categories")
def list_categories():
    """Liệt kê danh mục cửa hàng; đầu vào không có, đầu ra mảng chuỗi; ví dụ /products/categories."""
    return jsonify({"items": PRODUCT_CATEGORIES})

