"""Bảng dữ liệu users; giữ nguyên tên bảng và ràng buộc migration."""

from sqlalchemy import CheckConstraint, ForeignKey, Index
from sqlalchemy.orm import relationship

from app import db
from app.models.base import now_utc


class Customer(db.Model):
    __tablename__ = "customers"

    id            = db.Column(db.Integer, primary_key=True)
    name          = db.Column(db.String(120), nullable=False)
    email         = db.Column(db.String(255), nullable=False, unique=True, index=True)
    phone         = db.Column(db.String(30), nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), nullable=False, default="customer")
    created_at    = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)

    __table_args__ = (CheckConstraint("role IN ('customer', 'admin')", name="ck_customer_role"),)
