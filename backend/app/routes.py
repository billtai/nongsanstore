from flask import Blueprint, jsonify

api = Blueprint("api", __name__)


@api.get("/health")
def health():
    """Báo ứng dụng Flask đang hoạt động, không kiểm tra kết nối database.

    Đầu vào: GET /api/v1/health, không có body.
    Đầu ra: HTTP 200 và JSON {"status": "ok"}.
    Ví dụ: curl http://localhost:5000/api/v1/health.
    """
    return jsonify({"status": "ok"})
