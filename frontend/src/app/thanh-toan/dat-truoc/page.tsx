import { Checkout } from "@/features/checkout/checkout";

/** Thanh toán riêng hàng đặt trước; đầu vào: nhóm preorder trong giỏ, đầu ra: đơn chờ hàng. Ví dụ: /thanh-toan/dat-truoc. */
export default function Page() { return <Checkout kind="preorder" />; }
