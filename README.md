# Cửa hàng nông sản

Monorepo gồm `frontend/` (Next.js, React, TypeScript, Ant Design, Tailwind CSS) và `backend/` (Flask, PostgreSQL). Redis không cần để chạy MVP.

## Cài đặt và chạy local

Cần Node.js 20+, Python 3.10+ và PostgreSQL. Tạo database riêng trước khi chạy migration.

**Backend** — mở terminal tại `backend/`:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp -n .env.example .env
```

Điền `DATABASE_URL`, `SECRET_KEY`, `FRONTEND_ORIGIN` trong `backend/.env`; nếu cổng 5000 đang bận, đặt `PORT=5001`. Kiểm tra kỹ database đích rồi chạy migration **một lần**:

```bash
.venv/bin/flask --app run.py db upgrade
.venv/bin/python run.py
```

**Frontend** — mở terminal khác tại `frontend/`:

```bash
cp -n .env.example .env.local
npm install
npm run dev
```

Đặt `API_URL` trong `frontend/.env.local` bằng địa chỉ backend, ví dụ `http://127.0.0.1:5001`. Mở [http://localhost:3000](http://localhost:3000). `FRONTEND_ORIGIN` phải khớp chính xác origin đang mở (`localhost` hoặc `127.0.0.1`) để CORS hoạt động. Kiểm tra backend tại `GET /api/v1/health` (chỉ kiểm tra Flask phản hồi).

Trên database **mới, trống**, có thể nạp [dữ liệu mẫu](backend/sample_data.json) bằng `.venv/bin/flask --app run.py seed-sample` và tạo admin bằng `.venv/bin/flask --app run.py create-admin`. Không chạy seed trên dữ liệu thật. Không đưa `.env` vào Git. Chi tiết endpoint và ví dụ nằm trong [tài liệu API](backend/API.md).

## Giả định đang dùng

- Giá và tổng đơn là **tiền hàng sau giảm giá**; phí giao hàng chưa có quy tắc nên chưa cộng vào tổng.
- Đơn vị bán lấy theo sản phẩm (`kg`, `bó`, `hộp`); tồn kho tính theo lô và được giữ khi đặt đơn.
- COD là phương thức cơ bản. MoMo Test chỉ hiện khi đủ cấu hình. QR chuyển khoản SePay dùng tài khoản ngân hàng trong `backend/.env`.
- Khách bấm “Tôi đã chuyển khoản” chỉ báo đã thực hiện; đơn chỉ thành `paid` khi webhook khớp giao dịch hoặc admin đã kiểm tra sao kê và xác nhận.
- Giá đặt trước là dự kiến; khách cần duyệt giá khi hàng về trước khi xử lý đơn.

## Chưa hoàn tất

- Chưa có biểu phí giao hàng và quy trình hoàn tiền tự động; đơn đã thanh toán bị chặn hủy cho tới khi có quy trình hoàn tiền.
- Webhook SePay/MoMo cần URL HTTPS công khai và cấu hình phía nhà cung cấp để xác nhận tự động; localhost không nhận webhook trực tiếp từ Internet.
- Chưa dùng Redis. Dữ liệu mẫu và giá tham khảo không thay cho thông tin nguồn hàng, tồn kho hoặc giá bán thực tế.
# nongsanstore
