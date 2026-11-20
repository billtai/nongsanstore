"""Ký báo giá ngắn hạn; không lưu giá hay giỏ tạm trong database."""

from flask import current_app
from itsdangerous import BadSignature, SignatureExpired, URLSafeTimedSerializer

from app.errors import ApiError


def quote_serializer():
    """Tạo bộ ký báo giá từ SECRET_KEY; đầu ra serializer riêng với token đăng nhập."""
    return URLSafeTimedSerializer(current_app.config["SECRET_KEY"], salt="nong-san-quote-v1")


def read_quote(token: str, customer_id: int) -> dict:
    """Đọc báo giá 15 phút của đúng khách; ví dụ token của khách khác trả 403."""
    try:
        data = quote_serializer().loads(token, max_age=900)
    except SignatureExpired:
        raise ApiError(409, "quote_expired", "Báo giá đã hết hạn. Vui lòng lấy báo giá mới.") from None
    except BadSignature:
        raise ApiError(400, "invalid_quote", "Mã báo giá không hợp lệ.") from None
    if not isinstance(data, dict) or data.get("customer_id") != customer_id:
        raise ApiError(403, "forbidden", "Báo giá không thuộc tài khoản này.")
    return data
