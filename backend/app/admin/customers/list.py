"""Quản trị customers: thao tác list."""

from flask import jsonify, request
from sqlalchemy import func
from app import db
from app.admin import admin_api
from app.auth import require_role
from app.helpers import page_args
from app.models import Customer, Order


@admin_api.get("/customers")
@require_role("admin")
def admin_customers():
    """Tìm khách theo q, phân trang; trả thông tin và số đơn/tổng mua."""
    page, limit = page_args()
    query       = db.session.query(Customer).filter_by(role="customer")
    search      = request.args.get("q", "").strip()
    if search:
        query = query.filter((Customer.name.ilike(f"%{search}%")) | (Customer.email.ilike(f"%{search}%")) | (Customer.phone.ilike(f"%{search}%")))
    result = query.order_by(Customer.id.desc()).paginate(page=page, per_page=limit, error_out=False)
    ids    = [customer.id for customer in result.items]
    stats  = {row[0]: (row[1], row[2]) for row in db.session.query(Order.customer_id, func.count(Order.id), func.coalesce(func.sum(Order.total_vnd), 0)).filter(Order.customer_id.in_(ids), Order.status == "completed").group_by(Order.customer_id).all()} if ids else {}
    return jsonify({"items": [{"id": customer.id, "name": customer.name, "email": customer.email, "phone": customer.phone, "created_at": customer.created_at.isoformat(), "completed_orders": stats.get(customer.id, (0, 0))[0], "completed_total_vnd": stats.get(customer.id, (0, 0))[1]} for customer in result.items], "page": page, "limit": limit, "total": result.total})
