"""Đơn vị bán do admin quản lý; code được lưu trong sản phẩm và snapshot đơn hàng."""

from sqlalchemy import event

from app import db


class ProductUnit(db.Model):
    """Một đơn vị bán, ví dụ kg cho phép số lẻ còn hộp chỉ nhận số nguyên."""

    __tablename__ = "product_units"

    id              = db.Column(db.Integer, primary_key=True)
    code            = db.Column(db.String(10), nullable=False, unique=True)
    allows_fraction = db.Column(db.Boolean, nullable=False, default=False)
    is_active       = db.Column(db.Boolean, nullable=False, default=True)


@event.listens_for(ProductUnit.__table__, "after_create")
def seed_default_units(target, connection, **kwargs):
    """Nạp ba đơn vị mặc định khi tạo DB mới; đầu vào table/connection, đầu ra 3 dòng. Ví dụ db.create_all()."""
    connection.execute(target.insert(), [
        {"code" : "kg", "allows_fraction" : True, "is_active" : True},
        {"code" : "hộp", "allows_fraction" : False, "is_active" : True},
        {"code" : "bó", "allows_fraction" : False, "is_active" : True},
    ])
