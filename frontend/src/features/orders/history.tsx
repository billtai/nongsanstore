"use client";

import { Button, DatePicker, Empty, Input, Pagination, Tag } from "antd";
import dayjs from "dayjs";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { BrandLoading } from "@/components/shared/brand-loading";
import { ErrorState } from "@/components/shared/error-state";
import { orderStatusLabels } from "@/features/orders/status";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import type { Order } from "@/types/store";

/** Liệt kê đơn theo loại của tài khoản. Đầu vào: kind và phiên đăng nhập; đầu ra: thẻ đơn mở chi tiết. Ví dụ: kind=preorder hiển thị /don-hang/dat-truoc. */
export function OrderHistory({ kind = "regular" }: { kind?: "regular" | "preorder" }) {
  const [activeKind, setActiveKind] = useState<"regular" | "preorder">(kind);
  const [orders, setOrders] = useState<Order[]>();
  const [error, setError]   = useState("");
  const [reload, setReload] = useState(0);
  const [page, setPage]     = useState(1);
  const [total, setTotal]   = useState(0);
  const [query, setQuery]   = useState("");
  const [search, setSearch] = useState("");
  const [date, setDate]     = useState("");
  const [expanded, setExpanded] = useState<string[]>([]);

  useEffect(() => {
    // Đồng bộ tab với lịch sử trình duyệt; đầu vào: tham số loai trên URL,
    // đầu ra: tab đang xem. Ví dụ: quay lại ?loai=dat-truoc mở danh sách đặt trước.
    const syncKind = () => setActiveKind(new URLSearchParams(window.location.search).get("loai") === "dat-truoc" ? "preorder" : kind);
    syncKind();
    window.addEventListener("popstate", syncKind);
    return () => window.removeEventListener("popstate", syncKind);
  }, [kind]);

  /** Đổi loại đơn tại chỗ; đầu vào: tab được bấm, đầu ra: URL và danh sách tương ứng. Ví dụ: bấm Đơn đặt trước không dựng lại thanh điều hướng. */
  function changeKind(nextKind: "regular" | "preorder") {
    if (nextKind === activeKind) return;
    const url = new URL(window.location.href);
    if (nextKind === "preorder") url.searchParams.set("loai", "dat-truoc");
    else url.searchParams.set("loai", "don-hang");
    window.history.pushState(null, "", url);
    setOrders(undefined);
    setActiveKind(nextKind);
    setPage(1);
  }

  useEffect(() => {
    let active = true;
    setError("");
    setOrders(undefined);
    const params = new URLSearchParams({ kind: activeKind, page: String(page), limit: "10" });
    if (search) params.set("q", search);
    if (date) params.set("date", date);
    api<{ items: Order[]; total: number }>(`/orders?${params}`)
      .then(data => { if (active) { setOrders(data.items); setTotal(data.total); } })
      .catch(error => { if (active) setError(error.message); });
    return () => { active = false; };
  }, [activeKind, page, search, date, reload]);

  return <Shell>
    <div className="mb-7"><p className="eyebrow">Theo dõi đơn của bạn</p><h1 className="mt-2 text-3xl font-black text-forest">Đơn hàng của tôi</h1><p className="mt-2 text-sm text-stone-500">Chọn một đơn để xem sản phẩm, tiền hàng và quá trình xử lý.</p><nav aria-label="Loại đơn hàng" className="mt-5 inline-flex max-w-full gap-1 rounded-2xl border border-green-100 bg-[#edf3e7] p-1.5 shadow-sm"><button type="button" onClick={() => changeKind("regular")} aria-current={activeKind === "regular" ? "page" : undefined} className={`rounded-xl px-4 py-2.5 text-sm font-bold transition-colors sm:px-6 ${activeKind === "regular" ? "bg-forest text-white shadow-sm" : "text-forest hover:bg-white/80"}`}>Đơn hàng</button><button type="button" onClick={() => changeKind("preorder")} aria-current={activeKind === "preorder" ? "page" : undefined} className={`rounded-xl px-4 py-2.5 text-sm font-bold transition-colors sm:px-6 ${activeKind === "preorder" ? "bg-forest text-white shadow-sm" : "text-forest hover:bg-white/80"}`}>Đơn đặt trước</button></nav></div>
    <div className="mb-6 flex flex-wrap gap-3"><Input.Search className="w-full sm:max-w-xs" placeholder="Tìm theo tên sản phẩm" value={query} onChange={event => setQuery(event.target.value)} onSearch={value => { setSearch(value.trim()); setPage(1); }} allowClear enterButton="Tìm" /><DatePicker className="w-full sm:w-48" placeholder="Ngày đặt hàng" format="DD/MM/YYYY" value={date ? dayjs(date) : null} onChange={value => { setDate(value?.format("YYYY-MM-DD") || ""); setPage(1); }} allowClear /></div>
    <div className="min-h-[50vh]" aria-busy={!orders && !error}>
    {error ? <ErrorState error={error} retry={() => setReload(value => value + 1)} /> : !orders ? <BrandLoading label="Đang tải đơn hàng của bạn..." /> : !orders.length ? <Empty description={activeKind === "preorder" ? "Bạn chưa có đơn đặt trước" : "Bạn chưa có đơn hàng"}><Link href="/san-pham"><Button type="primary">Khám phá sản phẩm</Button></Link></Empty> : <>
      <div className="space-y-4">{orders.map(order => {
        const isExpanded = expanded.includes(order.order_code);
        const visibleItems = isExpanded ? order.items : order.items.slice(0, 1);
        return <article key={order.order_code} className="relative rounded-2xl border border-stone-100 bg-white p-5 shadow-sm transition hover:border-green-200 hover:shadow-md md:p-6">
          <Link href={`/don-hang/${order.order_code}`} className="absolute inset-0 rounded-2xl" aria-label={`Xem chi tiết đơn hàng ${order.order_code}`} />
          <div className="pointer-events-none relative flex flex-wrap items-start justify-between gap-3 border-b border-stone-100 pb-4">
            <div><div className="flex flex-wrap items-center gap-2"><strong className="text-base text-forest sm:text-lg">{activeKind === "preorder" ? "Đặt trước" : "Đơn"} {order.order_code}</strong><Tag color={order.status === "cancelled" ? "default" : order.status === "completed" ? "green" : "gold"}>{orderStatusLabels[order.status] || order.status}</Tag></div><p className="mt-1 text-sm text-stone-500">Đặt ngày {new Date(order.created_at).toLocaleDateString("vi-VN")}</p></div>
            <span className="text-sm font-semibold text-olive">Xem chi tiết →</span>
          </div>
          <div className="pointer-events-none relative divide-y divide-stone-100">{visibleItems.map((item, index) => <div key={`${item.product_id}-${index}`} className="flex items-center gap-4 py-4">
            <div className="h-20 w-20 shrink-0 overflow-hidden rounded-xl bg-[#f1f4e9] sm:h-24 sm:w-24">{item.image_url ? <img src={item.image_url} alt="" className="h-full w-full object-cover" /> : <span className="grid h-full w-full place-items-center text-3xl text-olive" aria-hidden="true">✳</span>}</div>
            <div className="min-w-0 flex-1"><strong className="block truncate text-sm text-stone-900 sm:text-base">{item.product_name}</strong><p className="mt-1 text-sm text-stone-500">{Number(item.quantity).toLocaleString("vi-VN", { maximumFractionDigits: 3 })} {item.unit} × {money(item.unit_price_vnd)}</p></div>
            <strong className="shrink-0 text-sm text-forest sm:text-base">{money(item.line_total_vnd)}</strong>
          </div>)}</div>
          {order.items.length > 1 && <button type="button" className="relative z-10 mx-auto flex min-h-10 items-center gap-1 px-4 text-sm font-semibold text-olive hover:text-forest" aria-expanded={isExpanded} onClick={() => setExpanded(current => isExpanded ? current.filter(code => code !== order.order_code) : [...current, order.order_code])}>{isExpanded ? "Thu gọn" : `Xem thêm ${order.items.length - 1} sản phẩm`} <span aria-hidden="true">{isExpanded ? "⌃" : "⌄"}</span></button>}
          <div className="pointer-events-none relative flex flex-wrap items-end justify-between gap-2 border-t border-stone-100 pt-4"><span className="text-sm text-stone-500">Tổng tiền ({order.items.length} sản phẩm)</span><strong className="text-lg text-forest">{money(order.status === "awaiting_price_approval" ? order.proposed_total_vnd ?? order.total_vnd : order.total_vnd)}</strong></div>
          {order.is_preorder && order.proposed_total_vnd !== null && order.initial_total_vnd !== null && order.proposed_total_vnd !== order.initial_total_vnd && <p className="pointer-events-none relative mt-1 text-right text-xs text-stone-500">Lúc đặt {money(order.initial_total_vnd)} → Khi có hàng {money(order.proposed_total_vnd)}</p>}
        </article>;
      })}</div>
      {total > 10 && <div className="mt-7 flex justify-center"><Pagination current={page} total={total} pageSize={10} showSizeChanger={false} onChange={setPage} /></div>}
    </>}
    </div>
  </Shell>;
}
