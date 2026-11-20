"""Số liệu trang chủ quản trị, tổng hợp trong database thay vì tải danh sách đơn."""

from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

from flask import jsonify, request
from sqlalchemy import case, func

from app import db
from app.admin import admin_api
from app.auth import require_role
from app.errors import ApiError
from app.helpers import integer_value, order_date_range, page_args
from app.models import Order, ProduceBatch, Product


@admin_api.get("/overview")
@require_role("admin")
def admin_overview():
    """Nhận aging_page (mặc định 1); trả số đơn theo kỳ, biểu đồ và trang 10 lô tồn quá 72 giờ. Ví dụ: aging_page=2 lấy lô 11-20."""
    zone       = ZoneInfo("Asia/Ho_Chi_Minh")
    today      = datetime.now(zone).date()
    day_start  = datetime(today.year, today.month, today.day, tzinfo=zone)
    month_start = datetime(today.year, today.month, 1, tzinfo=zone)
    year_start = datetime(today.year, 1, 1, tzinfo=zone)
    last_month = (month_start - timedelta(days=1)).replace(day=1)
    last_year  = datetime(today.year - 1, 1, 1, tzinfo=zone)
    next_year  = datetime(today.year + 1, 1, 1, tzinfo=zone)
    boundaries = {
        "today"          : (day_start, day_start + timedelta(days=1)),
        "previous_day"   : (day_start - timedelta(days=1), day_start),
        "month"          : (month_start, (month_start + timedelta(days=32)).replace(day=1)),
        "previous_month" : (last_month, month_start),
        "year"           : (year_start, next_year),
        "previous_year"  : (last_year, year_start),
    }
    # Đầu vào: các khoảng ngày theo giờ Việt Nam; đầu ra: sáu bộ đếm trong một truy vấn.
    # Ví dụ: đơn lúc 17:30 UTC ngày 17 được tính vào ngày 18 tại Việt Nam.
    counts = db.session.query(*[
        func.sum(case((Order.created_at >= start.astimezone(timezone.utc), 1), else_=0)).filter(
            Order.created_at < end.astimezone(timezone.utc)
        ).label(name)
        for name, (start, end) in boundaries.items()
    ]).filter(Order.created_at >= last_year.astimezone(timezone.utc), Order.created_at < next_year.astimezone(timezone.utc)).one()

    # Database nhóm theo tháng để frontend chỉ nhận 12 điểm dữ liệu; SQLite dùng cho test.
    # Đầu vào: created_at UTC; đầu ra: khóa YYYY-MM theo Asia/Ho_Chi_Minh.
    # Ví dụ: 2026-11-17 17:30 UTC thuộc nhóm 2026-11.
    if db.engine.dialect.name == "sqlite":
        month_key = func.strftime("%Y-%m", func.datetime(Order.created_at, "+7 hours"))
    else:
        month_key = func.to_char(func.timezone("Asia/Ho_Chi_Minh", Order.created_at), "YYYY-MM")
    first_chart_month = month_start
    for _ in range(11):
        first_chart_month = (first_chart_month - timedelta(days=1)).replace(day=1)
    grouped = dict(db.session.query(month_key, func.count(Order.id)).filter(
        Order.created_at >= first_chart_month.astimezone(timezone.utc),
        Order.created_at < next_year.astimezone(timezone.utc),
    ).group_by(month_key).all())
    chart = []
    cursor = first_chart_month
    for _ in range(12):
        key = cursor.strftime("%Y-%m")
        chart.append({"month": key, "orders": grouped.get(key, 0)})
        cursor = (cursor + timedelta(days=32)).replace(day=1)
    aging_page   = integer_value(request.args.get("aging_page", "1"), "aging_page", 1)
    aging_cutoff = datetime.now(timezone.utc) - timedelta(days=3)
    aging_query  = db.session.query(
        ProduceBatch.id,
        ProduceBatch.batch_code,
        ProduceBatch.created_at,
        ProduceBatch.remaining_quantity,
        Product.id.label("product_id"),
        Product.name.label("product_name"),
        Product.unit,
    ).join(Product, Product.id == ProduceBatch.product_id).filter(
        ProduceBatch.created_at < aging_cutoff,
        ProduceBatch.remaining_quantity > 0,
    )
    # Đầu vào: lô còn tồn, tạo trước mốc 72 giờ; đầu ra: tổng số và 10 lô cũ nhất.
    # Ví dụ: 50 lô quá hạn, aging_page=2 chỉ gửi lô 11-20.
    aging_total = aging_query.count()
    aging_rows  = aging_query.order_by(ProduceBatch.created_at.asc(), ProduceBatch.id.asc()).offset((aging_page - 1) * 10).limit(10).all()
    aging_items = [{
        "id"                 : row.id,
        "batch_code"         : row.batch_code,
        "product_id"         : row.product_id,
        "product_name"       : row.product_name,
        "unit"               : row.unit,
        "remaining_quantity" : str(row.remaining_quantity),
        "created_at"         : row.created_at.isoformat(),
    } for row in aging_rows]
    return jsonify({
        "timezone"     : "Asia/Ho_Chi_Minh",
        "as_of"        : datetime.now(timezone.utc).isoformat(),
        "counts"       : {name: int(getattr(counts, name) or 0) for name in boundaries},
        "monthly"      : chart,
        "aging_batches": {"items": aging_items, "total": aging_total, "page": aging_page, "limit": 10, "threshold_hours": 72},
    })


@admin_api.get("/overview/daily-revenue")
@require_role("admin")
def admin_daily_revenue():
    """Nhận page/limit/from_date/to_date; trả doanh thu từng ngày tạo đơn từ đơn completed. Ví dụ: from_date=2026-11-18&to_date=2026-11-18 lấy đúng một ngày Việt Nam."""
    page, limit = page_args()
    from_date   = request.args.get("from_date")
    to_date     = request.args.get("to_date")
    start = order_date_range(from_date)[0] if from_date is not None else None
    end   = order_date_range(to_date)[1] if to_date is not None else None
    if start is not None and end is not None and start >= end:
        raise ApiError(400, "invalid_input", "Ngày bắt đầu không được sau ngày kết thúc.")
    # Đầu vào: created_at UTC; đầu ra: ngày tạo đơn theo Asia/Ho_Chi_Minh.
    # Ví dụ: 17:30 UTC ngày 17 thuộc dòng ngày 18 tại Việt Nam.
    if db.engine.dialect.name == "sqlite":
        local_day = func.strftime("%Y-%m-%d", func.datetime(Order.created_at, "+7 hours"))
    else:
        local_day = func.to_char(func.timezone("Asia/Ho_Chi_Minh", Order.created_at), "YYYY-MM-DD")
    grouped = db.session.query(
        local_day.label("day"),
        func.count(Order.id).label("order_count"),
        func.sum(Order.total_vnd).label("total_vnd"),
    ).filter(Order.status == "completed").group_by(local_day)
    # Lọc bằng khoảng UTC để tận dụng chỉ mục status/created_at trước khi nhóm ngày.
    # Ví dụ: 2026-11-18 bắt đầu từ 17:00 UTC ngày 17 và kết thúc 17:00 UTC ngày 18.
    if start is not None:
        grouped = grouped.filter(Order.created_at >= start)
    if end is not None:
        grouped = grouped.filter(Order.created_at < end)
    total_days = db.session.query(func.count()).select_from(grouped.subquery()).scalar()
    rows       = grouped.order_by(local_day.desc()).offset((page - 1) * limit).limit(limit).all()
    return jsonify({
        "items"    : [{"day": row.day, "order_count": row.order_count, "total_vnd": int(row.total_vnd)} for row in rows],
        "page"     : page,
        "limit"    : limit,
        "total"    : total_days,
        "timezone" : "Asia/Ho_Chi_Minh",
    })
