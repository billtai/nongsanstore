import os
from pathlib import Path

from flask import Flask, jsonify, request, send_from_directory
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from werkzeug.exceptions import HTTPException

db = SQLAlchemy()
migrate = Migrate()


def create_app() -> Flask:
    """Tạo ứng dụng Flask từ biến môi trường.

    Đầu vào: DATABASE_URL và FRONTEND_ORIGIN trong môi trường hoặc tệp .env.
    Đầu ra: ứng dụng Flask đã cấu hình database, CORS và route kiểm tra.
    Ví dụ: flask --app app run gọi hàm này qua Flask CLI.
    """
    app = Flask(__name__)

    database_url    = os.getenv("DATABASE_URL")
    frontend_origin = os.getenv("FRONTEND_ORIGIN")
    secret_key      = os.getenv("SECRET_KEY")

    if not database_url:
        raise RuntimeError("Thiếu DATABASE_URL. Hãy cấu hình backend/.env.")
    if not frontend_origin:
        raise RuntimeError("Thiếu FRONTEND_ORIGIN. Hãy cấu hình backend/.env.")
    if not secret_key or secret_key == "replace_with_a_long_random_secret":
        raise RuntimeError("Thiếu SECRET_KEY an toàn. Hãy cấu hình backend/.env.")

    app.config["SQLALCHEMY_DATABASE_URI"] = database_url
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    app.config["SECRET_KEY"] = secret_key
    app.config["ASSETS_DIR"] = Path(__file__).resolve().parents[2] / "assets"
    app.config["MAX_CONTENT_LENGTH"] = 60 * 1024 * 1024

    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app, resources={r"/api/*": {"origins": [frontend_origin]}}, supports_credentials=True)
    app.config["SESSION_COOKIE_HTTPONLY"] = True
    app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

    from app import models  # noqa: F401; đăng ký model cho migration.
    from app.errors import ApiError, handle_api_error, handle_http_error
    from app.auth import auth_api
    from app.products import product_api
    from app.orders import order_api
    from app.admin import admin_api
    from app.routes import api
    from app.commands import register_commands

    app.register_error_handler(ApiError, handle_api_error)
    app.register_error_handler(HTTPException, handle_http_error)

    @app.errorhandler(Exception)
    def handle_unexpected_error(error):
        """Trả lỗi JSON nhất quán và giấu chi tiết server; ví dụ lỗi DB trả 500."""
        db.session.rollback()
        app.logger.exception("Unhandled API error", exc_info=error)
        return jsonify({"error": {"code": "internal_error", "message": "Lỗi máy chủ."}}), 500
    app.register_blueprint(api, url_prefix="/api/v1")
    app.register_blueprint(auth_api, url_prefix="/api/v1/auth")
    app.register_blueprint(product_api, url_prefix="/api/v1/products")
    app.register_blueprint(order_api, url_prefix="/api/v1/orders")
    app.register_blueprint(admin_api, url_prefix="/api/v1/admin")
    register_commands(app)

    @app.before_request
    def release_expired_preorders():
        """Dọn giữ hàng hết hạn trước API; đầu vào: yêu cầu API, đầu ra: tồn mới nếu quá 24 giờ. Ví dụ: mở sản phẩm sau hạn sẽ thấy lại 1 kg."""
        if not request.path.startswith("/api/v1/"):
            return
        from app.orders.reservations import expire_reservations
        if expire_reservations():
            db.session.commit()

    @app.get("/assets/<path:filename>")
    def serve_asset(filename: str):
        """Phục vụ ảnh đã tải lên; đầu vào đường dẫn tương đối, đầu ra tệp ảnh."""
        return send_from_directory(app.config["ASSETS_DIR"], filename)

    return app
