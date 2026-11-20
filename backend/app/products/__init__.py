"""Đăng ký API products và xuất hàm dùng chung."""

from flask import Blueprint

product_api = Blueprint("products", __name__)

from app.products.data import batch_data, product_data
from app.products import list  # noqa: F401
from app.products import detail  # noqa: F401
from app.products import batches  # noqa: F401
