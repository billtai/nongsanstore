# Giữ hàng cho đơn đặt trước

- Khi nhập hoặc tăng tồn lô, hệ thống phân bổ hàng cho đơn đặt trước cũ trước. Tồn đã phân bổ không xuất hiện trong tồn bán lẻ, kể cả khi mới nhập một phần.
- Khi đủ toàn bộ sản phẩm của đơn, hệ thống gửi giá hiện tại và bắt đầu hạn xác nhận 24 giờ. Khách thấy giá so sánh và thời điểm hết hạn trong chi tiết đơn.
- Nếu khách từ chối, quản trị viên hủy, hoặc quá hạn, hàng đã giữ được trả về tồn. Các đơn đặt trước tiếp theo được phân bổ trước khi hàng mở bán lẻ.
- API tự kiểm tra hạn trước mỗi yêu cầu. Để giải phóng đúng giờ kể cả khi không có người truy cập, chạy `flask --app app expire-preorders` mỗi phút bằng bộ lập lịch của môi trường triển khai. Lệnh này đọc cùng các biến môi trường như ứng dụng.
