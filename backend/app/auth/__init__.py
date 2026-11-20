"""Đăng ký API auth và xuất hàm dùng chung."""

from flask import Blueprint

auth_api = Blueprint("auth", __name__)

from app.auth.security import require_role, token_serializer
from app.auth import register  # noqa: F401
from app.auth import login  # noqa: F401
from app.auth import me  # noqa: F401
