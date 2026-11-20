"""API quản trị nhà cung cấp và nhập kho, luôn yêu cầu quyền admin."""

from datetime import date
from decimal import Decimal, ROUND_HALF_UP
from secrets import token_hex

from flask import jsonify, request
from sqlalchemy import or_, func
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import joinedload, selectinload

from app import db
from app.admin import admin_api
from app.auth import require_role
from app.errors import ApiError
from app.helpers import integer_value, json_body, page_args, quantity_value, required_text
from app.models import Product, ProduceBatch, PurchaseOrder, PurchaseOrderItem, Supplier
from app.models.base import now_utc
from app.products.slug import slugify


def supplier_data(supplier: Supplier, order_count: int = 0) -> dict:
    """Đổi Supplier sang JSON; đầu vào bản ghi và số đơn, đầu ra thông tin liên hệ. Ví dụ order_count=2."""
    return {
        "id"           : supplier.id,
        "name"         : supplier.name,
        "contact_name" : supplier.contact_name,
        "phone"        : supplier.phone,
        "email"        : supplier.email,
        "address"      : supplier.address,
        "tax_code"     : supplier.tax_code,
        "notes"        : supplier.notes,
        "is_active"    : supplier.is_active,
        "created_at"   : supplier.created_at.isoformat(),
        "order_count"  : order_count,
    }


def purchase_data(purchase: PurchaseOrder, include_items: bool = False) -> dict:
    """Đổi đơn nhập sang JSON; include_items bật chi tiết. Ví dụ GET /purchases/1 trả items."""
    data = {
        "id"            : purchase.id,
        "supplier_id"   : purchase.supplier_id,
        "supplier_name" : purchase.supplier.name,
        "status"        : purchase.status,
        "expected_date" : purchase.expected_date.isoformat() if purchase.expected_date else None,
        "notes"         : purchase.notes,
        "total_vnd"     : purchase.total_vnd,
        "created_at"    : purchase.created_at.isoformat(),
        "ordered_at"    : purchase.ordered_at.isoformat() if purchase.ordered_at else None,
        "received_at"   : purchase.received_at.isoformat() if purchase.received_at else None,
    }
    if include_items:
        data["items"] = [{
            "id"             : item.id,
            "product_id"     : item.product_id,
            "product_name"   : item.product_name,
            "unit"           : item.unit,
            "quantity"       : str(item.quantity),
            "unit_cost_vnd"  : item.unit_cost_vnd,
            "line_total_vnd" : item.line_total_vnd,
            "batch_id"       : item.batch_id,
            "batch_code"     : item.batch.batch_code if item.batch else None,
        } for item in purchase.items]
    return data


def supplier_fields(data: dict, supplier: Supplier) -> None:
    """Kiểm tra và gán trường nhà cung cấp; đầu vào JSON/Supplier, đầu ra Supplier đã sửa. Ví dụ name='Nông trại A'."""
    for key, length in (("name", 180), ("contact_name", 120), ("phone", 30), ("email", 180), ("address", 255), ("tax_code", 30), ("notes", 2000)):
        if key in data:
            value = required_text(data, key, length) if key == "name" else data[key]
            if key != "name" and (not isinstance(value, str) or len(value.strip()) > length):
                raise ApiError(400, "invalid_input", f"{key} phải là chuỗi tối đa {length} ký tự.")
            setattr(supplier, key, value.strip())
    if "is_active" in data:
        if not isinstance(data["is_active"], bool):
            raise ApiError(400, "invalid_input", "is_active phải là boolean.")
        supplier.is_active = data["is_active"]


@admin_api.get("/suppliers")
@require_role("admin")
def list_suppliers():
    """Tìm/lọc nhà cung cấp ở DB; nhận q/active/page/limit, trả trang. Ví dụ ?q=trang&page=2."""
    page, limit = page_args()
    count       = db.session.query(func.count(PurchaseOrder.id)).filter(PurchaseOrder.supplier_id == Supplier.id).correlate(Supplier).scalar_subquery()
    query       = db.session.query(Supplier, count.label("order_count"))
    search      = request.args.get("q", "").strip()
    active      = request.args.get("active")
    if search:
        query = query.filter(or_(Supplier.name.ilike(f"%{search}%"), Supplier.phone.ilike(f"%{search}%"), Supplier.email.ilike(f"%{search}%")))
    if active is not None:
        if active not in ("true", "false"):
            raise ApiError(400, "invalid_input", "active phải là true hoặc false.")
        query = query.filter(Supplier.is_active.is_(active == "true"))
    result = query.order_by(Supplier.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    return jsonify({"items": [supplier_data(row, count) for row, count in result.items], "page": page, "limit": limit, "total": result.total})


@admin_api.post("/suppliers")
@require_role("admin")
def create_supplier():
    """Tạo nhà cung cấp; nhận name và thông tin liên hệ, trả bản ghi. Ví dụ {name:'Trang trại A'}."""
    data = json_body()
    if set(data) - {"name", "contact_name", "phone", "email", "address", "tax_code", "notes"}:
        raise ApiError(400, "invalid_input", "Trường nhà cung cấp không hợp lệ.")
    supplier = Supplier(name=required_text(data, "name", 180))
    supplier_fields(data, supplier)
    db.session.add(supplier)
    db.session.commit()
    return jsonify(supplier_data(supplier)), 201


@admin_api.patch("/suppliers/<int:item_id>")
@require_role("admin")
def update_supplier(item_id: int):
    """Sửa hoặc ẩn nhà cung cấp; nhận ID/JSON, trả bản ghi. Ví dụ {is_active:false}."""
    supplier = db.session.get(Supplier, item_id)
    if supplier is None:
        raise ApiError(404, "not_found", "Không tìm thấy nhà cung cấp.")
    data = json_body()
    if not data or set(data) - {"name", "contact_name", "phone", "email", "address", "tax_code", "notes", "is_active"}:
        raise ApiError(400, "invalid_input", "Trường nhà cung cấp không hợp lệ.")
    supplier_fields(data, supplier)
    db.session.commit()
    count = db.session.query(func.count(PurchaseOrder.id)).filter_by(supplier_id=item_id).scalar()
    return jsonify(supplier_data(supplier, count))


@admin_api.delete("/suppliers/<int:item_id>")
@require_role("admin")
def delete_supplier(item_id: int):
    """Xóa nhà cung cấp chưa có đơn; nhận ID, trả ok hoặc 409. Ví dụ DELETE /suppliers/3."""
    supplier = db.session.get(Supplier, item_id)
    if supplier is None:
        raise ApiError(404, "not_found", "Không tìm thấy nhà cung cấp.")
    if db.session.query(PurchaseOrder.id).filter_by(supplier_id=item_id).first():
        raise ApiError(409, "supplier_in_use", "Nhà cung cấp đã có đơn; hãy ẩn thay vì xóa.")
    db.session.delete(supplier)
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "supplier_in_use", "Nhà cung cấp vừa được sử dụng; không thể xóa.") from None
    return jsonify({"ok": True})


def validate_purchase(data: dict, purchase: PurchaseOrder) -> None:
    """Kiểm tra đơn và các dòng hàng; nhận JSON/đơn nháp, đầu ra đơn đã thay item. Ví dụ 2 kg cà rốt giá 10000/kg."""
    supplier_id = integer_value(data.get("supplier_id"), "supplier_id", 1)
    supplier    = db.session.get(Supplier, supplier_id)
    if supplier is None or not supplier.is_active:
        raise ApiError(400, "invalid_input", "Nhà cung cấp không tồn tại hoặc đã ẩn.")
    raw_items = data.get("items")
    if not isinstance(raw_items, list) or not 1 <= len(raw_items) <= 100:
        raise ApiError(400, "invalid_input", "Đơn nhập cần 1-100 dòng sản phẩm.")
    product_ids = []
    for raw in raw_items:
        if not isinstance(raw, dict) or set(raw) - {"product_id", "quantity", "unit_cost_vnd"}:
            raise ApiError(400, "invalid_input", "Dòng sản phẩm không hợp lệ.")
        product_ids.append(integer_value(raw.get("product_id"), "product_id", 1))
    if len(set(product_ids)) != len(product_ids):
        raise ApiError(400, "invalid_input", "Mỗi sản phẩm chỉ được xuất hiện một lần trong đơn.")
    products = {row.id: row for row in db.session.query(Product).filter(Product.id.in_(product_ids)).all()}
    if len(products) != len(product_ids):
        raise ApiError(400, "invalid_input", "Có sản phẩm không tồn tại.")
    expected_text = data.get("expected_date")
    if expected_text:
        try:
            purchase.expected_date = date.fromisoformat(expected_text)
        except (ValueError, TypeError):
            raise ApiError(400, "invalid_input", "expected_date phải có dạng YYYY-MM-DD.") from None
    else:
        purchase.expected_date = None
    notes = data.get("notes", "")
    if not isinstance(notes, str) or len(notes) > 2000:
        raise ApiError(400, "invalid_input", "notes phải là chuỗi tối đa 2000 ký tự.")
    purchase.supplier_id = supplier_id
    purchase.notes       = notes.strip()
    purchase.items.clear()
    total = 0
    for raw, product_id in zip(raw_items, product_ids):
        product  = products[product_id]
        quantity = quantity_value(raw.get("quantity"), product.unit)
        cost     = integer_value(raw.get("unit_cost_vnd"), "unit_cost_vnd")
        if cost > 1000000000:
            raise ApiError(400, "invalid_input", "Giá nhập tối đa 1 tỷ đồng mỗi đơn vị.")
        amount = int((quantity * Decimal(cost)).quantize(Decimal("1"), rounding=ROUND_HALF_UP))
        total += amount
        purchase.items.append(PurchaseOrderItem(product_id=product_id, product_name=product.name, unit=product.unit, quantity=quantity, unit_cost_vnd=cost, line_total_vnd=amount))
    purchase.total_vnd = total


@admin_api.get("/purchases")
@require_role("admin")
def list_purchases():
    """Tìm/lọc đơn nhập ở DB; nhận q/status/supplier_id/page/limit, trả trang. Ví dụ ?supplier_id=2&page=1."""
    page, limit   = page_args()
    query         = db.session.query(PurchaseOrder).options(joinedload(PurchaseOrder.supplier))
    search        = request.args.get("q", "").strip()
    status        = request.args.get("status")
    supplier_text = request.args.get("supplier_id")
    if supplier_text is not None:
        supplier_id = integer_value(supplier_text, "supplier_id", 1)
        query       = query.filter(PurchaseOrder.supplier_id == supplier_id)
    if search:
        query = query.join(Supplier).filter(Supplier.name.ilike(f"%{search}%"))
    if status:
        if status not in ("draft", "ordered", "received", "cancelled"):
            raise ApiError(400, "invalid_input", "Trạng thái đơn nhập không hợp lệ.")
        query = query.filter(PurchaseOrder.status == status)
    result = query.order_by(PurchaseOrder.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    return jsonify({"items": [purchase_data(row) for row in result.items], "page": page, "limit": limit, "total": result.total})


@admin_api.get("/purchases/<int:item_id>")
@require_role("admin")
def get_purchase(item_id: int):
    """Lấy đơn và dòng hàng; nhận ID, trả chi tiết gồm mã lô nếu đã nhận. Ví dụ GET /purchases/2."""
    purchase = db.session.query(PurchaseOrder).options(joinedload(PurchaseOrder.supplier), selectinload(PurchaseOrder.items).joinedload(PurchaseOrderItem.batch)).filter_by(id=item_id).one_or_none()
    if purchase is None:
        raise ApiError(404, "not_found", "Không tìm thấy đơn nhập.")
    return jsonify(purchase_data(purchase, True))


@admin_api.post("/purchases")
@require_role("admin")
def create_purchase():
    """Tạo đơn nháp; nhận nhà cung cấp/dòng hàng, trả đơn. Ví dụ {supplier_id:1,items:[...]}."""
    data = json_body()
    if set(data) - {"supplier_id", "expected_date", "notes", "items"}:
        raise ApiError(400, "invalid_input", "Trường đơn nhập không hợp lệ.")
    purchase = PurchaseOrder(status="draft")
    validate_purchase(data, purchase)
    db.session.add(purchase)
    db.session.commit()
    return get_purchase(purchase.id), 201


@admin_api.patch("/purchases/<int:item_id>")
@require_role("admin")
def update_purchase(item_id: int):
    """Sửa đơn còn nháp; nhận ID/JSON đầy đủ, trả chi tiết. Ví dụ đổi số lượng trước khi ghi nhận đặt."""
    purchase = db.session.get(PurchaseOrder, item_id)
    if purchase is None:
        raise ApiError(404, "not_found", "Không tìm thấy đơn nhập.")
    if purchase.status != "draft":
        raise ApiError(409, "invalid_status", "Chỉ sửa được đơn nháp.")
    data = json_body()
    if set(data) - {"supplier_id", "expected_date", "notes", "items"}:
        raise ApiError(400, "invalid_input", "Trường đơn nhập không hợp lệ.")
    validate_purchase(data, purchase)
    db.session.commit()
    return get_purchase(item_id)


@admin_api.post("/purchases/<int:item_id>/status")
@admin_api.patch("/purchases/<int:item_id>/status")
@require_role("admin")
def transition_purchase(item_id: int):
    """Đổi trạng thái đơn nhập; nhận status/batches khi nhận hàng, trả đơn. Ví dụ ordered -> received tạo lô."""
    data   = json_body()
    target = data.get("status")
    if target == "received":
        if set(data) != {"status", "batches"}:
            raise ApiError(400, "invalid_input", "Nhận hàng cần status và batches.")
        # Dùng cùng giao dịch nhận hàng để mọi lối gọi đều tạo lô và chặn nhận trùng.
        # Ví dụ PATCH status=received và POST /receive đều tạo một lô cho mỗi dòng.
        return receive_purchase(item_id)
    if set(data) != {"status"}:
        raise ApiError(400, "invalid_input", "Chỉ nhận trường status khi ghi nhận đặt hoặc hủy.")
    purchase = db.session.query(PurchaseOrder).filter_by(id=item_id).with_for_update().one_or_none()
    if purchase is None:
        raise ApiError(404, "not_found", "Không tìm thấy đơn nhập.")
    allowed = {"draft": {"ordered", "cancelled"}, "ordered": {"cancelled"}}
    if target not in allowed.get(purchase.status, set()):
        raise ApiError(409, "invalid_status", "Không thể chuyển trạng thái đơn nhập.")
    purchase.status = target
    if target == "ordered":
        purchase.ordered_at = now_utc()
    db.session.commit()
    return get_purchase(item_id)


@admin_api.post("/purchases/<int:item_id>/receive")
@require_role("admin")
def receive_purchase(item_id: int):
    """Nhận hàng một lần và tạo lô cho mỗi dòng; nhận batches[{item_id,vùng,nguồn,ngày}], trả đơn có mã lô."""
    # Khóa hàng đơn trong giao dịch để hai người không thể cùng nhận một đơn.
    # Ví dụ hai request đồng thời cho đơn #3: request thứ hai thấy received và nhận lỗi 409.
    purchase = db.session.query(PurchaseOrder).filter_by(id=item_id).with_for_update().one_or_none()
    if purchase is None:
        raise ApiError(404, "not_found", "Không tìm thấy đơn nhập.")
    if purchase.status != "ordered":
        raise ApiError(409, "invalid_status", "Chỉ nhận hàng cho đơn đã ghi nhận đặt.")
    data       = json_body()
    raw_batches = data.get("batches")
    items      = db.session.query(PurchaseOrderItem).filter_by(purchase_id=item_id).order_by(PurchaseOrderItem.id).all()
    if not isinstance(raw_batches, list) or len(raw_batches) != len(items):
        raise ApiError(400, "invalid_input", "Cần thông tin lô cho mọi sản phẩm trong đơn.")
    batches_by_item = {}
    for raw in raw_batches:
        if not isinstance(raw, dict) or set(raw) != {"item_id", "growing_region", "origin", "harvest_date"}:
            raise ApiError(400, "invalid_input", "Thông tin lô không hợp lệ.")
        key = integer_value(raw.get("item_id"), "item_id", 1)
        if key in batches_by_item:
            raise ApiError(400, "invalid_input", "Trùng dòng sản phẩm nhận hàng.")
        batches_by_item[key] = raw
    if set(batches_by_item) != {item.id for item in items}:
        raise ApiError(400, "invalid_input", "Dòng sản phẩm nhận hàng không khớp đơn.")
    for item in items:
        raw          = batches_by_item[item.id]
        region       = required_text(raw, "growing_region", 180)
        origin       = required_text(raw, "origin", 255)
        harvest_text = required_text(raw, "harvest_date", 10)
        try:
            harvest_date = date.fromisoformat(harvest_text)
        except ValueError:
            raise ApiError(400, "invalid_input", "harvest_date phải có dạng YYYY-MM-DD.") from None
        batch_code = f"{slugify(item.product_name)[:54].strip('-').upper()}-{harvest_date:%Y%m%d}-{token_hex(8).upper()}"
        batch      = ProduceBatch(product_id=item.product_id, batch_code=batch_code, growing_region=region, origin=origin, harvest_date=harvest_date, remaining_quantity=item.quantity)
        db.session.add(batch)
        db.session.flush()
        item.batch_id = batch.id
    purchase.status      = "received"
    purchase.received_at = now_utc()
    try:
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        raise ApiError(409, "batch_exists", "Không thể tạo mã lô duy nhất; hãy thử lại.") from None
    return get_purchase(item_id)
