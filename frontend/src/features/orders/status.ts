/** Nhãn trạng thái từ API. Đầu vào: mã trạng thái; đầu ra: nhãn tiếng Việt. Ví dụ: pending -> Chờ xác nhận. */
export const orderStatusLabels: Record<string, string> = {
  preordered : "Chờ hàng",
  awaiting_price_approval : "Chờ bạn duyệt giá",
  pending    : "Chờ xác nhận",
  confirmed  : "Đã xác nhận",
  preparing  : "Đang chuẩn bị",
  delivering : "Đang giao",
  completed  : "Hoàn thành",
  cancelled  : "Đã hủy",
};
