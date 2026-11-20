# API backend MVP

Base URL: `http://127.0.0.1:5000/api/v1`. JSON dùng UTF-8. Các route yêu cầu đăng nhập dùng header `Authorization: Bearer <access_token>`. Token có hạn 24 giờ. Lỗi thống nhất: `{"error":{"code":"invalid_input","message":"..."}}` cùng HTTP status phù hợp. Danh sách nhận `page` (mặc định 1), `limit` (mặc định 20, tối đa 100) và trả `{"items":[],"page":1,"limit":20,"total":0}`.

Tiền lưu bằng VND nguyên; lượng `kg` tối đa ba chữ số thập phân, `bó` và `hộp` là số nguyên. Đơn dùng COD. `shipping_fee_vnd: null` ở báo giá có nghĩa **chưa có quy tắc phí giao**, không phải miễn phí. Tổng đơn hiện chỉ gồm hàng trừ giảm giá; cần chốt phí giao trước khi dùng cho bán hàng thật. Quy tắc admin được hủy đơn ở `pending` hoặc `confirmed` là giả định MVP, chưa phải chính sách cửa hàng. Lượt dùng mã đã áp dụng không tự hoàn khi hủy; cần chốt chính sách nếu muốn thay đổi.

## Xác thực và kiểm tra

| Method và đường dẫn | Đầu vào | Đầu ra | Quyền |
|---|---|---|---|
| `GET /health` | Không có | `{"status":"ok"}` | Công khai |
| `POST /auth/register` | `name`, `email`, `phone`, `password` | `id`, `name`, `email`, `role` (201) | Công khai |
| `POST /auth/login` | `email`, `password` | `access_token`, `token_type`, `expires_in`, `user` | Công khai |

Ví dụ:

```http
POST /api/v1/auth/register
Content-Type: application/json

{"name":"Lan","email":"lan@example.com","phone":"0911111111","password":"matkhau123"}
```

```json
{"id":1,"name":"Lan","email":"lan@example.com","role":"customer"}
```

```http
POST /api/v1/auth/login
Content-Type: application/json

{"email":"lan@example.com","password":"matkhau123"}
```

```json
{"access_token":"<token>","token_type":"Bearer","expires_in":86400,"user":{"id":1,"name":"Lan","role":"customer"}}
```

```http
GET /api/v1/health
```

```json
{"status":"ok"}
```

## Sản phẩm và lô công khai

| Method và đường dẫn | Đầu vào | Đầu ra | Quyền |
|---|---|---|---|
| `GET /products` | Query `q`, `unit=kg|bó|hộp`, `category`, `page`, `limit` | Trang sản phẩm mới nhất trước, gồm danh mục, giá, đơn vị và tồn | Công khai |
| `GET /products/categories` | Không có | Danh mục cửa hàng, kể cả danh mục chưa có sản phẩm | Công khai |
| `GET /products/{id}` | `id` | Sản phẩm và tồn | Công khai |
| `GET /products/by-slug/{slug}` | Slug tên sản phẩm, ví dụ `ca-rot-da-lat` | Sản phẩm công khai và tồn; trả 404 nếu ẩn | Công khai |
| `GET /products/{id}/batches` | `id`, `page`, `limit` | Trang lô gồm vùng trồng, nguồn gốc, ngày thu hoạch, tồn | Công khai |

Ví dụ request/response cho từng route:

```http
GET /api/v1/products?q=c%C3%A0&unit=kg&page=1&limit=20
```

```json
{"items":[{"id":1,"slug":"ca-rot-da-lat","name":"Cà rốt Đà Lạt","description":"Cà rốt tươi","unit":"kg","price_vnd":28000,"image_url":null,"is_visible":true,"stock":"30.000"}],"page":1,"limit":20,"total":1}
```

```http
GET /api/v1/products/1
```

```json
{"id":1,"slug":"ca-rot-da-lat","name":"Cà rốt Đà Lạt","description":"Cà rốt tươi","unit":"kg","price_vnd":28000,"image_url":null,"is_visible":true,"stock":"30.000"}
```

```http
GET /api/v1/products/1/batches?page=1&limit=20
```

```json
{"items":[{"id":1,"product_id":1,"batch_code":"MAU-CA-001","growing_region":"Đà Lạt, Lâm Đồng","origin":"Lâm Đồng, Việt Nam","harvest_date":"2026-11-10","remaining_quantity":"30.000"}],"page":1,"limit":20,"total":1}
```

## Báo giá và đơn của khách

| Method và đường dẫn | Đầu vào | Đầu ra | Quyền |
|---|---|---|---|
| `POST /orders/quote` | `items: [{product_id, quantity}]`, `discount_code` tùy chọn | `subtotal_vnd`, `discount_vnd`, `total_vnd`, `shipping_fee_vnd`, `payment_method` | Khách/admin |
| `POST /orders/confirm` | `quote_id`, `recipient_name`, `recipient_phone`, `delivery_address`, `payment_method=cod` | Snapshot đơn (201); gửi lại cùng báo giá trả đúng đơn cũ (200) | Khách/admin |
| `POST /orders` | `recipient_name`, `recipient_phone`, `delivery_address`, `payment_method=cod`, `items`, `discount_code` tùy chọn | Snapshot đơn (201) | Khách/admin |
| `GET /orders` | Query `status`, `page`, `limit` | Trang đơn của tài khoản | Khách/admin |
| `GET /orders/{order_code}` | Mã đơn ngẫu nhiên, ví dụ `VN-A1B2...` | Snapshot đơn và lịch sử trạng thái | Chủ đơn |

Đơn khách hàng trả `order_code` duy nhất thay cho `id` tăng dần; API quản trị vẫn giữ `id` nội bộ. Migration `0012_order_code` tạo mã cho cả đơn cũ.

### Đặt trước sản phẩm hết hàng

Khi sản phẩm có tồn kho bằng 0, gửi dòng hàng với `preorder: true` trong `POST /orders/quote`. Báo giá trả `items[].preorder` và `is_preorder`; mã báo giá đã ký giữ nguyên lựa chọn đặt trước khi gọi `POST /orders/confirm`. Đơn có ít nhất một dòng đặt trước nhận trạng thái `preordered` (Chờ hàng) và chỉ hỗ trợ `payment_method: "cod"`. Các dòng đặt trước chưa trừ tồn kho khi tạo đơn. Quản trị chỉ chuyển đơn sang `confirmed` khi đã có đủ hàng; thao tác này giữ tồn cho các dòng đặt trước trong cùng giao dịch. Hủy đơn trả lại tồn của những dòng đã được giữ. Migration `0014_preorders` thêm cờ `order_items.is_preorder` và trạng thái đơn mới.

Ví dụ dòng báo giá: `{"product_id": 1, "quantity": "2", "preorder": true}`. Nếu hàng đã về trước khi xác nhận, API trả `409 stock_changed` để khách cập nhật giỏ hàng và đặt mua thông thường.

Ví dụ:

`POST /orders/quote` hiện trả thêm `quote_id`, `expires_in: 900`, `currency: "VND"` và `items` có tên, đơn vị, giá và thành tiền từng dòng. Mã báo giá có hạn 15 phút và gắn với tài khoản đã đăng nhập; báo giá không giữ tồn kho. Khi xác nhận, server khóa và kiểm tra lại giá, mã giảm cùng tồn. Nếu thay đổi, trả `409 quote_changed` hoặc `409 insufficient_stock`; khách cần lấy báo giá mới.

```http
POST /api/v1/orders/quote
Authorization: Bearer <token>
Content-Type: application/json

{"items":[{"product_id":1,"quantity":"2"}],"discount_code":"GIAM10"}
```

```json
{"quote_id":"<mã báo giá đã ký>","expires_in":900,"items":[{"product_id":1,"name":"Cà rốt Đà Lạt","quantity":"2","unit":"kg","unit_price_vnd":28000,"line_total_vnd":56000}],"subtotal_vnd":56000,"discount_vnd":5600,"total_vnd":50400,"shipping_fee_vnd":null,"payment_method":"cod","currency":"VND"}
```

```http
POST /api/v1/orders
Authorization: Bearer <token>
Content-Type: application/json

{"recipient_name":"Lan","recipient_phone":"0911111111","delivery_address":"Đà Lạt, Lâm Đồng","payment_method":"cod","items":[{"product_id":1,"quantity":"2"}],"discount_code":"GIAM10"}
```

Ví dụ xác nhận báo giá từ giao diện:

```http
POST /api/v1/orders/confirm
Authorization: Bearer <token>
Content-Type: application/json

{"quote_id":"<quote_id từ báo giá>","recipient_name":"Lan","recipient_phone":"0911111111","delivery_address":"Đà Lạt, Lâm Đồng","payment_method":"cod"}
```

Response là snapshot đơn như `POST /orders` bên dưới. `quote_id` chỉ tạo được một đơn; gửi lại cùng mã trả đơn đã tạo mà không trừ tồn lần nữa.

```json
{"order_code":"VN-A1B2C3D4E5F60718293A4B5C","recipient_name":"Lan","recipient_phone":"0911111111","delivery_address":"Đà Lạt, Lâm Đồng","status":"pending","payment_method":"cod","subtotal_vnd":56000,"discount_vnd":5600,"total_vnd":50400,"discount_code":"GIAM10","created_at":"2026-11-17T03:00:00+00:00","items":[{"product_id":1,"product_name":"Cà rốt Đà Lạt","unit":"kg","quantity":"2.000","unit_price_vnd":28000,"line_total_vnd":56000}],"history":[{"from_status":null,"to_status":"pending","reason":null,"created_at":"2026-11-17T03:00:00+00:00"}]}
```

```http
GET /api/v1/orders?status=pending&page=1&limit=20
Authorization: Bearer <token>
```

```json
{"items":[{"order_code":"VN-A1B2C3D4E5F60718293A4B5C","status":"pending","items":[{"product_id":1,"unit_price_vnd":28000}]}],"page":1,"limit":20,"total":1}
```

`items` trong ví dụ danh sách trên được rút gọn để dễ đọc; response thật chứa đầy đủ các trường như ví dụ tạo đơn.

```http
GET /api/v1/orders/VN-A1B2C3D4E5F60718293A4B5C
Authorization: Bearer <token>
```

Response có cùng cấu trúc đầy đủ với ví dụ `POST /orders`.

## Thanh toán MoMo Test

Các endpoint bên dưới dùng cổng `https://test-payment.momo.vn` và chỉ hiện MoMo khi đủ biến môi trường trong `backend/.env`. Cần áp dụng migration `0008_momo_test` thủ công trước khi dùng. Ví dụ đầu vào/đầu ra chỉ minh họa cấu trúc; `pay_url` và `quote_id` thực tế do server tạo.

| Method và đường dẫn | Đầu vào | Đầu ra | Quyền |
|---|---|---|---|
| `GET /orders/payment-methods` | Không có | `{ "items": ["cod", "momo"] }` khi đã cấu hình | Công khai |
| `POST /orders/confirm` | Báo giá, người nhận, `payment_method: "momo"` | Đơn gồm `payment_status: "pending"`, `pay_url` | Khách đăng nhập |
| `POST /orders/momo/ipn` | JSON kết quả và chữ ký HMAC do MoMo gửi | HTTP 204 | MoMo, xác thực chữ ký |
| `GET /orders/{order_code}/momo/status` | Mã đơn | Trạng thái thanh toán và đơn | Chủ đơn |
| `POST /orders/{order_code}/momo/retry` | Mã đơn đang chờ | Đơn và `pay_url` của cùng giao dịch | Chủ đơn |

```http
POST /api/v1/orders/confirm
Authorization: Bearer <access_token>
Content-Type: application/json

{"quote_id":"<quote_id>","recipient_name":"Nguyễn An","recipient_phone":"0900000000","delivery_address":"Đà Lạt, Lâm Đồng","payment_method":"momo"}
```

```json
{"order_code":"VN-A1B2C3D4E5F60718293A4B5C","payment_method":"momo","payment_status":"pending","pay_url":"https://test-payment.momo.vn/...","total_vnd":100000}
```

Nếu MoMo Test chưa tạo được liên kết, API trả `202` cùng đơn đã tạo và `payment_error`; gọi `POST /orders/{order_code}/momo/retry` để dùng lại mã giao dịch, tránh giữ tồn kho cho nhiều đơn trùng. IPN chỉ cập nhật `payment_status` sau khi kiểm tra chữ ký, `partnerCode`, `orderId`, `requestId` và `amount`. MoMo thất bại giữ đơn để admin hủy và hoàn tồn; ứng dụng chưa có API hoàn tiền.

## Cổng thanh toán SePay Sandbox

Prefix các đường dẫn là `/api/v1`. Cần migration `0010_sepay_bank_transfer`, Merchant ID và Merchant Secret Key để mở trang QR Sandbox. **IPN Secret Key riêng** cần cho bước xác nhận đơn. Chưa có URL công khai thì SePay không gửi IPN về local.

| Method và đường dẫn | Đầu vào | Đầu ra | Quyền |
| --- | --- | --- | --- |
| `GET /orders/payment-methods` | Không có | `{ "items": ["cod", "sepay"] }` nếu chỉ SePay được cấu hình | Công khai |
| `POST /orders/confirm` | Báo giá, người nhận, `payment_method: "sepay"` | Đơn `pending` và `sepay_checkout` đã ký | Khách đăng nhập |
| `GET /orders/{order_code}` | Mã đơn | Đơn và form thanh toán nếu đang chờ | Chủ đơn |
| `POST /orders/sepay/ipn` | JSON IPN, header `X-Secret-Key` | `{ "success": true, "matched": true/false }` | SePay, khóa IPN |

Ví dụ xác nhận đơn (kèm Bearer token của khách):

```json
{"quote_id":"<quote_id>","recipient_name":"Nguyễn An","recipient_phone":"0900000000","delivery_address":"Đà Lạt, Lâm Đồng","payment_method":"sepay"}
```

Ví dụ phần thanh toán trong phản hồi (signature là giá trị được backend ký):

```json
{"payment_status":"pending","sepay_checkout":{"action":"https://pay-sandbox.sepay.vn/v1/checkout/init","fields":{"order_amount":"100000","merchant":"SP-TEST-...","currency":"VND","operation":"PURCHASE","order_description":"Thanh toan don hang 12","order_invoice_number":"NS12...","payment_method":"BANK_TRANSFER","signature":"<chữ ký>"}}}
```

Trình duyệt gửi các `fields` theo thứ tự trong phản hồi bằng form `POST` tới `action`. Ví dụ IPN xác nhận:

```json
{"notification_type":"ORDER_PAID","order":{"order_invoice_number":"NS12...","order_status":"CAPTURED","order_currency":"VND","order_amount":"100000.00"},"transaction":{"id":"384c66dd-41e6-4316-a544-b4141682595c","transaction_type":"PAYMENT","transaction_status":"APPROVED","transaction_amount":"100000","transaction_currency":"VND"}}
```

IPN đúng khóa, invoice, trạng thái và số tiền trả `200 {"success":true,"matched":true}` và đổi `payment_status` thành `paid`. Sai khóa trả `401`. IPN trùng không ghi nhận thêm lần nữa.

## QR chuyển khoản trực tiếp

Luồng mới dùng `payment_method: "sepay_bank"`. Cần migration `0011_sepay_bank_qr` và ba biến tài khoản nhận `SEPAY_BANK_CODE`, `SEPAY_ACCOUNT_NUMBER`, `SEPAY_ACCOUNT_NAME`. QR được tạo từ [URL VietQR của SePay](https://developer.sepay.vn/vi/sepay-webhooks/tao-qr-va-form-thanh-toan); Merchant Secret Key của Cổng thanh toán không dùng trong luồng này.

| Method và đường dẫn | Đầu vào | Đầu ra | Quyền |
| --- | --- | --- | --- |
| `GET /orders/payment-methods` | Không có | `{ "items": ["cod", "sepay_bank"] }` khi cấu hình tài khoản nhận | Công khai |
| `POST /orders/confirm` | `quote_id`, người nhận, `payment_method: "sepay_bank"` | Đơn `pending` và `bank_transfer` | Khách đăng nhập |
| `GET /orders/{order_code}` | Mã đơn | Đơn và `bank_transfer` gồm QR URL | Chủ đơn |
| `POST /orders/{order_code}/sepay/bank-transfer-reported` | Mã đơn, không cần body | Đơn có `bank_transfer_reported_at`; `payment_status` vẫn `pending` | Khách là chủ đơn |
| `POST /orders/sepay/bank-webhook` | JSON giao dịch và `Authorization: Apikey <key>` | `{ "success": true, "matched": true/false }` | SePay, API Key |
| `POST /admin/orders/{id}/confirm-bank-payment` | ID đơn QR, không cần body; chỉ gọi sau khi đối chiếu sao kê | Đơn có `payment_status: "paid"`, `bank_payment_confirmed_at`, `bank_payment_confirmed_by` | Admin |

Ví dụ khách báo đã chuyển khoản: `POST /api/v1/orders/VN-ABC/sepay/bank-transfer-reported` với Bearer token của chủ đơn và body rỗng trả `200` cùng dữ liệu đơn, gồm `"bank_transfer_reported_at": "2026-11-18T..."` và `"payment_status": "pending"`. Gửi lại không đổi thời điểm đã báo. Webhook ngân hàng hợp lệ vẫn là nguồn xác nhận tự động để đổi sang `paid`.

Ví dụ admin đã thấy khoản tiền trong sao kê: `POST /api/v1/admin/orders/12/confirm-bank-payment` với Bearer token admin và body rỗng trả `200` cùng đơn có `"payment_status": "paid"`, `"bank_payment_confirmed_by": 1`. Đơn QR chưa nhận tiền vẫn phải giữ `pending`; thao tác này không tự xác minh giao dịch ngân hàng.

Ví dụ dữ liệu chuyển khoản trong phản hồi:

```json
{"payment_method":"sepay_bank","payment_status":"pending","bank_transfer":{"bank_code":"ACB","account_number":"22810217","account_name":"TỐNG THÀNH TÀI","amount_vnd":40000,"payment_code":"NS12A1B2C3D4E5F60708","qr_url":"https://vietqr.app/img?acc=22810217&bank=ACB&amount=40000&des=NS12A1B2C3D4E5F60708&template=compact"}}
```

Ví dụ webhook tiền vào (dữ liệu minh họa):

```json
{"id":92704,"accountNumber":"22810217","content":"NS12A1B2C3D4E5F60708","transferType":"in","transferAmount":40000}
```

Đúng API Key, tài khoản, mã, số tiền và giao dịch chưa dùng: `200 {"success":true,"matched":true}`. Sai mã hoặc số tiền: `200 {"success":true,"matched":false}` để đối soát thủ công. Sai API Key: `401`.

### Ẩn lô và xem đơn đã dùng mã giảm giá

- `PATCH /api/v1/admin/batches/:id` với `{"is_visible":false}` ẩn lô; `true` hiện lại. Lô ẩn vẫn giữ lịch sử và số lượng nhưng không được tính vào tồn có thể bán, không được cấp cho đơn mới.
- `GET /api/v1/admin/batches?visible=true|false&page=1&limit=10` lọc lô theo trạng thái hiển thị tại database.
- `PATCH /api/v1/admin/products/:id` với `{"is_visible":false|true}` ẩn/hiện sản phẩm; chỉ admin được gọi.
- `PATCH /api/v1/admin/discounts/:id` với `{"is_active":false|true}` tắt/bật mã giảm giá; mã đã tắt không dùng được cho đơn mới.
- `GET /api/v1/admin/discounts/:id/orders?page=1&limit=10` trả các đơn đã áp dụng mã, gồm mã đơn, người nhận, số tiền giảm, tổng tiền, trạng thái; chỉ admin được gọi và phân trang tại database.
- `GET /api/v1/admin/overview?aging_page=1` trả `counts` gồm `today`, `previous_day`, `month`, `previous_month`, `year`, `previous_year`, `monthly` gồm 12 tháng gần nhất, và `aging_batches` gồm tổng số cùng một trang 10 lô nhập quá 72 giờ vẫn còn tồn (kể cả lô ẩn). Mọi kỳ dùng múi giờ `Asia/Ho_Chi_Minh`, tính tất cả đơn đã tạo ở mọi trạng thái; chỉ admin được gọi và số liệu được tổng hợp/phân trang tại database.
- `GET /api/v1/admin/overview/daily-revenue?page=1&limit=10&from_date=2026-11-01&to_date=2026-11-30` trả các dòng doanh thu theo ngày tạo đơn (múi giờ `Asia/Ho_Chi_Minh`), gồm `day`, `order_count`, `total_vnd`; `from_date` và `to_date` tùy chọn, bao gồm cả hai ngày. Chỉ tính đơn có trạng thái `completed` (Đã giao), sắp ngày mới nhất trước và phân trang tại database. Chỉ admin được gọi.
  Mã đã được dùng trong đơn có thể tắt/bật nhưng không thể đổi tên, để lịch sử đơn vẫn gắn đúng mã.
