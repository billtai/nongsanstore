"""Tạo slug URL ổn định và duy nhất cho sản phẩm."""

import re
import unicodedata

from sqlalchemy import select


def slugify(name: str) -> str:
    """Chuyển tên sang slug ASCII; đầu vào tên, đầu ra slug; ví dụ 'Cà rốt Đà Lạt' -> 'ca-rot-da-lat'."""
    normalized = unicodedata.normalize("NFKD", name.replace("đ", "d").replace("Đ", "D"))
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    return re.sub(r"-+", "-", re.sub(r"[^a-z0-9]+", "-", ascii_name)).strip("-") or "san-pham"


def unique_slug(connection, name: str) -> str:
    """Tạo slug chưa trùng trong DB; đầu vào kết nối/tên, đầu ra slug; ví dụ tên trùng -> 'ca-rot-2'."""
    from app.models.products import Product

    base       = slugify(name)
    candidate  = base
    suffix     = 2
    while connection.execute(select(Product.id).where(Product.slug == candidate)).first():
        candidate = f"{base}-{suffix}"
        suffix   += 1
    return candidate
