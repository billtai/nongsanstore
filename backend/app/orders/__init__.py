"""Đăng ký API orders và xuất hàm dùng chung."""

from flask import Blueprint

order_api = Blueprint("orders", __name__)

from app.orders.data import order_data
from app.orders import quote  # noqa: F401
from app.orders import momo  # noqa: F401
from app.orders import sepay  # noqa: F401
from app.orders import sepay_bank  # noqa: F401
from app.orders import create  # noqa: F401
from app.orders import list  # noqa: F401
from app.orders import detail  # noqa: F401
from app.orders import preorder  # noqa: F401
