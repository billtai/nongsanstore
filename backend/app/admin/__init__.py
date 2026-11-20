"""API quản trị theo nghiệp vụ; nhập module để đăng ký toàn bộ route."""

from flask import Blueprint

admin_api = Blueprint("admin", __name__)

from app.admin import products, batches, orders, customers, discounts, units, procurement, overview  # noqa: E402,F401
