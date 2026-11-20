"""auth: me; tách xử lý theo thao tác API."""

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


@auth_api.get("/me")
@require_role("admin", "customer")
def me():
    """Xác nhận token và vai trò mới nhất từ DB; đầu vào Bearer token, đầu ra user. Ví dụ middleware kiểm tra admin."""
    return jsonify({"id": g.user.id, "name": g.user.name, "email": g.user.email, "phone": g.user.phone, "role": g.user.role})

