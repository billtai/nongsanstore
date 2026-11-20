import os

from dotenv import load_dotenv

load_dotenv()

from app import create_app  # noqa: E402  # Nạp .env trước khi tạo ứng dụng.

app = create_app()

if __name__ == "__main__":
    # Đầu vào: PORT và FLASK_DEBUG; đầu ra: máy chủ local phục vụ API.
    # Ví dụ: python run.py phục vụ trên cổng 5000 nếu PORT=5000.
    app.run(
        host  = "127.0.0.1",
        port  = int(os.getenv("PORT", "5000")),
        debug = os.getenv("FLASK_DEBUG", "false").lower() == "true",
    )
