"""Lỗi API thống nhất để frontend xử lý ổn định."""

from flask import jsonify
from werkzeug.exceptions import HTTPException


class ApiError(Exception):
    """Mang HTTP status, mã lỗi và thông báo; ví dụ ApiError(404, 'not_found', 'Không tìm thấy')."""

    def __init__(self, status: int, code: str, message: str):
        self.status  = status
        self.code    = code
        self.message = message


def handle_api_error(error: ApiError):
    """Đổi ApiError thành JSON và HTTP status; đầu vào lỗi, đầu ra response."""
    return jsonify({"error": {"code": error.code, "message": error.message}}), error.status


def handle_http_error(error: HTTPException):
    """Đổi lỗi HTTP thành JSON; ví dụ đường dẫn lạ trả lỗi 404 cùng cấu trúc."""
    code = error.name.lower().replace(" ", "_")
    return jsonify({"error": {"code": code, "message": error.description}}), error.code
