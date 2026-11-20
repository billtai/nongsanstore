/** Nhãn trạng thái và định dạng hiển thị dùng trong quản trị. */
export const statusText: Record<string, string> = {
  preordered : "Chờ hàng",
  awaiting_price_approval : "Chờ khách duyệt giá",
  pending    : "Chờ xác nhận",
  confirmed  : "Đã xác nhận",
  preparing  : "Đang chuẩn bị",
  delivering : "Đang giao",
  completed  : "Hoàn thành",
  cancelled  : "Đã hủy",
};
export const nextStatus: Record<string, string[]> = {
  preordered : ["cancelled"],
  awaiting_price_approval : ["cancelled"],
  pending    : ["confirmed", "cancelled"],
  confirmed  : ["preparing", "cancelled"],
  preparing  : ["delivering", "cancelled"],
  delivering : ["completed"],
  completed  : [],
  cancelled  : [],
};
export const money = (value: number) => `${Number(value || 0).toLocaleString("vi-VN")} ₫`;
export const day = (value?: string) => value ? new Date(value).toLocaleDateString("vi-VN") : "—";

