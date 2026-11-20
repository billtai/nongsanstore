"""auth: register; tách xử lý theo thao tác API."""

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
from app.auth.security import require_role, token_serializer


@auth_api.post("/register")
def register():
    """Tạo tài khoản customer; nhận name/email/phone/password, trả thông tin công khai."""
    data     = json_body()
    name     = required_text(data, "name", 120)
    email    = required_text(data, "email", 255).lower()
    phone    = required_text(data, "phone", 30)
    password = required_text(data, "password", 128)
    if "@" not in email or len(password) < 8:
        raise ApiError(400, "invalid_input", "Email không hợp lệ hoặc mật khẩu dưới 8 ký tự.")
    user = Customer(name=name, email=email, phone=phone, password_hash=generate_password_hash(password), role="customer")
    db.session.add(user)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "email_exists", "Email đã được đăng ký.") from None
    return jsonify({"id": user.id, "name": user.name, "email": user.email, "role": user.role}), 201

