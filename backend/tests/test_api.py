"""Kiểm tra luồng MVP trên SQLite trong bộ nhớ, không đụng PostgreSQL thật."""

import os
import hashlib
import tempfile
import unittest
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from io import BytesIO
from pathlib import Path
from zoneinfo import ZoneInfo

from PIL import Image

os.environ["DATABASE_URL"]    = "sqlite:///:memory:"
os.environ["FRONTEND_ORIGIN"] = "http://localhost:3000"
os.environ["SECRET_KEY"]      = "test-only-secret-key-not-for-production"

from app import create_app, db  # noqa: E402
from app.models import Customer, DiscountCode, Order, ProduceBatch, Product, ProductUnit  # noqa: E402
from werkzeug.security import generate_password_hash  # noqa: E402


class ApiFlowTest(unittest.TestCase):
    """Tạo dữ liệu tạm, chạy đặt đơn và kiểm tra snapshot cùng tồn kho."""

    def setUp(self):
        """Tạo app/bảng trong RAM; đầu ra client và một sản phẩm có tồn 5 kg."""
        self.app    = create_app()
        self.assets = tempfile.TemporaryDirectory()
        self.app.config["ASSETS_DIR"] = Path(self.assets.name)
        self.client = self.app.test_client()
        self.ctx    = self.app.app_context()
        self.ctx.push()
        db.create_all()
        admin = Customer(name="Admin", email="admin@example.test", phone="0900000000", password_hash=generate_password_hash("password123"), role="admin")
        product = Product(name="Cà rốt", unit="kg", price_vnd=20000, description="Mẫu")
        db.session.add_all([admin, product])
        db.session.flush()
        db.session.add(ProduceBatch(product_id=product.id, batch_code="TEST-1", growing_region="Lâm Đồng", origin="Việt Nam", harvest_date=date(2026, 11, 10), remaining_quantity=Decimal("5")))
        db.session.add(DiscountCode(code="GIAM10", kind="percent", value=10, min_subtotal_vnd=10000, used_count=0, is_active=True))
        db.session.commit()

    def tearDown(self):
        """Xóa database RAM và ngữ cảnh; không có đầu vào/đầu ra."""
        db.session.remove()
        db.drop_all()
        self.ctx.pop()
        self.assets.cleanup()

    def test_login_accepts_existing_scrypt_hash(self):
        """Đăng nhập dữ liệu hash scrypt cũ; đầu vào mật khẩu đúng/sai, đầu ra 200/401. Ví dụ: tài khoản đã tạo ở Werkzeug mới vẫn truy cập được."""
        admin    = Customer.query.filter_by(email="admin@example.test").one()
        salt     = "legacy-salt"
        digest   = hashlib.scrypt(b"password123", salt=salt.encode(), n=32768, r=8, p=1, maxmem=64 * 1024 * 1024).hex()
        admin.password_hash = f"scrypt:32768:8:1${salt}${digest}"
        db.session.commit()
        valid    = self.client.post("/api/v1/auth/login", json={"email": admin.email, "password": "password123"})
        invalid  = self.client.post("/api/v1/auth/login", json={"email": admin.email, "password": "wrong-password"})
        self.assertEqual(valid.status_code, 200)
        self.assertEqual(invalid.status_code, 401)

    def token(self, email):
        """Đăng nhập tài khoản mẫu; đầu vào email, đầu ra Authorization header."""
        response = self.client.post("/api/v1/auth/login", json={"email": email, "password": "password123"})
        return {"Authorization": f"Bearer {response.json['access_token']}"}

    def test_order_snapshot_stock_and_admin_permissions(self):
        """Đặt đơn 2 kg, khóa quyền admin, giữ snapshot và hoàn tồn khi hủy."""
        registered = self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "lan@example.test", "phone": "0911111111", "password": "password123"})
        self.assertEqual(registered.status_code, 201)
        customer_headers = self.token("lan@example.test")
        admin_headers    = self.token("admin@example.test")
        self.assertEqual(self.client.get("/api/v1/admin/orders", headers=customer_headers).status_code, 403)
        body = {"recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod", "discount_code": "GIAM10", "items": [{"product_id": 1, "quantity": "2"}]}
        response = self.client.post("/api/v1/orders", json=body, headers=customer_headers)
        self.assertEqual(response.status_code, 201)
        self.assertEqual(response.json["total_vnd"], 36000)
        self.assertEqual(ProduceBatch.query.first().remaining_quantity, Decimal("3"))
        Product.query.first().image_url = "/assets/products/carrot/main.png"
        db.session.commit()
        history = self.client.get("/api/v1/orders?kind=regular", headers=customer_headers)
        self.assertEqual(history.json["items"][0]["items"][0]["image_url"], "/assets/products/carrot/main.png")
        Product.query.first().price_vnd = 30000
        db.session.commit()
        self.assertNotIn("id", response.json)
        self.assertRegex(response.json["order_code"], r"^VN-[A-F0-9]{24}$")
        detail = self.client.get(f"/api/v1/orders/{response.json['order_code']}", headers=customer_headers)
        self.assertEqual(detail.json["items"][0]["unit_price_vnd"], 20000)
        self.assertEqual(self.client.get("/api/v1/orders/1", headers=customer_headers).status_code, 404)
        self.client.post("/api/v1/auth/register", json={"name": "Mai", "email": "mai@example.test", "phone": "0922222222", "password": "password123"})
        other_headers = self.token("mai@example.test")
        self.assertEqual(self.client.get(f"/api/v1/orders/{response.json['order_code']}", headers=other_headers).status_code, 404)
        admin_order_id = self.client.get("/api/v1/admin/orders", headers=admin_headers).json["items"][0]["id"]
        cancelled = self.client.post(f"/api/v1/admin/orders/{admin_order_id}/transitions", json={"to_status": "cancelled"}, headers=admin_headers)
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(ProduceBatch.query.first().remaining_quantity, Decimal("5"))

    def test_preorder_waits_for_customer_price_approval(self):
        """Đặt trước khi tồn 0; đầu vào giá mới khi hàng về, đầu ra so sánh giá và giữ tồn ngay lúc gửi giá. Ví dụ: 2 kg tăng từ 20.000 lên 25.000đ/kg."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "preorder@example.test", "phone": "0911111111", "password": "password123"})
        customer_headers = self.token("preorder@example.test")
        admin_headers    = self.token("admin@example.test")
        batch            = ProduceBatch.query.first()
        batch.remaining_quantity = Decimal("0")
        db.session.commit()

        items = [{"product_id": 1, "quantity": "2", "preorder": True}]
        quote = self.client.post("/api/v1/orders/quote", json={"items": items}, headers=customer_headers)
        self.assertEqual(quote.status_code, 200)
        self.assertTrue(quote.json["is_preorder"])
        body = {"quote_id": quote.json["quote_id"], "recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod"}
        created = self.client.post("/api/v1/orders/confirm", json=body, headers=customer_headers)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(created.json["status"], "preordered")
        self.assertTrue(created.json["is_preorder"])
        self.assertTrue(created.json["items"][0]["is_preorder"])
        self.assertEqual(self.client.get("/api/v1/orders?kind=preorder", headers=customer_headers).json["total"], 1)
        self.assertEqual(self.client.get("/api/v1/orders?kind=regular", headers=customer_headers).json["total"], 0)
        self.assertEqual(self.client.get("/api/v1/admin/orders?kind=preorder", headers=admin_headers).json["total"], 1)
        self.assertEqual(self.client.get("/api/v1/admin/orders?kind=regular", headers=admin_headers).json["total"], 0)
        self.assertEqual(batch.remaining_quantity, Decimal("0"))
        admin_order_id = self.client.get("/api/v1/admin/orders", headers=admin_headers).json["items"][0]["id"]
        endpoint       = f"/api/v1/admin/orders/{admin_order_id}/price-proposal"
        self.assertEqual(self.client.post(endpoint, headers=admin_headers).status_code, 409)
        batch.remaining_quantity = Decimal("3")
        Product.query.first().price_vnd = 25000
        db.session.commit()
        proposed = self.client.post(endpoint, headers=admin_headers)
        self.assertEqual(proposed.status_code, 200)
        self.assertEqual(proposed.json["status"], "awaiting_price_approval")
        self.assertEqual(proposed.json["initial_total_vnd"], 40000)
        self.assertEqual(proposed.json["proposed_total_vnd"], 50000)
        self.assertEqual(proposed.json["items"][0]["initial_unit_price_vnd"], 20000)
        self.assertEqual(proposed.json["items"][0]["proposed_unit_price_vnd"], 25000)
        self.assertEqual(batch.remaining_quantity, Decimal("1"))
        self.assertEqual(self.client.post(f"/api/v1/orders/{created.json['order_code']}/price-approval", headers=admin_headers).status_code, 403)
        confirmed = self.client.post(f"/api/v1/orders/{created.json['order_code']}/price-approval", headers=customer_headers)
        self.assertEqual(confirmed.status_code, 200)
        self.assertEqual(confirmed.json["status"], "confirmed")
        self.assertEqual(confirmed.json["total_vnd"], 50000)
        self.assertEqual(confirmed.json["initial_total_vnd"], 40000)
        self.assertTrue(confirmed.json["is_preorder"])
        self.assertEqual(self.client.get("/api/v1/orders?kind=preorder", headers=customer_headers).json["total"], 1)
        self.assertEqual(self.client.get("/api/v1/admin/orders?kind=preorder", headers=admin_headers).json["total"], 1)
        self.assertEqual(batch.remaining_quantity, Decimal("1"))

    def test_preorder_price_rejection_keeps_stock_and_is_private(self):
        """Từ chối giá hoàn hàng đã giữ; đầu vào đơn đã gửi giá, đầu ra cancelled và tồn mở lại. Ví dụ: khách khác không thể chấp thuận hộ."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "reject@example.test", "phone": "0911111111", "password": "password123"})
        self.client.post("/api/v1/auth/register", json={"name": "Mai", "email": "other@example.test", "phone": "0922222222", "password": "password123"})
        customer_headers = self.token("reject@example.test")
        other_headers    = self.token("other@example.test")
        admin_headers    = self.token("admin@example.test")
        batch            = ProduceBatch.query.first()
        batch.remaining_quantity = Decimal("0")
        db.session.commit()
        quote   = self.client.post("/api/v1/orders/quote", json={"items": [{"product_id": 1, "quantity": "2", "preorder": True}]}, headers=customer_headers)
        created = self.client.post("/api/v1/orders/confirm", json={"quote_id": quote.json["quote_id"], "recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod"}, headers=customer_headers)
        order_id = Order.query.filter_by(order_code=created.json["order_code"]).one().id
        batch.remaining_quantity = Decimal("3")
        db.session.commit()
        self.assertEqual(self.client.post(f"/api/v1/admin/orders/{order_id}/price-proposal", headers=admin_headers).status_code, 200)
        path = f"/api/v1/orders/{created.json['order_code']}"
        self.assertEqual(self.client.post(f"{path}/price-approval", headers=other_headers).status_code, 404)
        self.assertEqual(batch.remaining_quantity, Decimal("1"))
        rejected = self.client.post(f"{path}/price-rejection", headers=customer_headers)
        self.assertEqual(rejected.status_code, 200)
        self.assertEqual(rejected.json["status"], "cancelled")
        self.assertEqual(batch.remaining_quantity, Decimal("3"))
        self.assertEqual(self.client.post(f"{path}/price-approval", headers=customer_headers).status_code, 409)

    def test_new_stock_reserves_preorder_then_expires_after_one_day(self):
        """Nhập đúng 1 kg cho đơn đặt trước 1 kg; đầu ra: tồn công khai bằng 0, quá 24 giờ trả lại 1 kg. Ví dụ: khách không xác nhận trong ngày."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "reserve@example.test", "phone": "0911111111", "password": "password123"})
        customer_headers = self.token("reserve@example.test")
        admin_headers    = self.token("admin@example.test")
        batch            = ProduceBatch.query.first()
        batch.remaining_quantity = Decimal("0")
        db.session.commit()
        items   = [{"product_id": 1, "quantity": "1", "preorder": True}]
        quote   = self.client.post("/api/v1/orders/quote", json={"items": items}, headers=customer_headers)
        created = self.client.post("/api/v1/orders/confirm", json={"quote_id": quote.json["quote_id"], "recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod"}, headers=customer_headers)
        arrival = self.client.post("/api/v1/admin/batches", json={"product_id": 1, "growing_region": "Lâm Đồng", "origin": "Việt Nam", "harvest_date": "2026-11-18", "quantity": "1"}, headers=admin_headers)
        self.assertEqual(arrival.status_code, 201)
        self.assertEqual(self.client.get("/api/v1/products/1").json["stock"], "0.000")
        order = Order.query.filter_by(order_code=created.json["order_code"]).one()
        self.assertEqual(order.status, "awaiting_price_approval")
        order.price_proposed_at = datetime.now(timezone.utc) - timedelta(days=1, minutes=1)
        db.session.commit()
        self.assertEqual(self.client.get("/api/v1/products/1").json["stock"], "1.000")
        self.assertEqual(order.status, "cancelled")
        self.assertEqual(self.client.post(f"/api/v1/orders/{order.order_code}/price-approval", headers=customer_headers).status_code, 409)

    def test_partial_arrival_is_reserved_before_regular_sale(self):
        """Nhập thiếu hàng vẫn giữ cho đơn cũ; đầu vào: đặt trước 2 kg rồi nhập 1 kg, đầu ra: tồn bán lẻ 0 và chờ thêm 1 kg. Ví dụ: hai lần nhập mỗi lần 1 kg."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "partial@example.test", "phone": "0911111111", "password": "password123"})
        customer_headers = self.token("partial@example.test")
        admin_headers    = self.token("admin@example.test")
        ProduceBatch.query.first().remaining_quantity = Decimal("0")
        db.session.commit()
        quote   = self.client.post("/api/v1/orders/quote", json={"items": [{"product_id": 1, "quantity": "2", "preorder": True}]}, headers=customer_headers)
        created = self.client.post("/api/v1/orders/confirm", json={"quote_id": quote.json["quote_id"], "recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod"}, headers=customer_headers)
        batch_body = {"product_id": 1, "growing_region": "Lâm Đồng", "origin": "Việt Nam", "harvest_date": "2026-11-18", "quantity": "1"}
        self.assertEqual(self.client.post("/api/v1/admin/batches", json=batch_body, headers=admin_headers).status_code, 201)
        self.assertEqual(self.client.get("/api/v1/products/1").json["stock"], "0.000")
        self.assertEqual(Order.query.filter_by(order_code=created.json["order_code"]).one().status, "preordered")
        self.assertEqual(self.client.post("/api/v1/admin/batches", json=batch_body, headers=admin_headers).status_code, 201)
        self.assertEqual(self.client.get("/api/v1/products/1").json["stock"], "0.000")
        self.assertEqual(Order.query.filter_by(order_code=created.json["order_code"]).one().status, "awaiting_price_approval")

    def test_customer_cancel_preorder_reopens_reserved_stock(self):
        """Khách hủy đơn đang chờ hàng; đầu vào: đơn giữ một phần 1 kg, đầu ra: tồn sản phẩm hiện lại 1 kg. Ví dụ: hủy trước khi đủ 2 kg."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "cancel-preorder@example.test", "phone": "0911111111", "password": "password123"})
        customer_headers = self.token("cancel-preorder@example.test")
        admin_headers    = self.token("admin@example.test")
        ProduceBatch.query.first().remaining_quantity = Decimal("0")
        db.session.commit()
        quote   = self.client.post("/api/v1/orders/quote", json={"items": [{"product_id": 1, "quantity": "2", "preorder": True}]}, headers=customer_headers)
        created = self.client.post("/api/v1/orders/confirm", json={"quote_id": quote.json["quote_id"], "recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod"}, headers=customer_headers)
        batch   = self.client.post("/api/v1/admin/batches", json={"product_id": 1, "growing_region": "Lâm Đồng", "origin": "Việt Nam", "harvest_date": "2026-11-18", "quantity": "1"}, headers=admin_headers)
        self.assertEqual(batch.status_code, 201)
        self.assertEqual(self.client.get("/api/v1/products/1").json["stock"], "0.000")
        cancelled = self.client.post(f"/api/v1/orders/{created.json['order_code']}/cancel", headers=customer_headers)
        self.assertEqual(cancelled.status_code, 200)
        self.assertEqual(cancelled.json["status"], "cancelled")
        self.assertEqual(self.client.get("/api/v1/products/1").json["stock"], "1.000")
        self.assertEqual(self.client.post(f"/api/v1/orders/{created.json['order_code']}/cancel", headers=customer_headers).status_code, 409)

    def test_mixed_stock_and_preorder_must_be_separate_orders(self):
        """Chặn giỏ trộn hai loại ở API; đầu vào một dòng có sẵn và một dòng đặt trước, đầu ra lỗi 400. Ví dụ: không thể tạo đơn khiến hàng có sẵn phải chờ hàng về."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "split@example.test", "phone": "0911111111", "password": "password123"})
        headers = self.token("split@example.test")
        product = Product(name="Bí xanh", unit="kg", price_vnd=15000, description="Mẫu")
        db.session.add(product)
        db.session.commit()
        items = [{"product_id": 1, "quantity": "1", "preorder": False}, {"product_id": product.id, "quantity": "1", "preorder": True}]
        quote = self.client.post("/api/v1/orders/quote", json={"items": items}, headers=headers)
        direct = self.client.post("/api/v1/orders", json={"items": items, "recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod"}, headers=headers)
        self.assertEqual(quote.status_code, 400)
        self.assertEqual(quote.json["error"]["code"], "mixed_order")
        self.assertEqual(direct.status_code, 400)

    def test_order_search_by_product_and_local_date(self):
        """Lọc lịch sử theo sản phẩm và ngày Việt Nam; đầu vào q/date, đầu ra đúng đơn của khách và admin. Ví dụ: 17:30 UTC ngày 17 thuộc ngày 18 tại Việt Nam."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "search@example.test", "phone": "0911111111", "password": "password123"})
        customer_headers = self.token("search@example.test")
        admin_headers    = self.token("admin@example.test")
        body             = {"recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod", "items": [{"product_id": 1, "quantity": "1"}]}
        created          = self.client.post("/api/v1/orders", json=body, headers=customer_headers)
        self.assertEqual(created.status_code, 201)
        order            = Order.query.filter_by(order_code=created.json["order_code"]).one()
        order.created_at = datetime(2026, 11, 17, 17, 30, tzinfo=timezone.utc)
        db.session.commit()
        self.assertEqual(self.client.get("/api/v1/orders?q=Cà%20rốt&date=2026-11-18", headers=customer_headers).json["total"], 1)
        self.assertEqual(self.client.get("/api/v1/orders?q=Bí%20xanh&date=2026-11-18", headers=customer_headers).json["total"], 0)
        self.assertEqual(self.client.get("/api/v1/orders?date=2026-11-17", headers=customer_headers).json["total"], 0)
        self.assertEqual(self.client.get("/api/v1/admin/orders?q=Cà%20rốt&date=2026-11-18", headers=admin_headers).json["total"], 1)
        self.assertEqual(self.client.get("/api/v1/orders?date=18-11-2026", headers=customer_headers).status_code, 400)

    def test_admin_overview_counts_and_permissions(self):
        """Thống kê từ database, chỉ admin xem; đầu vào đơn ở hai ngày Việt Nam, đầu ra bộ đếm và 12 tháng. Ví dụ: đơn hôm nay và hôm qua đều thuộc tháng này."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "stats@example.test", "phone": "0911111111", "password": "password123"})
        customer_headers = self.token("stats@example.test")
        admin_headers    = self.token("admin@example.test")
        endpoint         = "/api/v1/admin/overview"
        self.assertEqual(self.client.get(endpoint).status_code, 401)
        self.assertEqual(self.client.get(endpoint, headers=customer_headers).status_code, 403)
        body = {"recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod", "items": [{"product_id": 1, "quantity": "1"}]}
        local_now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        local_midday = local_now.replace(hour=12, minute=0, second=0, microsecond=0)
        for offset in (0, 1):
            created = self.client.post("/api/v1/orders", json=body, headers=customer_headers)
            self.assertEqual(created.status_code, 201)
            order = Order.query.filter_by(order_code=created.json["order_code"]).one()
            order.created_at = (local_midday - timedelta(days=offset)).astimezone(timezone.utc)
        old_batch = ProduceBatch.query.filter_by(batch_code="TEST-1").one()
        old_batch.created_at = datetime.now(timezone.utc) - timedelta(days=4)
        old_batch.is_visible = False
        db.session.commit()
        result = self.client.get(endpoint, headers=admin_headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["counts"]["today"], 1)
        self.assertEqual(result.json["counts"]["previous_day"], 1)
        self.assertEqual(len(result.json["monthly"]), 12)
        self.assertEqual(sum(point["orders"] for point in result.json["monthly"]), 2)
        self.assertEqual(result.json["aging_batches"]["total"], 1)
        self.assertEqual(result.json["aging_batches"]["items"][0]["batch_code"], "TEST-1")
        self.assertEqual(result.json["aging_batches"]["items"][0]["remaining_quantity"], "3.000")
        self.assertEqual(self.client.get(f"{endpoint}?aging_page=2", headers=admin_headers).json["aging_batches"]["items"], [])

    def test_admin_daily_revenue_uses_creation_day_and_completed_orders(self):
        """Báo cáo nhóm ngày tạo theo giờ Việt Nam; đầu vào đơn completed/pending, đầu ra số đơn và tổng tiền. Ví dụ: 17:30 UTC ngày 17 thuộc ngày 18."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "revenue@example.test", "phone": "0911111111", "password": "password123"})
        customer_headers = self.token("revenue@example.test")
        admin_headers    = self.token("admin@example.test")
        endpoint         = "/api/v1/admin/overview/daily-revenue"
        self.assertEqual(self.client.get(endpoint).status_code, 401)
        self.assertEqual(self.client.get(endpoint, headers=customer_headers).status_code, 403)
        body = {"recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod", "items": [{"product_id": 1, "quantity": "1"}]}
        cases = [
            (datetime(2026, 11, 17, 16, 30, tzinfo=timezone.utc), "completed", 10000),
            (datetime(2026, 11, 17, 17, 30, tzinfo=timezone.utc), "completed", 20000),
            (datetime(2026, 11, 18, 2, 30, tzinfo=timezone.utc), "completed", 30000),
            (datetime(2026, 11, 18, 3, 30, tzinfo=timezone.utc), "pending", 40000),
        ]
        for created_at, status, total_vnd in cases:
            created = self.client.post("/api/v1/orders", json=body, headers=customer_headers)
            self.assertEqual(created.status_code, 201)
            order = Order.query.filter_by(order_code=created.json["order_code"]).one()
            order.created_at = created_at
            order.status     = status
            order.total_vnd  = total_vnd
        db.session.commit()
        result = self.client.get(f"{endpoint}?page=1&limit=1", headers=admin_headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["total"], 2)
        self.assertEqual(result.json["items"], [{"day": "2026-11-18", "order_count": 2, "total_vnd": 50000}])
        older = self.client.get(f"{endpoint}?page=2&limit=1", headers=admin_headers)
        self.assertEqual(older.json["items"], [{"day": "2026-11-17", "order_count": 1, "total_vnd": 10000}])
        filtered = self.client.get(f"{endpoint}?from_date=2026-11-18&to_date=2026-11-18", headers=admin_headers)
        self.assertEqual(filtered.json["total"], 1)
        self.assertEqual(filtered.json["items"], [{"day": "2026-11-18", "order_count": 2, "total_vnd": 50000}])
        self.assertEqual(self.client.get(f"{endpoint}?from_date=2026-11-19&to_date=2026-11-18", headers=admin_headers).status_code, 400)
        self.assertEqual(self.client.get(f"{endpoint}?from_date=18-11-2026", headers=admin_headers).status_code, 400)

    def test_sepay_ipn_matches_once_and_rejects_wrong_amount(self):
        """Tạo đơn Sandbox; đầu vào IPN hợp lệ, đầu ra paid một lần; ví dụ gửi lại cùng UUID."""
        os.environ["SEPAY_MERCHANT_ID"]   = "SP-TEST-EXAMPLE"
        os.environ["SEPAY_SECRET_KEY"]    = "spsk_test_example_only"
        os.environ["SEPAY_IPN_SECRET_KEY"] = "ipn-example-only"
        try:
            customer = self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "lan-sepay@example.test", "phone": "0911111111", "password": "password123"})
            self.assertEqual(customer.status_code, 201)
            headers = self.token("lan-sepay@example.test")
            created = self.client.post("/api/v1/orders", json={"recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "sepay", "items": [{"product_id": 1, "quantity": "2"}]}, headers=headers)
            self.assertEqual(created.status_code, 201)
            self.assertEqual(created.json["payment_status"], "pending")
            checkout = created.json["sepay_checkout"]
            self.assertEqual(checkout["action"], "https://pay-sandbox.sepay.vn/v1/checkout/init")
            invoice = checkout["fields"]["order_invoice_number"]
            payload = {"notification_type": "ORDER_PAID", "order": {"order_invoice_number": invoice, "order_status": "CAPTURED", "order_currency": "VND", "order_amount": "40000.00"}, "transaction": {"id": "test-uuid-92704", "transaction_type": "PAYMENT", "transaction_status": "APPROVED", "transaction_amount": "40000", "transaction_currency": "VND"}}
            endpoint = "/api/v1/orders/sepay/ipn"
            self.assertEqual(self.client.post(endpoint, json=payload).status_code, 401)
            authorized = {"X-Secret-Key": "ipn-example-only"}
            self.assertFalse(self.client.post(endpoint, json={**payload, "transaction": {**payload["transaction"], "transaction_amount": "39000"}}, headers=authorized).json["matched"])
            self.assertTrue(self.client.post(endpoint, json=payload, headers=authorized).json["matched"])
            self.assertTrue(self.client.post(endpoint, json=payload, headers=authorized).json["matched"])
            detail = self.client.get(f"/api/v1/orders/{created.json['order_code']}", headers=headers)
            self.assertEqual(detail.json["payment_status"], "paid")
        finally:
            for name in ("SEPAY_MERCHANT_ID", "SEPAY_SECRET_KEY", "SEPAY_IPN_SECRET_KEY"):
                os.environ.pop(name, None)

    def test_sepay_gateway_is_hidden_for_new_orders(self):
        """Ẩn cổng cũ khỏi checkout; đầu vào Merchant Test, đầu ra chỉ COD khi thiếu QR ngân hàng."""
        os.environ["SEPAY_MERCHANT_ID"] = "SP-TEST-EXAMPLE"
        os.environ["SEPAY_SECRET_KEY"]  = "spsk_test_example_only"
        try:
            methods = self.client.get("/api/v1/orders/payment-methods")
            self.assertNotIn("sepay", methods.json["items"])
        finally:
            os.environ.pop("SEPAY_MERCHANT_ID", None)
            os.environ.pop("SEPAY_SECRET_KEY", None)

    def test_sepay_bank_qr_and_webhook(self):
        """Tạo QR ACB và xác nhận webhook; đầu vào tiền vào đúng mã, đầu ra paid một lần."""
        os.environ["SEPAY_BANK_CODE"]            = "ACB"
        os.environ["SEPAY_ACCOUNT_NUMBER"]       = "22810217"
        os.environ["SEPAY_ACCOUNT_NAME"]         = "TỐNG THÀNH TÀI"
        os.environ["SEPAY_BANK_WEBHOOK_API_KEY"] = "bank-webhook-test-key"
        try:
            self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "lan-bank@example.test", "phone": "0911111111", "password": "password123"})
            headers = self.token("lan-bank@example.test")
            created = self.client.post("/api/v1/orders", json={"recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "sepay_bank", "items": [{"product_id": 1, "quantity": "2"}]}, headers=headers)
            self.assertEqual(created.status_code, 201)
            transfer = created.json["bank_transfer"]
            self.assertEqual(transfer["account_number"], "22810217")
            self.assertIn("acc=22810217", transfer["qr_url"])
            self.assertIn("amount=40000", transfer["qr_url"])
            code = transfer["payment_code"]
            report_endpoint = f"/api/v1/orders/{created.json['order_code']}/sepay/bank-transfer-reported"
            self.assertEqual(self.client.post(report_endpoint).status_code, 401)
            reported = self.client.post(report_endpoint, headers=headers)
            self.assertEqual(reported.status_code, 200)
            self.assertIsNotNone(reported.json["bank_transfer_reported_at"])
            self.assertEqual(reported.json["payment_status"], "pending")
            self.assertEqual(self.client.post(report_endpoint, headers=headers).json["bank_transfer_reported_at"], reported.json["bank_transfer_reported_at"])
            payload = {"id": 92704, "accountNumber": "22810217", "content": code, "transferType": "in", "transferAmount": 40000}
            endpoint = "/api/v1/orders/sepay/bank-webhook"
            self.assertEqual(self.client.post(endpoint, json=payload).status_code, 401)
            authorized = {"Authorization": "Apikey bank-webhook-test-key"}
            self.assertFalse(self.client.post(endpoint, json={**payload, "transferAmount": 39000}, headers=authorized).json["matched"])
            self.assertTrue(self.client.post(endpoint, json=payload, headers=authorized).json["matched"])
            self.assertEqual(self.client.get(f"/api/v1/orders/{created.json['order_code']}", headers=headers).json["payment_status"], "paid")
            self.assertTrue(self.client.post(endpoint, json=payload, headers=authorized).json["matched"])
        finally:
            for name in ("SEPAY_BANK_CODE", "SEPAY_ACCOUNT_NUMBER", "SEPAY_ACCOUNT_NAME", "SEPAY_BANK_WEBHOOK_API_KEY"):
                os.environ.pop(name, None)

    def test_admin_confirms_reported_bank_payment(self):
        """Khách báo chuyển khoản, admin đối soát tay; đầu vào đơn QR, đầu ra paid và cho phép xử lý đơn."""
        os.environ["SEPAY_BANK_CODE"]      = "ACB"
        os.environ["SEPAY_ACCOUNT_NUMBER"] = "22810217"
        os.environ["SEPAY_ACCOUNT_NAME"]   = "TỐNG THÀNH TÀI"
        try:
            self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "lan-manual@example.test", "phone": "0911111111", "password": "password123"})
            customer_headers = self.token("lan-manual@example.test")
            admin_headers    = self.token("admin@example.test")
            created = self.client.post("/api/v1/orders", json={"recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "sepay_bank", "items": [{"product_id": 1, "quantity": "2"}]}, headers=customer_headers)
            order_id = db.session.query(Order.id).filter_by(order_code=created.json["order_code"]).scalar()
            report_url  = f"/api/v1/orders/{created.json['order_code']}/sepay/bank-transfer-reported"
            confirm_url = f"/api/v1/admin/orders/{order_id}/confirm-bank-payment"
            self.assertEqual(self.client.post(report_url, headers=customer_headers).json["payment_status"], "pending")
            self.assertEqual(self.client.post(confirm_url, headers=customer_headers).status_code, 403)
            self.assertEqual(self.client.post(f"/api/v1/admin/orders/{order_id}/transitions", json={"to_status": "confirmed"}, headers=admin_headers).status_code, 409)
            confirmed = self.client.post(confirm_url, headers=admin_headers)
            self.assertEqual(confirmed.status_code, 200)
            self.assertEqual(confirmed.json["payment_status"], "paid")
            self.assertIsNotNone(confirmed.json["bank_payment_confirmed_at"])
            self.assertEqual(confirmed.json["bank_payment_confirmed_by"], 1)
            self.assertEqual(self.client.post(f"/api/v1/admin/orders/{order_id}/transitions", json={"to_status": "confirmed"}, headers=admin_headers).status_code, 200)
        finally:
            for name in ("SEPAY_BANK_CODE", "SEPAY_ACCOUNT_NUMBER", "SEPAY_ACCOUNT_NAME"):
                os.environ.pop(name, None)

    def test_batch_code_is_generated_from_product_name(self):
        """Tạo hai lô cùng sản phẩm/ngày: mã theo tên nhưng khác nhau; sửa lô giữ mã cũ."""
        headers = self.token("admin@example.test")
        product = Product.query.first()
        body    = {"product_id": product.id, "growing_region": "Đà Lạt", "origin": "Lâm Đồng", "harvest_date": "2026-11-17", "quantity": "2"}

        first  = self.client.post("/api/v1/admin/batches", json=body, headers=headers)
        second = self.client.post("/api/v1/admin/batches", json=body, headers=headers)
        self.assertEqual(first.status_code, 201)
        self.assertEqual(second.status_code, 201)
        self.assertTrue(first.json["batch_code"].startswith("CA-ROT-20261117-"))
        self.assertNotEqual(first.json["batch_code"], second.json["batch_code"])

        changed = self.client.patch(f"/api/v1/admin/batches/{first.json['id']}", json={"growing_region": "Đức Trọng"}, headers=headers)
        self.assertEqual(changed.json["batch_code"], first.json["batch_code"])
        manual = self.client.post("/api/v1/admin/batches", json={**body, "batch_code": "TU-NHAP"}, headers=headers)
        self.assertEqual(manual.status_code, 400)

    def test_hidden_batch_is_not_sellable(self):
        """Ẩn lô không xóa dữ liệu; đầu ra tồn bán bằng 0 và đơn mới bị chặn. Ví dụ ẩn lô 5 kg."""
        headers = self.token("admin@example.test")
        batch   = ProduceBatch.query.first()
        hidden  = self.client.patch(f"/api/v1/admin/batches/{batch.id}", json={"is_visible": False}, headers=headers)
        self.assertEqual(hidden.status_code, 200)
        self.assertFalse(hidden.json["is_visible"])
        self.assertEqual(Decimal(self.client.get("/api/v1/products/1").json["stock"]), Decimal("0"))
        self.assertEqual(self.client.get("/api/v1/products/1/batches").json["total"], 0)
        self.assertEqual(self.client.get("/api/v1/admin/batches?visible=false", headers=headers).json["total"], 1)
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "lan@example.test", "phone": "0911111111", "password": "password123"})
        customer_headers = self.token("lan@example.test")
        quote = self.client.post("/api/v1/orders/quote", json={"items": [{"product_id": 1, "quantity": "1"}]}, headers=customer_headers)
        self.assertEqual(quote.status_code, 409)
        self.assertEqual(self.client.patch(f"/api/v1/admin/batches/{batch.id}", json={"is_visible": True}, headers=headers).status_code, 200)
        self.assertEqual(self.client.get("/api/v1/products/1").json["stock"], "5.000")

    def test_discount_orders_are_paginated_and_admin_only(self):
        """Tra mã chỉ trả đơn đã dùng mã; đầu vào discount_id/page, đầu ra trang đơn. Ví dụ GIAM10 có một đơn."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "lan@example.test", "phone": "0911111111", "password": "password123"})
        customer_headers = self.token("lan@example.test")
        admin_headers    = self.token("admin@example.test")
        body = {"recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod", "discount_code": "GIAM10", "items": [{"product_id": 1, "quantity": "1"}]}
        created = self.client.post("/api/v1/orders", json=body, headers=customer_headers)
        self.assertEqual(created.status_code, 201)
        discount_id = DiscountCode.query.filter_by(code="GIAM10").first().id
        path        = f"/api/v1/admin/discounts/{discount_id}/orders?page=1&limit=1"
        self.assertEqual(self.client.get(path, headers=customer_headers).status_code, 403)
        result = self.client.get(path, headers=admin_headers)
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json["total"], 1)
        self.assertEqual(result.json["items"][0]["order_code"], created.json["order_code"])
        self.assertEqual(result.json["items"][0]["discount_vnd"], 2000)
        renamed = self.client.patch(f"/api/v1/admin/discounts/{discount_id}", json={"code": "MOI"}, headers=admin_headers)
        self.assertEqual(renamed.status_code, 409)
        disabled = self.client.patch(f"/api/v1/admin/discounts/{discount_id}", json={"is_active": False}, headers=admin_headers)
        self.assertEqual(disabled.status_code, 200)
        self.assertEqual(self.client.get(path, headers=admin_headers).json["total"], 1)

    def test_supplier_purchase_receipt_and_permissions(self):
        """Đặt và nhận 2 kg từ nhà cung cấp; đầu ra lô tăng tồn một lần, khách không có quyền."""
        headers = self.token("admin@example.test")
        supplier = self.client.post("/api/v1/admin/suppliers", json={"name": "Trang trại A", "phone": "0901234567"}, headers=headers)
        self.assertEqual(supplier.status_code, 201)
        self.assertEqual(self.client.get("/api/v1/admin/suppliers?q=Trang", headers=headers).json["total"], 1)
        body = {"supplier_id": supplier.json["id"], "items": [{"product_id": 1, "quantity": "2", "unit_cost_vnd": 15000}]}
        created = self.client.post("/api/v1/admin/purchases", json=body, headers=headers)
        self.assertEqual(created.status_code, 201)
        order_id = created.json["id"]
        item_id  = created.json["items"][0]["id"]
        self.assertEqual(created.json["total_vnd"], 30000)
        other = self.client.post("/api/v1/admin/suppliers", json={"name": "Trang trại B"}, headers=headers)
        self.assertEqual(self.client.get(f"/api/v1/admin/purchases?supplier_id={supplier.json['id']}&page=1&limit=10", headers=headers).json["total"], 1)
        self.assertEqual(self.client.get(f"/api/v1/admin/purchases?supplier_id={other.json['id']}&page=1&limit=10", headers=headers).json["total"], 0)
        self.assertEqual(self.client.get("/api/v1/admin/purchases?supplier_id=bad", headers=headers).status_code, 400)
        self.assertEqual(self.client.post(f"/api/v1/admin/purchases/{order_id}/receive", json={"batches": []}, headers=headers).status_code, 409)
        self.assertEqual(self.client.patch(f"/api/v1/admin/purchases/{order_id}/status", json={"status": "ordered"}, headers=headers).status_code, 200)
        self.assertEqual(self.client.patch(f"/api/v1/admin/purchases/{order_id}/status", json={"status": "received"}, headers=headers).status_code, 400)
        received = self.client.patch(f"/api/v1/admin/purchases/{order_id}/status", json={"status": "received", "batches": [{"item_id": item_id, "growing_region": "Đà Lạt", "origin": "Việt Nam", "harvest_date": "2026-11-17"}]}, headers=headers)
        self.assertEqual(received.status_code, 200)
        self.assertEqual(received.json["status"], "received")
        self.assertTrue(received.json["items"][0]["batch_code"].startswith("CA-ROT-20261117-"))
        self.assertEqual(sum(batch.remaining_quantity for batch in ProduceBatch.query.all()), Decimal("7"))
        self.assertEqual(self.client.post(f"/api/v1/admin/purchases/{order_id}/receive", json={"batches": []}, headers=headers).status_code, 409)
        self.assertEqual(self.client.patch(f"/api/v1/admin/purchases/{order_id}/status", json={"status": "received", "batches": [{"item_id": item_id, "growing_region": "Đà Lạt", "origin": "Việt Nam", "harvest_date": "2026-11-17"}]}, headers=headers).status_code, 409)
        self.assertEqual(sum(batch.remaining_quantity for batch in ProduceBatch.query.all()), Decimal("7"))
        self.assertEqual(self.client.delete(f"/api/v1/admin/suppliers/{supplier.json['id']}", headers=headers).status_code, 409)
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "lan@example.test", "phone": "0911111111", "password": "password123"})
        self.assertEqual(self.client.get("/api/v1/admin/purchases", headers=self.token("lan@example.test")).status_code, 403)

    def test_admin_units_and_product_assignment(self):
        """Admin thêm/tắt đơn vị, chọn cho sản phẩm và không đổi đơn vị khi còn tồn."""
        headers = self.token("admin@example.test")
        listed  = self.client.get("/api/v1/admin/units", headers=headers)
        self.assertEqual({item["code"] for item in listed.json["items"]}, {"kg", "bó", "hộp"})

        created = self.client.post("/api/v1/admin/units", json={"code": "thùng", "allows_fraction": False}, headers=headers)
        self.assertEqual(created.status_code, 201)
        unit_id = created.json["id"]
        product = self.client.post("/api/v1/admin/products", json={"name": "Cam", "category": "Trái cây", "unit": "thùng", "price_vnd": 50000}, headers=headers)
        self.assertEqual(product.status_code, 201)
        self.assertEqual(product.json["unit"], "thùng")
        self.assertEqual(self.client.get("/api/v1/products?unit=thùng").json["total"], 1)

        disabled = self.client.patch(f"/api/v1/admin/units/{unit_id}", json={"is_active": False}, headers=headers)
        self.assertEqual(disabled.status_code, 200)
        rejected = self.client.post("/api/v1/admin/products", json={"name": "Táo", "category": "Trái cây", "unit": "thùng", "price_vnd": 50000}, headers=headers)
        self.assertEqual(rejected.status_code, 400)
        self.assertEqual(self.client.delete(f"/api/v1/admin/units/{unit_id}", headers=headers).status_code, 409)

        current = Product.query.filter_by(name="Cà rốt").first()
        blocked = self.client.patch(f"/api/v1/admin/products/{current.id}", json={"unit": "hộp"}, headers=headers)
        self.assertEqual(blocked.status_code, 409)
        self.assertTrue(ProductUnit.query.filter_by(code="kg").first().allows_fraction)

    def test_insufficient_stock_rolls_back_and_discount_is_checked(self):
        """Không tạo đơn khi thiếu hàng; mã không đạt điều kiện bị từ chối trên server."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "lan@example.test", "phone": "0911111111", "password": "password123"})
        headers = self.token("lan@example.test")
        body    = {"recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "items": [{"product_id": 1, "quantity": "6"}]}
        response = self.client.post("/api/v1/orders", json=body, headers=headers)
        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json["error"]["code"], "insufficient_stock")
        self.assertEqual(ProduceBatch.query.first().remaining_quantity, Decimal("5"))
        self.assertEqual(self.client.get("/api/v1/orders", headers=headers).json["total"], 0)
        body["items"][0]["quantity"] = "0.1"
        body["discount_code"]         = "GIAM10"
        response = self.client.post("/api/v1/orders/quote", json=body, headers=headers)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json["error"]["code"], "invalid_discount")

    def test_product_images_upload_and_remove(self):
        """Admin lưu ảnh chính/chi tiết, ảnh công khai xem được, ảnh bỏ được xóa."""
        headers = self.token("admin@example.test")
        picture = BytesIO()
        Image.new("RGB", (8, 8), "green").save(picture, format="PNG")
        picture.seek(0)
        response = self.client.post("/api/v1/admin/products/1/images", data={"main": (BytesIO(picture.getvalue()), "main.png"), "details": (BytesIO(picture.getvalue()), "detail.png")}, headers=headers)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.json["images"]), 1)
        main_url   = response.json["image_url"]
        detail_id  = response.json["images"][0]["id"]
        detail_url = response.json["images"][0]["image_url"]
        main_response = self.client.get(main_url)
        self.assertEqual(main_response.status_code, 200)
        main_response.close()
        self.assertEqual(self.client.get("/api/v1/products/1").json["images"][0]["id"], detail_id)
        removed = self.client.post("/api/v1/admin/products/1/images", data={"remove_ids": f"[{detail_id}]"}, headers=headers)
        self.assertEqual(removed.json["images"], [])
        self.assertEqual(self.client.get(detail_url).status_code, 404)
        invalid = self.client.post("/api/v1/admin/products/1/images", data={"main": (BytesIO(b"not an image"), "fake.png")}, headers=headers)
        self.assertEqual(invalid.status_code, 400)
        main_response = self.client.get(main_url)
        self.assertEqual(main_response.status_code, 200)
        main_response.close()

    def test_product_slug_is_public_and_unique(self):
        """Tên tiếng Việt tạo URL dễ đọc; tên trùng có slug riêng và sản phẩm ẩn không xem được."""
        first = Product.query.first()
        self.assertEqual(first.slug, "ca-rot")
        self.assertEqual(self.client.get("/api/v1/products/by-slug/ca-rot").json["id"], first.id)
        second = Product(name="Cà rốt", unit="kg", price_vnd=21000)
        db.session.add(second)
        db.session.commit()
        self.assertEqual(second.slug, "ca-rot-2")
        first.is_visible = False
        db.session.commit()
        self.assertEqual(self.client.get("/api/v1/products/by-slug/ca-rot").status_code, 404)

    def test_quote_confirmation_is_revalidated_and_idempotent(self):
        """Báo giá đổi giá bị từ chối; xác nhận lặp chỉ tạo một đơn và trừ tồn một lần."""
        self.client.post("/api/v1/auth/register", json={"name": "Lan", "email": "lan@example.test", "phone": "0911111111", "password": "password123"})
        headers = self.token("lan@example.test")
        quote   = self.client.post("/api/v1/orders/quote", json={"items": [{"product_id": 1, "quantity": "2"}], "discount_code": "GIAM10"}, headers=headers)
        self.assertEqual(quote.status_code, 200)
        self.assertEqual(quote.json["total_vnd"], 36000)
        self.assertIsNone(quote.json["shipping_fee_vnd"])
        body = {"quote_id": quote.json["quote_id"], "recipient_name": "Lan", "recipient_phone": "0911111111", "delivery_address": "Đà Lạt", "payment_method": "cod"}
        Product.query.first().price_vnd = 30000
        db.session.commit()
        changed = self.client.post("/api/v1/orders/confirm", json=body, headers=headers)
        self.assertEqual(changed.status_code, 409)
        self.assertEqual(changed.json["error"]["code"], "quote_changed")
        self.assertEqual(ProduceBatch.query.first().remaining_quantity, Decimal("5"))
        Product.query.first().price_vnd = 20000
        db.session.commit()
        created  = self.client.post("/api/v1/orders/confirm", json=body, headers=headers)
        repeated = self.client.post("/api/v1/orders/confirm", json=body, headers=headers)
        self.assertEqual(created.status_code, 201)
        self.assertEqual(repeated.status_code, 200)
        self.assertEqual(created.json["order_code"], repeated.json["order_code"])
        self.assertEqual(ProduceBatch.query.first().remaining_quantity, Decimal("3"))

    def test_categories_filter_and_latest_order(self):
        """Danh mục lọc đúng và danh sách mới nhất theo thời gian tạo; ví dụ /products?category=Rau%20củ%20quả."""
        newest = Product(name="Cà chua", category="Rau củ quả", unit="hộp", price_vnd=22000)
        other  = Product(name="Nấm mỡ", category="Nấm & gia vị", unit="hộp", price_vnd=45000)
        db.session.add_all([newest, other])
        db.session.commit()
        category_response = self.client.get("/api/v1/products/categories")
        self.assertIn("Rau củ quả", category_response.json["items"])
        self.assertIn("Trái cây", category_response.json["items"])
        filtered = self.client.get("/api/v1/products?category=Rau%20củ%20quả")
        self.assertEqual(filtered.json["total"], 2)
        self.assertTrue(all(item["category"] == "Rau củ quả" for item in filtered.json["items"]))
        latest = self.client.get("/api/v1/products?limit=3")
        # Danh sách công khai ưu tiên sản phẩm có tồn trước nhóm hết hàng.
        self.assertEqual(latest.json["items"][0]["id"], Product.query.filter_by(name="Cà rốt").first().id)


if __name__ == "__main__":
    unittest.main()
