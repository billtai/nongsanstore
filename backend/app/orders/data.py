"""orders: data; tách xử lý theo thao tác API."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal, ROUND_HALF_UP
from flask import g, jsonify, request
from sqlalchemy import func
from app import db
from app.auth import require_role
from app.helpers import integer_value, json_body, page_args, quantity_value, required_text
from app.errors import ApiError
from app.models import DiscountCode, Order, OrderBatchAllocation, OrderItem, OrderStatusHistory, ProduceBatch, Product
from app.orders import order_api


def order_data(order: Order, include_internal: bool = False, product_images: dict[int, str | None] | None = None):
    """Trả dữ liệu đơn; đầu vào: Order, cờ admin và ảnh sản phẩm đã lấy theo lô; đầu ra: JSON. Ví dụ: lịch sử đơn có ảnh sản phẩm, khách không nhận id nội bộ."""
    from app.orders.sepay import sepay_checkout
    from app.orders.sepay_bank import bank_transfer_data
    result = {
        "order_code"       : order.order_code,
        "recipient_name"   : order.recipient_name,
        "recipient_phone"  : order.recipient_phone,
        "delivery_address" : order.delivery_address,
        "status"           : order.status,
        "is_preorder"      : order.is_preorder,
        "payment_method"   : order.payment_method,
        "payment_status"   : order.payment_status,
        "pay_url"          : order.momo_pay_url if order.payment_method == "momo" and order.payment_status == "pending" else None,
        "sepay_checkout"   : sepay_checkout(order) if order.payment_status == "pending" else None,
        "bank_transfer"    : bank_transfer_data(order),
        "bank_transfer_reported_at" : order.bank_transfer_reported_at.isoformat() if order.bank_transfer_reported_at else None,
        "bank_payment_confirmed_at" : order.bank_payment_confirmed_at.isoformat() if order.bank_payment_confirmed_at else None,
        "bank_payment_confirmed_by" : order.bank_payment_confirmed_by if include_internal else None,
        "subtotal_vnd"     : order.subtotal_vnd,
        "discount_vnd"     : order.discount_vnd,
        "total_vnd"        : order.total_vnd,
        "discount_code"    : order.discount_code,
        "initial_subtotal_vnd" : order.initial_subtotal_vnd,
        "initial_discount_vnd" : order.initial_discount_vnd,
        "initial_total_vnd"    : order.initial_total_vnd,
        "proposed_subtotal_vnd" : order.proposed_subtotal_vnd,
        "proposed_discount_vnd" : order.proposed_discount_vnd,
        "proposed_total_vnd"    : order.proposed_total_vnd,
        "price_proposed_at"    : order.price_proposed_at.isoformat() if order.price_proposed_at else None,
        "price_approval_deadline" : (order.price_proposed_at + timedelta(days=1)).isoformat() if order.status == "awaiting_price_approval" and order.price_proposed_at else None,
        "price_approved_at"    : order.price_approved_at.isoformat() if order.price_approved_at else None,
        "created_at"       : order.created_at.isoformat(),
        "items"            : [{"product_id": item.product_id, "product_name": item.product_name, "image_url": product_images.get(item.product_id) if product_images else None, "unit": item.unit, "quantity": str(item.quantity), "unit_price_vnd": item.unit_price_vnd, "line_total_vnd": item.line_total_vnd, "is_preorder": item.is_preorder, "initial_unit_price_vnd": item.initial_unit_price_vnd, "initial_line_total_vnd": item.initial_line_total_vnd, "proposed_unit_price_vnd": item.proposed_unit_price_vnd, "proposed_line_total_vnd": item.proposed_line_total_vnd} for item in order.items],
        "history"          : [{"from_status": event.from_status, "to_status": event.to_status, "reason": event.reason, "created_at": event.created_at.isoformat()} for event in order.status_history],
    }
    if include_internal:
        result["id"]          = order.id
        result["customer_id"] = order.customer_id
    return result

