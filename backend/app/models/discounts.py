"""Bảng dữ liệu discounts; giữ nguyên tên bảng và ràng buộc migration."""

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import relationship

from app import db
from app.models.base import now_utc


class DiscountCode(db.Model):
    __tablename__ = "discount_codes"

    id               = db.Column(db.Integer, primary_key=True)
    code             = db.Column(db.String(50), nullable=False, unique=True)
    kind             = db.Column(db.String(10), nullable=False)
    value            = db.Column(db.Integer, nullable=False)
    min_subtotal_vnd = db.Column(db.Integer, nullable=False, default=0)
    starts_at        = db.Column(db.DateTime(timezone=True))
    ends_at          = db.Column(db.DateTime(timezone=True))
    usage_limit      = db.Column(db.Integer)
    used_count       = db.Column(db.Integer, nullable=False, default=0)
    is_active        = db.Column(db.Boolean, nullable=False, default=True)

    __table_args__ = (
        CheckConstraint("kind IN ('fixed', 'percent')", name="ck_discount_kind"),
        CheckConstraint("value > 0", name="ck_discount_value"),
        CheckConstraint("kind != 'percent' OR value <= 100", name="ck_discount_percent"),
        CheckConstraint("min_subtotal_vnd >= 0", name="ck_discount_minimum"),
        CheckConstraint("usage_limit IS NULL OR usage_limit > 0", name="ck_discount_limit"),
        CheckConstraint("used_count >= 0", name="ck_discount_used"),
    )
