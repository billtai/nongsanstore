"""auth: security; tách xử lý theo thao tác API."""

from functools import wraps
from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from app.helpers import json_body, required_text
from app.errors import ApiError
from app.models import Customer
from app.auth import auth_api


def token_serializer():
    """Tạo bộ ký token từ SECRET_KEY; ví dụ login dùng để ký customer id."""
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="nong-san-auth-v1")



def require_role(*roles):
    """Kiểm tra token và vai trò; ví dụ @require_role('admin') chặn khách hàng."""
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            header = request.headers.get("Authorization", "")
            if not header.startswith("Bearer "):
                raise ApiError(401, "unauthorized", "Thiếu Bearer token.")
            try:
                user_id = token_serializer().loads(header[7:], max_age=86400)
            except (BadSignature, SignatureExpired):
                raise ApiError(401, "unauthorized", "Token không hợp lệ hoặc đã hết hạn.") from None
            user = db.session.get(Customer, user_id)
            if user is None:
                raise ApiError(401, "unauthorized", "Tài khoản không tồn tại.")
            if user.role not in roles:
                raise ApiError(403, "forbidden", "Không có quyền truy cập.")
            g.user = user
            return view(*args, **kwargs)
        return wrapped
    return decorator

