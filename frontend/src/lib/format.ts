/** Định dạng VND; đầu vào số tiền, đầu ra chuỗi. Ví dụ: money(12000) → 12.000 ₫. */
export function money(value: number): string {
  return new Intl.NumberFormat("vi-VN", { style: "currency", currency: "VND" }).format(value);
}
