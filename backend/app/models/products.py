"""Bảng dữ liệu products; giữ nguyên tên bảng và ràng buộc migration."""

from sqlalchemy import CheckConstraint, ForeignKey, Index, event
from sqlalchemy.orm import relationship

from app import db
from app.models.base import now_utc


class Product(db.Model):
    __tablename__ = "products"

    id          = db.Column(db.Integer, primary_key=True)
    name        = db.Column(db.String(180), nullable=False)
    slug        = db.Column(db.String(220), nullable=False, unique=True, index=True)
    category    = db.Column(db.String(80), nullable=False, default="Rau củ quả", server_default="Rau củ quả")
    description = db.Column(db.Text, nullable=False, default="")
    unit        = db.Column(db.String(10), ForeignKey("product_units.code"), nullable=False)
    price_vnd   = db.Column(db.Integer, nullable=False)
    image_url   = db.Column(db.String(500))
    is_visible  = db.Column(db.Boolean, nullable=False, default=True)
    created_at  = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    unit_definition = relationship("ProductUnit")
    batches     = relationship("ProduceBatch", back_populates="product")
    images      = relationship("ProductImage", back_populates="product", cascade="all, delete-orphan", lazy="selectin", order_by="ProductImage.id")

    __table_args__ = (
        CheckConstraint("price_vnd >= 0", name="ck_product_price"),
    )


class ProduceBatch(db.Model):
    __tablename__ = "produce_batches"

    id                 = db.Column(db.Integer, primary_key=True)
    product_id         = db.Column(db.Integer, ForeignKey("products.id"), nullable=False, index=True)
    batch_code         = db.Column(db.String(80), nullable=False, unique=True)
    growing_region     = db.Column(db.String(180), nullable=False)
    origin             = db.Column(db.String(255), nullable=False)
    harvest_date       = db.Column(db.Date, nullable=False)
    remaining_quantity = db.Column(db.Numeric(12, 3), nullable=False)
    is_visible         = db.Column(db.Boolean, nullable=False, default=True, server_default="true")
    created_at         = db.Column(db.DateTime(timezone=True), nullable=False, default=now_utc)
    product            = relationship("Product", back_populates="batches")

    __table_args__ = (
        CheckConstraint("remaining_quantity >= 0", name="ck_batch_quantity"),
        Index("ix_batches_created_at", "created_at"),
    )


class ProductImage(db.Model):
    """Một ảnh chi tiết của sản phẩm; ảnh chính tiếp tục lưu ở Product.image_url."""

    __tablename__ = "product_images"

    id         = db.Column(db.Integer, primary_key=True)
    product_id = db.Column(db.Integer, ForeignKey("products.id", ondelete="CASCADE"), nullable=False, index=True)
    image_url  = db.Column(db.String(500), nullable=False)
    product    = relationship("Product", back_populates="images")


@event.listens_for(Product, "before_insert")
def assign_product_slug(mapper, connection, target):
    """Gán slug khi tạo sản phẩm, kể cả dữ liệu seed/test; đầu vào Product, đầu ra slug trên bản ghi; ví dụ Cà rốt -> ca-rot."""
    if not target.slug:
        from app.products.slug import unique_slug

        target.slug = unique_slug(connection, target.name)
