"""Lệnh quản trị chạy thủ công; không tự thay đổi database khi khởi động."""

import json
from datetime import date
from decimal import Decimal
from pathlib import Path

import click
from flask import Flask
from werkzeug.security import generate_password_hash

from app import db
from app.models import Customer, ProduceBatch, Product, ProductImage


def register_commands(app: Flask):
    """Gắn lệnh tạo admin và nạp mẫu; đầu vào Flask app, đầu ra lệnh CLI."""

    @app.cli.command("expire-preorders")
    def expire_preorders():
        """Dọn hàng giữ quá 24 giờ theo lịch; đầu vào: thời gian hiện tại, đầu ra: số đơn hủy. Ví dụ: cron chạy mỗi phút gọi flask --app app expire-preorders."""
        from app.orders.reservations import expire_reservations
        count = expire_reservations()
        db.session.commit()
        click.echo(f"Đã hủy {count} đơn đặt trước quá hạn.")

    @app.cli.command("create-admin")
    @click.option("--name", prompt=True)
    @click.option("--email", prompt=True)
    @click.option("--phone", prompt=True)
    @click.password_option()
    def create_admin(name, email, phone, password):
        """Tạo admin thủ công; ví dụ flask --app app create-admin."""
        email = email.strip().lower()
        if Customer.query.filter_by(email=email).first():
            raise click.ClickException("Email đã tồn tại; không thay đổi tài khoản hiện có.")
        if len(password) < 8 or "@" not in email:
            raise click.ClickException("Email không hợp lệ hoặc mật khẩu dưới 8 ký tự.")
        db.session.add(Customer(name=name.strip(), email=email, phone=phone.strip(), password_hash=generate_password_hash(password), role="admin"))
        db.session.commit()
        click.echo("Đã tạo tài khoản admin.")

    @app.cli.command("seed-sample")
    def seed_sample():
        """Nạp mẫu chỉ khi chưa có sản phẩm; ví dụ flask --app app seed-sample."""
        if db.session.query(Product.id).first():
            raise click.ClickException("Database đã có sản phẩm; không nạp mẫu để tránh thay đổi dữ liệu hiện có.")
        source = Path(__file__).resolve().parent.parent / "sample_data.json"
        data   = json.loads(source.read_text(encoding="utf-8"))
        for entry in data["products"]:
            product = Product(name=entry["name"], description=entry["description"], unit=entry["unit"], price_vnd=entry["price_vnd"])
            db.session.add(product)
            db.session.flush()
            for batch in entry["batches"]:
                db.session.add(ProduceBatch(product_id=product.id, batch_code=batch["batch_code"], growing_region=batch["growing_region"], origin=batch["origin"], harvest_date=date.fromisoformat(batch["harvest_date"]), remaining_quantity=Decimal(batch["quantity"])))
        db.session.commit()
        click.echo("Đã nạp 3 sản phẩm mẫu.")

    @app.cli.command("import-cu-qua")
    @click.option("--dry-run", is_flag=True, help="Chỉ xem sản phẩm sẽ được thêm.")
    def import_cu_qua(dry_run):
        """Nạp danh mục củ quả, bỏ qua tên đã có.

        Đầu vào: backend/catalog/cu_qua.json và cờ --dry-run.
        Đầu ra: số sản phẩm mới; ví dụ flask --app app import-cu-qua --dry-run.
        """
        source   = Path(__file__).resolve().parent.parent / "catalog" / "cu_qua.json"
        entries  = json.loads(source.read_text(encoding="utf-8"))["products"]
        names    = [entry["name"] for entry in entries]
        existing = {
            name.casefold() for (name,) in db.session.query(Product.name).filter(Product.name.in_(names)).all()
        }
        pending = [entry for entry in entries if entry["name"].casefold() not in existing]

        if dry_run:
            for entry in pending:
                click.echo(f'{entry["name"]}: {entry["price_vnd"]:,} đ/{entry["unit"]}')
            click.echo(f"Sẽ thêm {len(pending)} sản phẩm; bỏ qua {len(entries) - len(pending)} sản phẩm đã có.")
            return

        for entry in pending:
            product = Product(
                name        = entry["name"],
                category    = entry["category"],
                description = entry["description"],
                unit        = entry["unit"],
                price_vnd   = entry["price_vnd"],
                image_url   = entry["image_url"],
                is_visible  = True,
            )
            db.session.add(product)
            db.session.flush()
            for image_url in entry["images"]:
                db.session.add(ProductImage(product_id=product.id, image_url=image_url))

        db.session.commit()
        click.echo(f"Đã thêm {len(pending)} sản phẩm; bỏ qua {len(entries) - len(pending)} sản phẩm đã có.")
