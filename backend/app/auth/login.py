"""auth: login; tách xử lý theo thao tác API."""

from functools import wraps
import hashlib
import hmac
from flask import current_app, g, jsonify, request
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer
from sqlalchemy.exc import IntegrityError
from werkzeug.security import check_password_hash, generate_password_hash
from app import db
from app.helpers import json_body, required_text
from app.errors import ApiError
from app.models import Customer
from app.auth import auth_api
from app.auth.security import require_role, token_serializer


def password_matches(stored_hash: str, password: str) -> bool:
    """Kiểm tra cả hash scrypt cũ và hash Werkzeug hiện tại. Đầu vào: hash lưu DB, mật khẩu nhập; đầu ra: đúng/sai. Ví dụ: scrypt:32768:8:1$salt$hex được đối chiếu bằng hashlib.scrypt."""
    if not stored_hash.startswith("scrypt:"):
        return check_password_hash(stored_hash, password)
    try:
        method, salt, expected = stored_hash.split("$", 2)
        _, n, r, p           = method.split(":")
        params               = (int(n), int(r), int(p))
        if params != (32768, 8, 1):
            return False
        actual = hashlib.scrypt(password.encode(), salt=salt.encode(), n=params[0], r=params[1], p=params[2], maxmem=64 * 1024 * 1024).hex()
        return hmac.compare_digest(actual, expected)
    except (ValueError, TypeError):
        return False


@auth_api.post("/login")
def login():
    """Đăng nhập email/password; trả token, loại token, hạn dùng và thông tin tài khoản."""
    data     = json_body()
    email    = required_text(data, "email", 255).lower()
    password = required_text(data, "password", 128)
    user     = db.session.query(Customer).filter_by(email=email).first()
    if user is None or not password_matches(user.password_hash, password):
        raise ApiError(401, "invalid_credentials", "Email hoặc mật khẩu không đúng.")
    token = token_serializer().dumps(user.id)
    return jsonify({"access_token": token, "token_type": "Bearer", "expires_in": 86400, "user": {"id": user.id, "name": user.name, "role": user.role}})

