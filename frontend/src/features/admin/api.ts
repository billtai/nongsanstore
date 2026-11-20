/**
 * Gọi API và chuyển lỗi HTTP thành thông báo có thể đọc.
 * Đầu vào: path và tùy chọn fetch; đầu ra: JSON đã parse hoặc Error.
 * Ví dụ: api('/admin/products?page=1') trả danh sách sản phẩm.
 */
export async function adminApi(path: string, options?: RequestInit) {
  const response = await fetch(path.startsWith("/admin/") ? `/api${path}` : path, { credentials: "include", ...options });
  const data = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(data.error?.message || `API báo lỗi ${response.status}.`);
  return data;
}

