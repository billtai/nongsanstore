"""Kết nối thanh toán ví MoMo trên môi trường Test và xác nhận IPN."""

import hashlib
import hmac
import json
import os
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from flask import g, jsonify

from app import db
from app.auth import require_role
from app.errors import ApiError
from app.helpers import json_body
from app.models import Order
from app.orders import order_api
from app.orders.data import order_data


MOMO_TEST_CREATE_URL = "https://test-payment.momo.vn/v2/gateway/api/create"
IPN_FIELDS           = ("accessKey", "amount", "extraData", "message", "orderId", "orderInfo", "orderType", "partnerCode", "payType", "requestId", "responseTime", "resultCode", "transId")


def momo_settings():
    """Đọc cấu hình Test từ môi trường; đầu vào biến MOMO_*, đầu ra dict hoặc None.

    Ví dụ: thiếu MOMO_SECRET_KEY thì phương thức MoMo bị ẩn khỏi trang thanh toán.
    """
    names = ("MOMO_PARTNER_CODE", "MOMO_ACCESS_KEY", "MOMO_SECRET_KEY", "MOMO_IPN_URL", "MOMO_REDIRECT_URL")
    values = {name: os.getenv(name, "").strip() for name in names}
    if not all(values.values()) or not values["MOMO_IPN_URL"].startswith("https://") or not values["MOMO_REDIRECT_URL"].startswith("https://") or "{order_id}" not in values["MOMO_REDIRECT_URL"]:
        return None
    return values


def momo_signature(fields: dict, secret: str) -> str:
    """Ký chuỗi key=value bằng HMAC SHA256; đầu vào các trường đúng thứ tự, đầu ra hex.

    Ví dụ: {"a": 1, "b": 2} được ký từ chuỗi a=1&b=2.
    """
    raw = "&".join(f"{key}={value}" for key, value in fields.items())
    return hmac.new(secret.encode(), raw.encode(), hashlib.sha256).hexdigest()


def initiate_momo(order: Order) -> str:
    """Tạo liên kết trả tiền Test; đầu vào đơn MoMo, đầu ra payUrl hoặc lỗi 502.

    Ví dụ: đơn #12 có tổng 100000 VND nhận URL tại test-payment.momo.vn.
    """
    settings = momo_settings()
    if settings is None:
        raise ApiError(503, "momo_unavailable", "MoMo Test chưa được cấu hình đầy đủ.")
    if order.payment_method != "momo" or order.total_vnd < 1000 or order.total_vnd > 50000000:
        raise ApiError(400, "invalid_payment", "Số tiền MoMo phải từ 1.000 đến 50.000.000 VND.")
    if order.momo_pay_url:
        return order.momo_pay_url

    fields = {
        "accessKey"   : settings["MOMO_ACCESS_KEY"],
        "amount"      : order.total_vnd,
        "extraData"   : "",
        "ipnUrl"      : settings["MOMO_IPN_URL"],
        "orderId"     : order.momo_order_id,
        "orderInfo"   : f"Thanh toan don hang {order.order_code}",
        "partnerCode" : settings["MOMO_PARTNER_CODE"],
        "redirectUrl" : settings["MOMO_REDIRECT_URL"].format(order_id=order.order_code),
        "requestId"   : order.momo_request_id,
        "requestType": "captureWallet",
    }
    body = {
        "partnerCode" : fields["partnerCode"],
        "requestId"   : fields["requestId"],
        "amount"      : fields["amount"],
        "orderId"     : fields["orderId"],
        "orderInfo"   : fields["orderInfo"],
        "redirectUrl" : fields["redirectUrl"],
        "ipnUrl"      : fields["ipnUrl"],
        "requestType": fields["requestType"],
        "extraData"   : "",
        "lang"        : "vi",
        "signature"   : momo_signature(fields, settings["MOMO_SECRET_KEY"]),
    }
    request = Request(MOMO_TEST_CREATE_URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json; charset=UTF-8"}, method="POST")
    try:
        with urlopen(request, timeout=30) as response:
            result = json.load(response)
    except (HTTPError, URLError, TimeoutError, ValueError):
        raise ApiError(502, "momo_unavailable", "Không thể kết nối MoMo Test. Vui lòng thử lại.") from None
    if not isinstance(result, dict) or result.get("resultCode") != 0 or not isinstance(result.get("payUrl"), str):
        raise ApiError(502, "momo_rejected", "MoMo Test chưa tạo được liên kết thanh toán.")
    if result.get("partnerCode") != fields["partnerCode"] or result.get("orderId") != fields["orderId"] or result.get("requestId") != fields["requestId"] or result.get("amount") != order.total_vnd:
        raise ApiError(502, "momo_invalid_response", "Phản hồi MoMo không khớp đơn hàng.")
    response_fields = {
        "accessKey"   : settings["MOMO_ACCESS_KEY"],
        "amount"      : result["amount"],
        "message"     : result.get("message", ""),
        "orderId"     : result["orderId"],
        "partnerCode" : result["partnerCode"],
        "payUrl"      : result["payUrl"],
        "requestId"   : result["requestId"],
        "responseTime": result.get("responseTime", ""),
        "resultCode"  : result["resultCode"],
    }
    if not hmac.compare_digest(momo_signature(response_fields, settings["MOMO_SECRET_KEY"]), str(result.get("signature", ""))):
        raise ApiError(502, "momo_invalid_response", "Chữ ký phản hồi MoMo không hợp lệ.")
    if not result["payUrl"].startswith("https://test-payment.momo.vn/"):
        raise ApiError(502, "momo_invalid_response", "Đường dẫn thanh toán MoMo không hợp lệ.")
    order.momo_pay_url = result["payUrl"]
    db.session.commit()
    db.session.refresh(order)
    return order.momo_pay_url


@order_api.get("/payment-methods")
def payment_methods():
    """Liệt kê phương thức đang bật; đầu vào không có, đầu ra COD, MoMo và SePay nếu đủ cấu hình."""
    from app.orders.sepay import sepay_settings
    from app.orders.sepay_bank import bank_settings
    return jsonify({"items": ["cod", *(["momo"] if momo_settings() else []), *(["sepay_bank"] if bank_settings() else [])]})


@order_api.post("/momo/ipn")
def momo_ipn():
    """Nhận IPN đã ký từ MoMo; đầu vào JSON MoMo, đầu ra HTTP 204.

    Ví dụ: resultCode=0 và amount khớp đơn sẽ đổi payment_status thành paid.
    """
    settings = momo_settings()
    if settings is None:
        raise ApiError(503, "momo_unavailable", "MoMo Test chưa được cấu hình.")
    data = json_body()
    if any(key not in data or data[key] is None for key in IPN_FIELDS if key != "accessKey") or not isinstance(data.get("signature"), str) or type(data.get("resultCode")) is not int:
        raise ApiError(400, "invalid_ipn", "Thiếu trường xác thực MoMo.")
    fields = {key: settings["MOMO_ACCESS_KEY"] if key == "accessKey" else data[key] for key in IPN_FIELDS}
    if not hmac.compare_digest(momo_signature(fields, settings["MOMO_SECRET_KEY"]), data["signature"]):
        raise ApiError(400, "invalid_ipn", "Chữ ký MoMo không hợp lệ.")
    order = db.session.query(Order).filter_by(momo_order_id=data["orderId"]).with_for_update().first()
    if order is None or order.payment_method != "momo" or data["partnerCode"] != settings["MOMO_PARTNER_CODE"] or data["requestId"] != order.momo_request_id or type(data["amount"]) is not int or data["amount"] != order.total_vnd:
        db.session.rollback()
        raise ApiError(400, "invalid_ipn", "Giao dịch MoMo không khớp đơn hàng.")
    if order.payment_status != "paid":
        order.payment_status = "paid" if data["resultCode"] == 0 else "failed"
        if data["resultCode"] == 0:
            order.momo_trans_id = str(data["transId"])
        db.session.commit()
    return "", 204


@order_api.get("/<order_code>/momo/status")
@require_role("customer", "admin")
def momo_status(order_code: str):
    """Đọc trạng thái thanh toán đã xác nhận qua IPN; đầu vào mã đơn, đầu ra trạng thái.

    Ví dụ: GET /orders/12/momo/status trả paid sau khi MoMo gửi IPN thành công.
    """
    order = db.session.query(Order).filter_by(order_code=order_code, customer_id=g.user.id).first()
    if order is None or order.payment_method != "momo":
        raise ApiError(404, "not_found", "Không tìm thấy đơn MoMo.")
    return jsonify({"order_code": order.order_code, "payment_status": order.payment_status, "order": order_data(order)})


@order_api.post("/<order_code>/momo/retry")
@require_role("customer", "admin")
def retry_momo(order_code: str):
    """Lấy lại liên kết Test cho đơn đang chờ; đầu vào mã đơn, đầu ra đơn và pay_url.

    Ví dụ: POST /orders/12/momo/retry dùng lại mã giao dịch của đơn #12.
    """
    order = db.session.query(Order).filter_by(order_code=order_code, customer_id=g.user.id).first()
    if order is None or order.payment_method != "momo":
        raise ApiError(404, "not_found", "Không tìm thấy đơn MoMo.")
    if order.status == "cancelled" or order.payment_status != "pending":
        raise ApiError(409, "payment_closed", "Đơn không còn chờ thanh toán MoMo.")
    initiate_momo(order)
    return jsonify(order_data(order))
