"""API quản trị đơn vị: danh sách, thêm, sửa và xóa đơn vị chưa dùng."""

from flask import jsonify, request
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from app import db
from app.admin import admin_api
from app.auth import require_role
from app.errors import ApiError
from app.helpers import json_body, page_args, required_text
from app.models import Product, ProductUnit


def unit_data(unit: ProductUnit, product_count: int):
    """Đổi đơn vị thành JSON; đầu vào unit/số sản phẩm, đầu ra code và cấu hình. Ví dụ kg có allows_fraction=true."""
    return {
        "id"              : unit.id,
        "code"            : unit.code,
        "allows_fraction" : unit.allows_fraction,
        "is_active"       : unit.is_active,
        "product_count"   : product_count,
    }


@admin_api.get("/units")
@require_role("admin")
def list_units():
    """Tìm/lọc đơn vị tại DB; nhận q/active/page/limit, trả danh sách phân trang."""
    page, limit = page_args()
    count  = select(func.count(Product.id)).where(Product.unit == ProductUnit.code).correlate(ProductUnit).scalar_subquery()
    query  = db.session.query(ProductUnit, count.label("product_count"))
    search = request.args.get("q", "").strip()
    active = request.args.get("active")
    if search:
        query = query.filter(ProductUnit.code.ilike(f"%{search}%"))
    if active is not None:
        if active not in ("true", "false"):
            raise ApiError(400, "invalid_input", "active phải là true hoặc false.")
        query = query.filter(ProductUnit.is_active.is_(active == "true"))
    result = query.order_by(ProductUnit.code).paginate(page=page, per_page=limit, error_out=False)
    return jsonify({
        "items" : [unit_data(unit, total) for unit, total in result.items],
        "page"  : page,
        "limit" : limit,
        "total" : result.total,
    })


@admin_api.post("/units")
@require_role("admin")
def create_unit():
    """Thêm đơn vị; nhận code/allows_fraction, trả đơn vị. Ví dụ {code: 'thùng', allows_fraction: false}."""
    data            = json_body()
    code            = required_text(data, "code", 10).lower()
    allows_fraction = data.get("allows_fraction", False)
    if not code.isalnum() or not isinstance(allows_fraction, bool):
        raise ApiError(400, "invalid_input", "Mã đơn vị phải là chữ hoặc số; allows_fraction phải là boolean.")
    unit = ProductUnit(code=code, allows_fraction=allows_fraction, is_active=True)
    db.session.add(unit)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "unit_exists", "Đơn vị đã tồn tại.") from None
    return jsonify(unit_data(unit, 0)), 201


@admin_api.patch("/units/<int:item_id>")
@require_role("admin")
def update_unit(item_id: int):
    """Bật/tắt hoặc sửa chế độ số lẻ; nhận is_active/allows_fraction, trả đơn vị mới."""
    unit = db.session.get(ProductUnit, item_id)
    if unit is None:
        raise ApiError(404, "not_found", "Không tìm thấy đơn vị.")
    data = json_body()
    if not data or set(data) - {"is_active", "allows_fraction"}:
        raise ApiError(400, "invalid_input", "Trường cập nhật không hợp lệ.")
    product_count = db.session.query(func.count(Product.id)).filter_by(unit=unit.code).scalar()
    for key in data:
        if not isinstance(data[key], bool):
            raise ApiError(400, "invalid_input", f"{key} phải là boolean.")
    if "allows_fraction" in data and data["allows_fraction"] != unit.allows_fraction and product_count:
        raise ApiError(409, "unit_in_use", "Không thể đổi chế độ số lẻ khi đơn vị đang được sản phẩm sử dụng.")
    if "is_active" in data:
        unit.is_active = data["is_active"]
    if "allows_fraction" in data:
        unit.allows_fraction = data["allows_fraction"]
    db.session.commit()
    return jsonify(unit_data(unit, product_count))


@admin_api.delete("/units/<int:item_id>")
@require_role("admin")
def delete_unit(item_id: int):
    """Xóa đơn vị chưa dùng; nhận ID, trả ok hoặc 409. Ví dụ DELETE /admin/units/4."""
    unit = db.session.get(ProductUnit, item_id)
    if unit is None:
        raise ApiError(404, "not_found", "Không tìm thấy đơn vị.")
    if db.session.query(Product.id).filter_by(unit=unit.code).first():
        raise ApiError(409, "unit_in_use", "Đơn vị đang được sản phẩm sử dụng; hãy tắt thay vì xóa.")
    db.session.delete(unit)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "unit_in_use", "Đơn vị vừa được sản phẩm sử dụng; không thể xóa.") from None
    return jsonify({"ok": True})
