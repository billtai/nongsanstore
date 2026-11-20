"""Tải ảnh chính và ảnh chi tiết vào assets/ cùng cấp frontend/backend."""

import json
from io import BytesIO
from pathlib import Path
from uuid import uuid4

from flask import current_app, jsonify, request
from PIL import Image, UnidentifiedImageError

from app import db
from app.admin import admin_api
from app.auth import require_role
from app.errors import ApiError
from app.models import Product, ProductImage
from app.products import product_data

Image.MAX_IMAGE_PIXELS = 20_000_000


def save_image(file, product_id: int) -> tuple[str, Path]:
    """Xác thực và lưu một ảnh; đầu vào tệp/id, đầu ra URL và đường dẫn tệp.

    Ví dụ: ảnh JPEG của sản phẩm 3 thành /assets/products/3/<uuid>.jpg.
    """
    content = file.read(5 * 1024 * 1024 + 1)
    if not content or len(content) > 5 * 1024 * 1024:
        raise ApiError(400, "invalid_image", "Mỗi ảnh phải nhỏ hơn hoặc bằng 5 MB.")
    try:
        probe = Image.open(BytesIO(content))
        if probe.format not in ("JPEG", "PNG", "WEBP"):
            raise ApiError(400, "invalid_image", "Chỉ nhận ảnh JPEG, PNG hoặc WebP.")
        probe.verify()
        image = Image.open(BytesIO(content))
        image.load()
        if image.width * image.height > 20_000_000:
            raise ApiError(400, "invalid_image", "Ảnh vượt quá 20 triệu điểm ảnh.")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise ApiError(400, "invalid_image", "Tệp ảnh không hợp lệ.") from None

    format_name = image.format
    extension   = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp"}[format_name]
    folder      = current_app.config["ASSETS_DIR"] / "products" / str(product_id)
    folder.mkdir(parents=True, exist_ok=True)
    destination = folder / f"{uuid4().hex}.{extension}"
    # Ghi lại ảnh bằng Pillow để loại metadata và tránh lưu nguyên nội dung upload.
    image.save(destination, format=format_name)
    return f"/assets/products/{product_id}/{destination.name}", destination


def local_asset_path(url: str | None, product_id: int) -> Path | None:
    """Chỉ nhận ảnh nằm trong thư mục của sản phẩm; URL cũ bên ngoài trả None."""
    prefix = f"/assets/products/{product_id}/"
    if not url or not url.startswith(prefix):
        return None
    filename = url.removeprefix(prefix)
    if Path(filename).name != filename:
        return None
    return current_app.config["ASSETS_DIR"] / "products" / str(product_id) / filename


@admin_api.post("/products/<int:product_id>/images")
@require_role("admin")
def update_product_images(product_id: int):
    """Thêm/thay ảnh chính, thêm hoặc bỏ ảnh chi tiết.

    Đầu vào: multipart main (tùy chọn), details (nhiều tệp), remove_ids (JSON array).
    Đầu ra: sản phẩm với image_url và images; ví dụ POST ảnh chính và hai ảnh detail.
    """
    product = db.session.get(Product, product_id)
    if product is None:
        raise ApiError(404, "not_found", "Không tìm thấy sản phẩm.")
    try:
        remove_ids = json.loads(request.form.get("remove_ids", "[]"))
    except json.JSONDecodeError:
        raise ApiError(400, "invalid_input", "remove_ids phải là mảng JSON.") from None
    if not isinstance(remove_ids, list) or any(type(value) is not int for value in remove_ids) or len(remove_ids) != len(set(remove_ids)):
        raise ApiError(400, "invalid_input", "remove_ids phải là mảng ID không trùng.")
    existing  = {image.id: image for image in product.images}
    if any(image_id not in existing for image_id in remove_ids):
        raise ApiError(400, "invalid_input", "Ảnh cần bỏ không thuộc sản phẩm.")
    details   = [file for file in request.files.getlist("details") if file.filename]
    main      = request.files.get("main")
    if main and not main.filename:
        main = None
    if not main and not details and not remove_ids:
        raise ApiError(400, "invalid_input", "Cần chọn ảnh hoặc ảnh cần bỏ.")
    if len(existing) - len(remove_ids) + len(details) > 10:
        raise ApiError(400, "invalid_input", "Tối đa 10 ảnh chi tiết cho một sản phẩm.")

    created_paths = []
    removed_paths = []
    try:
        if main:
            new_url, new_path = save_image(main, product_id)
            created_paths.append(new_path)
            old_path = local_asset_path(product.image_url, product_id)
            if old_path:
                removed_paths.append(old_path)
            product.image_url = new_url
        for file in details:
            new_url, new_path = save_image(file, product_id)
            created_paths.append(new_path)
            db.session.add(ProductImage(product_id=product_id, image_url=new_url))
        for image_id in remove_ids:
            removed_paths.append(local_asset_path(existing[image_id].image_url, product_id))
            db.session.delete(existing[image_id])
        db.session.commit()
    except Exception:
        db.session.rollback()
        for path in created_paths:
            path.unlink(missing_ok=True)
        raise
    for path in removed_paths:
        if path:
            path.unlink(missing_ok=True)
    return jsonify(product_data(product))
