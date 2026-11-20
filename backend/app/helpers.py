"""Kiểm tra đầu vào và phân trang dùng chung cho các endpoint."""

from decimal import Decimal, InvalidOperation
from datetime import date, datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import g, request

from app.errors import ApiError


def json_body() -> dict:
    """Lấy JSON object từ request; ví dụ {"name":"Cà rốt"}; lỗi 400 nếu sai dạng."""
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise ApiError(400, "invalid_json", "Body phải là JSON object.")
    return data


def required_text(data: dict, key: str, max_length: int) -> str:
    """Lấy chuỗi bắt buộc đã trim; ví dụ required_text(data, 'name', 120)."""
    value = data.get(key)
    if not isinstance(value, str) or not value.strip() or len(value.strip()) > max_length:
        raise ApiError(400, "invalid_input", f"{key} phải là chuỗi 1-{max_length} ký tự.")
    return value.strip()


def integer_value(value, name: str, minimum: int = 0) -> int:
    """Kiểm tra số nguyên; ví dụ integer_value(2, 'page', 1) trả 2."""
    if isinstance(value, bool):
        raise ApiError(400, "invalid_input", f"{name} phải là số nguyên >= {minimum}.")
    try:
        number = int(value)
    except (TypeError, ValueError):
        raise ApiError(400, "invalid_input", f"{name} phải là số nguyên >= {minimum}.") from None
    if str(number) != str(value) or number < minimum:
        raise ApiError(400, "invalid_input", f"{name} phải là số nguyên >= {minimum}.")
    return number


def quantity_value(value, unit: str):
    """Đọc số lượng theo cấu hình đơn vị; ví dụ kg nhận 0.5, hộp chỉ nhận số nguyên."""
    if not hasattr(g, "unit_fraction_map"):
        from app import db
        from app.models import ProductUnit

        # Một truy vấn cho toàn request, kể cả đơn có nhiều dòng sản phẩm.
        g.unit_fraction_map = dict(db.session.query(ProductUnit.code, ProductUnit.allows_fraction).all())
    allows_fraction = g.unit_fraction_map.get(unit)
    if allows_fraction is None:
        raise ApiError(400, "invalid_input", "Đơn vị không tồn tại.")
    try:
        quantity = Decimal(str(value))
    except (InvalidOperation, TypeError):
        raise ApiError(400, "invalid_input", "Số lượng không hợp lệ.") from None
    if not quantity.is_finite() or quantity <= 0 or quantity > 999999999 or quantity.as_tuple().exponent < -3:
        raise ApiError(400, "invalid_input", "Số lượng phải > 0 và tối đa 3 số lẻ.")
    if not allows_fraction and quantity != quantity.to_integral_value():
        raise ApiError(400, "invalid_input", f"Đơn vị {unit} chỉ nhận số lượng nguyên.")
    return quantity


def page_args():
    """Đọc page/limit, giới hạn 100 dòng; ví dụ ?page=2&limit=20."""
    page  = integer_value(request.args.get("page", "1"), "page", 1)
    limit = integer_value(request.args.get("limit", "20"), "limit", 1)
    if limit > 100:
        raise ApiError(400, "invalid_input", "limit tối đa 100.")
    return page, limit


def order_date_range(value: str):
    """Đổi ngày Việt Nam thành khoảng UTC để lọc theo chỉ mục thời gian. Đầu vào: YYYY-MM-DD; đầu ra: [đầu ngày, đầu ngày kế). Ví dụ: 2026-11-18 bắt đầu lúc 17:00 UTC ngày trước."""
    try:
        local_day = date.fromisoformat(value)
        if local_day.isoformat() != value:
            raise ValueError("date format")
    except ValueError:
        raise ApiError(400, "invalid_input", "Ngày đặt phải có dạng YYYY-MM-DD.") from None
    zone  = ZoneInfo("Asia/Ho_Chi_Minh")
    start = datetime.combine(local_day, datetime.min.time(), zone).astimezone(timezone.utc)
    end   = (datetime.combine(local_day, datetime.min.time(), zone) + timedelta(days=1)).astimezone(timezone.utc)
    return start, end


def page_result(query, serializer):
    """Phân trang query; đầu ra gồm items, page, limit, total."""
    page, limit = page_args()
    result      = query.paginate(page=page, per_page=limit, error_out=False)
    return {
        "items" : [serializer(row) for row in result.items],
        "page"  : page,
        "limit" : limit,
        "total" : result.total,
    }
