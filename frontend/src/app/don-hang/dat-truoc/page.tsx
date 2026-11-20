import { OrderHistory } from "@/features/orders/history";

/** Hiển thị mục đơn đặt trước của khách; đầu vào: phiên hiện tại, đầu ra: lịch sử đặt trước. Ví dụ: /don-hang/dat-truoc. */
export default function Page() { return <OrderHistory kind="preorder" />; }
