"""Thời gian UTC dùng chung cho các bảng dữ liệu."""

from datetime import datetime, timezone


def now_utc():
    """Không nhận đầu vào; trả thời điểm UTC. Ví dụ: dùng cho created_at của đơn."""
    return datetime.now(timezone.utc)
