"""Chuyển model mã giảm giá sang dữ liệu API."""

from app.models import DiscountCode


def discount_data(item: DiscountCode):
    """Đổi mã giảm giá thành JSON cho bảng/form; ví dụ code, value và used_count."""
    return {"id": item.id, "code": item.code, "kind": item.kind, "value": item.value, "min_subtotal_vnd": item.min_subtotal_vnd, "starts_at": item.starts_at.isoformat() if item.starts_at else None, "ends_at": item.ends_at.isoformat() if item.ends_at else None, "usage_limit": item.usage_limit, "used_count": item.used_count, "is_active": item.is_active}
