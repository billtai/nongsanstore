import type { CartLine } from "@/types/store";

const CART_KEY = "nong-san-cart";

/** Đọc giỏ hàng cục bộ an toàn. Đầu vào: không có; đầu ra: các mã sản phẩm và số lượng. Ví dụ: readCart() sau khi thêm một sản phẩm. */
export function readCart(): CartLine[] {
  try { return JSON.parse(localStorage.getItem(CART_KEY) || "[]") as CartLine[]; }
  catch { return []; }
}

/** Ghi giỏ hàng cục bộ và báo cho thanh điều hướng. Đầu vào: các dòng giỏ; đầu ra: không có. Ví dụ: writeCart([{ product_id: "1", quantity: 2 }]). */
export function writeCart(lines: CartLine[]): void {
  localStorage.setItem(CART_KEY, JSON.stringify(lines));
  window.dispatchEvent(new Event("cart-change"));
}

