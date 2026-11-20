"use client";

import { Alert, Button, Divider, Popconfirm, Steps, Tag } from "antd";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { BrandLoading } from "@/components/shared/brand-loading";
import { ErrorState } from "@/components/shared/error-state";
import { orderStatusLabels } from "@/features/orders/status";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import type { Order } from "@/types/store";

/** Xem đơn thuộc tài khoản theo mã công khai. Đầu vào: mã URL và phiên đăng nhập; đầu ra: hàng hóa, thanh toán, giao nhận và lịch sử. Ví dụ: /don-hang/VN-A1B2. */
export function OrderDetail() {
  const code                = useParams<{ id: string }>().id;
  const [order, setOrder]   = useState<Order>();
  const [error, setError]   = useState("");
  const [reload, setReload] = useState(0);
  const [retrying, setRetrying] = useState(false);
  const [reportingTransfer, setReportingTransfer] = useState(false);
  const [transferError, setTransferError]         = useState("");
  const [priceSaving, setPriceSaving] = useState(false);
  const [priceError, setPriceError]   = useState("");

  /** Gửi quyết định của khách; đầu vào: approval hoặc cancel, đầu ra: đơn mới từ API. Ví dụ: cancel hoàn hàng đã giữ và hiện lại tồn bán. */
  async function decidePrice(decision: "approval" | "cancel") {
    setPriceSaving(true);
    setPriceError("");
    try {
      const endpoint = decision === "cancel" ? "cancel" : "price-approval";
      const updated  = await api<Order>(`/orders/${encodeURIComponent(code)}/${endpoint}`, { method: "POST" });
      setOrder(updated);
    } catch (reason) {
      setPriceError(reason instanceof Error ? reason.message : "Không thể cập nhật đơn. Vui lòng thử lại.");
    } finally {
      setPriceSaving(false);
    }
  }

  /** Lấy lại pay_url của cùng đơn; đầu vào mã đơn đang chờ, đầu ra chuyển tới MoMo Test. Ví dụ: thử lại không tạo thêm đơn. */
  async function retryMomo() {
    setRetrying(true);
    try {
      const result = await api<Order>(`/orders/${encodeURIComponent(code)}/momo/retry`, { method: "POST" });
      if (result.pay_url?.startsWith("https://test-payment.momo.vn/")) window.location.assign(result.pay_url);
      else setError("MoMo Test chưa trả liên kết thanh toán.");
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể kết nối MoMo Test.");
    } finally {
      setRetrying(false);
    }
  }

  /** Báo đã chuyển khoản; đầu vào mã đơn trên URL, đầu ra đơn có thời điểm báo; ví dụ: khách quét QR rồi bấm xác nhận. */
  async function reportTransfer() {
    setReportingTransfer(true);
    setTransferError("");
    try {
      const updated = await api<Order>(`/orders/${encodeURIComponent(code)}/sepay/bank-transfer-reported`, { method: "POST" });
      setOrder(updated);
    } catch (reason) {
      setTransferError(reason instanceof Error ? reason.message : "Không thể ghi nhận thông báo chuyển khoản.");
    } finally {
      setReportingTransfer(false);
    }
  }

  useEffect(() => {
    setOrder(undefined);
    setError("");
    api<Order>(`/orders/${encodeURIComponent(code)}`).then(setOrder).catch(error => setError(error.message));
  }, [code, reload]);

  return <Shell>
    <div className="mb-6 text-sm text-stone-500"><Link href="/">Trang chủ</Link> / <Link href={order?.is_preorder ? "/don-hang/dat-truoc" : "/don-hang/lich-su"}>{order?.is_preorder ? "Đơn đặt trước của tôi" : "Đơn hàng của tôi"}</Link> / <span className="text-forest">Đơn {code}</span></div>
    {error ? <ErrorState error={error} retry={() => setReload(value => value + 1)} /> : !order ? <BrandLoading label="Đang tải chi tiết đơn hàng..." /> : <>
      <div className="mb-7 flex flex-wrap items-start justify-between gap-4"><div><p className="eyebrow">{order.is_preorder ? "Chi tiết đơn đặt trước" : "Chi tiết đơn hàng"}</p><h1 className="mt-2 break-all text-3xl font-black text-forest">Đơn {order.order_code}</h1><p className="mt-2 text-sm text-stone-500">Đặt lúc {new Date(order.created_at).toLocaleString("vi-VN")}</p></div><div className="flex gap-2">{order.is_preorder && <Tag className="px-3 py-1 text-sm" color="blue">Đặt trước</Tag>}<Tag className="px-3 py-1 text-sm" color={order.status === "cancelled" ? "default" : order.status === "completed" ? "green" : "gold"}>{orderStatusLabels[order.status] || order.status}</Tag></div></div>
      {order.status === "preordered" && <Alert className="mb-6" type="warning" showIcon message="Đơn đặt trước đang chờ hàng" description="Giá lúc đặt là giá dự kiến. Khi hàng về, cửa hàng sẽ gửi giá mới để bạn xem và xác nhận trước khi xử lý đơn." />}
      {order.status === "preordered" && <div className="mb-6"><Popconfirm title="Hủy đơn đặt trước này?" description="Phần hàng đã giữ sẽ được trả lại kho." okText="Hủy đơn" cancelText="Giữ đơn" onConfirm={() => void decidePrice("cancel")}><Button danger loading={priceSaving}>Hủy đơn đặt trước</Button></Popconfirm>{priceError && <Alert className="mt-3" type="error" showIcon message={priceError} />}</div>}
      {order.is_preorder && order.status === "cancelled" && <Alert className="mb-6" type="success" showIcon message="Đơn đặt trước đã hủy" description="Phần hàng đã giữ đã được trả lại kho hoặc chuyển cho đơn đặt trước đang chờ tiếp theo." />}
      {order.status === "awaiting_price_approval" && order.price_approval_deadline && <Alert className="mb-6" type="warning" showIcon message="Hàng đã được giữ cho bạn" description={`Vui lòng xác nhận giá trước ${new Date(order.price_approval_deadline).toLocaleString("vi-VN")}. Sau thời hạn này, đơn sẽ tự hủy và hàng được mở bán lại.`} />}
      {order.is_preorder && <section className="mb-6 rounded-3xl border border-amber-200 bg-amber-50 p-5 md:p-7"><h2 className="text-xl font-black text-forest">So sánh giá đặt trước</h2><p className="mt-2 text-sm text-stone-600">{order.proposed_total_vnd === null ? "Giá lúc đặt là dự kiến. Cửa hàng sẽ cập nhật giá khi có hàng." : order.price_approved_at ? "Bạn đã chấp thuận giá khi hàng về." : "Giá mới đã được gửi để bạn quyết định. Ưu đãi theo số tiền giảm lúc đặt vẫn được giữ, tối đa bằng tiền hàng mới."}</p><div className="mt-5 space-y-3">{order.items.map(item => <div key={item.product_id} className="rounded-2xl bg-white p-4"><strong>{item.product_name}</strong><span className="ml-2 text-sm text-stone-500">{item.quantity} {item.unit}</span><div className="mt-2 grid gap-2 text-sm sm:grid-cols-2"><p>Giá lúc đặt: <b>{money(item.initial_unit_price_vnd ?? item.unit_price_vnd)} / {item.unit}</b></p><p>Giá khi hàng về: <b className={item.proposed_unit_price_vnd !== null && item.proposed_unit_price_vnd > (item.initial_unit_price_vnd ?? item.unit_price_vnd) ? "text-red-700" : "text-forest"}>{item.proposed_unit_price_vnd === null ? "Chưa cập nhật" : `${money(item.proposed_unit_price_vnd)} / ${item.unit}`}</b></p></div>{item.proposed_unit_price_vnd !== null && item.proposed_unit_price_vnd !== (item.initial_unit_price_vnd ?? item.unit_price_vnd) && <p className="mt-1 text-sm font-semibold">{item.proposed_unit_price_vnd > (item.initial_unit_price_vnd ?? item.unit_price_vnd) ? "Tăng" : "Giảm"} {money(Math.abs(item.proposed_unit_price_vnd - (item.initial_unit_price_vnd ?? item.unit_price_vnd)))} / {item.unit}</p>}</div>)}</div><div className="mt-5 grid gap-2 border-t border-amber-200 pt-4 text-sm sm:grid-cols-2"><p>Tổng dự kiến lúc đặt: <b>{money(order.initial_total_vnd ?? order.total_vnd)}</b></p><p>Tổng khi hàng về: <b className="text-forest">{order.proposed_total_vnd === null ? "Chưa cập nhật" : money(order.proposed_total_vnd)}</b></p></div>{order.proposed_total_vnd !== null && order.initial_total_vnd !== null && order.proposed_total_vnd !== order.initial_total_vnd && <p className="mt-2 font-bold text-forest">Chênh lệch: {order.proposed_total_vnd > order.initial_total_vnd ? "+" : "−"}{money(Math.abs(order.proposed_total_vnd - order.initial_total_vnd))}</p>}{order.status === "awaiting_price_approval" && <><div className="mt-5 flex flex-wrap gap-3"><Button type="primary" loading={priceSaving} onClick={() => void decidePrice("approval")}>Đồng ý giá mới</Button><Popconfirm title="Từ chối giá và hủy đơn đặt trước?" okText="Hủy đơn" cancelText="Quay lại" onConfirm={() => void decidePrice("cancel")}><Button danger disabled={priceSaving}>Không đồng ý, hủy đơn</Button></Popconfirm></div>{priceError && <Alert className="mt-4" type="error" showIcon message={priceError} />}</>}</section>}
      <div className="grid gap-6 lg:grid-cols-[1.35fr_.65fr]"><div className="space-y-6">{order.payment_method === "momo" && <Alert type={order.payment_status === "paid" ? "success" : order.payment_status === "failed" ? "error" : "info"} showIcon message={order.payment_status === "paid" ? "MoMo Test đã xác nhận thanh toán" : order.payment_status === "failed" ? "Thanh toán MoMo Test thất bại" : "Đang chờ MoMo Test xác nhận thanh toán"} description={<><Button size="small" onClick={() => setReload(value => value + 1)}>Cập nhật trạng thái</Button>{order.payment_status === "pending" && order.pay_url && <Button size="small" href={order.pay_url} className="ml-2">Đến MoMo Test</Button>}{order.payment_status === "pending" && !order.pay_url && <Button size="small" loading={retrying} onClick={retryMomo} className="ml-2">Tạo lại liên kết</Button>}</>} />}
      {order.payment_method === "sepay_bank" && order.bank_transfer && <section className="rounded-3xl border border-stone-100 bg-white p-5 shadow-sm md:p-7"><h2 className="text-xl font-black text-forest">Quét QR chuyển khoản</h2><Alert className="mt-4" type={order.payment_status === "paid" ? "success" : "info"} showIcon message={order.payment_status === "paid" ? "Đã xác nhận thanh toán" : "Đang chờ ngân hàng xác nhận"} description={<Button size="small" className="mt-2" onClick={() => setReload(value => value + 1)}>Cập nhật trạng thái</Button>} />{order.payment_status === "pending" && <div className="mt-5 grid gap-5 sm:grid-cols-[220px_1fr]"><img src={order.bank_transfer.qr_url} alt="QR chuyển khoản ngân hàng" width={220} height={220} className="h-[220px] w-[220px] object-contain" /><dl className="space-y-2 text-sm"><div><dt className="text-stone-500">Ngân hàng</dt><dd className="font-semibold">{order.bank_transfer.bank_code}</dd></div><div><dt className="text-stone-500">Số tài khoản</dt><dd className="font-semibold">{order.bank_transfer.account_number}</dd></div><div><dt className="text-stone-500">Chủ tài khoản</dt><dd className="font-semibold">{order.bank_transfer.account_name}</dd></div><div><dt className="text-stone-500">Số tiền</dt><dd className="font-semibold">{money(order.bank_transfer.amount_vnd)}</dd></div><div><dt className="text-stone-500">Nội dung chuyển khoản</dt><dd className="font-bold text-forest">{order.bank_transfer.payment_code}</dd></div><Button size="small" onClick={() => navigator.clipboard.writeText(order.bank_transfer!.payment_code)}>Sao chép nội dung</Button></dl></div>}{order.payment_status === "pending" && !order.bank_transfer_reported_at && <Button type="primary" className="mt-5" loading={reportingTransfer} onClick={() => void reportTransfer()}>Tôi đã chuyển khoản</Button>}{order.payment_status === "pending" && order.bank_transfer_reported_at && <Alert className="mt-5" type="warning" showIcon message="Đã ghi nhận bạn báo chuyển khoản" description="Đơn vẫn đang chờ đối soát. Cửa hàng sẽ kiểm tra nếu ngân hàng gửi thông báo chậm." />}{transferError && <Alert className="mt-3" type="error" showIcon message={transferError} />}<p className="mt-4 text-xs text-stone-500">Chuyển đúng số tiền và nội dung để hệ thống đối chiếu. Phí giao hàng chưa được xác định.</p></section>}
      {order.payment_method === "sepay" && <section className="rounded-3xl border border-stone-100 bg-white p-5 shadow-sm md:p-7"><h2 className="text-xl font-black text-forest">Thanh toán SePay Sandbox</h2><Alert className="mt-4" type={order.payment_status === "paid" ? "success" : "info"} showIcon message={order.payment_status === "paid" ? "Đã xác nhận thanh toán" : "Đang chờ SePay xác nhận giao dịch"} description={<Button size="small" className="mt-2" onClick={() => setReload(value => value + 1)}>Cập nhật trạng thái</Button>} />{order.payment_status === "pending" && order.sepay_checkout?.action === "https://pay-sandbox.sepay.vn/v1/checkout/init" && <form method="POST" action={order.sepay_checkout.action} className="mt-4">{Object.entries(order.sepay_checkout.fields).map(([name, value]) => <input key={name} type="hidden" name={name} value={value} />)}<Button type="primary" htmlType="submit">Đến SePay Sandbox để thanh toán</Button></form>}<p className="mt-4 text-xs text-stone-500">Cổng thanh toán thử nghiệm. Phí giao hàng chưa được xác định.</p></section>}
      <section className="rounded-3xl border border-stone-100 bg-white p-5 shadow-sm md:p-7"><h2 className="mb-5 text-xl font-black text-forest">Sản phẩm đã đặt</h2><div className="divide-y divide-stone-100">{order.items.map((item, index) => <div key={`${item.product_id}-${index}`} className="flex flex-wrap justify-between gap-4 py-4 first:pt-0 last:pb-0"><div><strong className="text-stone-900">{item.product_name}</strong>{item.is_preorder && <Tag className="ml-2" color="gold">Đặt trước</Tag>}<p className="mt-1 text-sm text-stone-500">{item.quantity} {item.unit} × {money(item.unit_price_vnd)} / {item.unit}</p></div><strong className="text-forest">{money(item.line_total_vnd)}</strong></div>)}</div></section><section className="rounded-3xl border border-stone-100 bg-white p-5 shadow-sm md:p-7"><h2 className="mb-5 text-xl font-black text-forest">Thông tin giao hàng</h2><dl className="grid gap-x-4 gap-y-3 text-sm sm:grid-cols-[150px_1fr]"><dt className="text-stone-500">Người nhận</dt><dd className="font-semibold">{order.recipient_name}</dd><dt className="text-stone-500">Số điện thoại</dt><dd>{order.recipient_phone}</dd><dt>Địa chỉ</dt><dd>{order.delivery_address}</dd><dt className="text-stone-500">Thanh toán</dt><dd>{order.payment_method === "cod" ? "Thanh toán khi nhận hàng" : order.payment_method === "momo" ? "Ví MoMo Test" : "Chuyển khoản SePay"}</dd></dl></section>{order.history?.length > 0 && <section className="rounded-3xl border border-stone-100 bg-white p-5 shadow-sm md:p-7"><h2 className="mb-5 text-xl font-black text-forest">Quá trình xử lý</h2><Steps direction="vertical" size="small" current={order.history.length - 1} items={order.history.map(event => ({ title: orderStatusLabels[event.to_status] || event.to_status, description: `${new Date(event.created_at).toLocaleString("vi-VN")}${event.reason ? ` · ${event.reason}` : ""}` }))} /></section>}</div>
        <aside className="h-fit rounded-3xl border border-stone-100 bg-white p-5 shadow-sm md:p-7"><h2 className="text-xl font-black text-forest">Tổng kết đơn hàng</h2><div className="mt-6 space-y-4 text-sm"><p className="flex justify-between gap-3"><span>Tiền hàng</span><span>{money(order.status === "awaiting_price_approval" ? order.proposed_subtotal_vnd ?? order.subtotal_vnd : order.subtotal_vnd)}</span></p><p className="flex justify-between gap-3"><span>Giảm giá{order.discount_code ? ` (${order.discount_code})` : ""}</span><span>−{money(order.status === "awaiting_price_approval" ? order.proposed_discount_vnd ?? order.discount_vnd : order.discount_vnd)}</span></p><p className="text-xs text-stone-500">Phí giao hàng chưa được xác định trong đơn này.</p></div><Divider /><p className="flex items-center justify-between gap-3 text-lg font-black text-forest"><span>{order.status === "preordered" ? "Tổng tiền dự kiến" : order.status === "awaiting_price_approval" ? "Tổng tiền đề xuất" : "Tổng tiền hàng"}</span><span>{money(order.status === "awaiting_price_approval" ? order.proposed_total_vnd ?? order.total_vnd : order.total_vnd)}</span></p><Link href={order.is_preorder ? "/don-hang/dat-truoc" : "/don-hang/lich-su"}><Button className="mt-7 w-full">← Quay lại {order.is_preorder ? "đơn đặt trước" : "đơn hàng"} của tôi</Button></Link></aside></div>
    </>}
  </Shell>;
}
