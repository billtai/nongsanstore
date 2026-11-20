// Trình duyệt gọi API cùng origin; Next.js chuyển tiếp đến Flask theo API_URL.
// Ví dụ: trang ở localhost:3000 gọi /api/v1/products.

/**
 * Chuyển sản phẩm từ API Flask sang dữ liệu giao diện.
 * Đầu vào: bản ghi có price_vnd/stock; đầu ra: Product có price/stock_quantity.
 * Ví dụ: { id: 1, price_vnd: 20000, stock: "5" } thành giá 20000 và tồn 5.
 */
function productFromApi(raw: Record<string, unknown>) {
  return {
    ...raw,
    id             : String(raw.id),
    category       : String(raw.category || "Nông sản"),
    price          : Number(raw.price_vnd),
    stock_quantity : Number(raw.stock),
  };
}

/** Gọi API và giữ nguyên thông báo lỗi từ backend. Đầu vào: đường dẫn và tùy chọn fetch; đầu ra: JSON kiểu T. Ví dụ: api<ProductPage>("/products?page=1"). */
export async function api<T>(path: string, options: RequestInit = {}): Promise<T> {
  // Đầu vào: token đăng nhập của tab; đầu ra: header xác thực cho API khách hàng.
  // Ví dụ: sau khi đăng nhập, yêu cầu /orders/quote gửi Bearer token tự động.
  const token = typeof window !== "undefined" ? sessionStorage.getItem("nong-san-customer-token") : null;
  const response = await fetch(`/api/v1${path}`, {
    credentials : "include",
    cache       : "no-store",
    ...options,
    headers     : { "Content-Type": "application/json", ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options.headers },
  });
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    if (response.status === 401) throw new Error("Vui lòng đăng nhập để xem đơn hàng.");
    if (response.status === 404) throw new Error(body.error?.message || body.message || "Không tìm thấy dữ liệu yêu cầu.");
    throw new Error(body.error?.message || body.message || "Có lỗi xảy ra. Vui lòng thử lại sau.");
  }
  const data = await response.json();
  if (path.startsWith("/products?") && Array.isArray(data.items)) {
    return {
      ...data,
      items     : data.items.map(productFromApi),
      page_size : data.limit,
    } as T;
  }
  if (/^\/products\/\d+$/.test(path) || path.startsWith("/products/by-slug/")) {
    return productFromApi(data) as T;
  }
  return data as T;
}

