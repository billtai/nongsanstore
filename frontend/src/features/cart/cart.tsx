"use client";

import { Alert, Button, Card, Empty, Form, Input, InputNumber, Pagination, Select, Skeleton, Space, Tag, message } from "antd";
import Link from "next/link";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import type { CartLine, Order, Product, ProductPage, Quote } from "@/types/store";
import { readCart, writeCart } from "@/features/cart/storage";
import { Shell } from "@/components/shared/shell";
import { BrandLoading } from "@/components/shared/brand-loading";
import { ErrorState } from "@/components/shared/error-state";
import { ProductCard } from "@/features/products/product-card";

export function Cart() {
  const router                  = useRouter();
  const [lines, setLines]       = useState<CartLine[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [drafts, setDrafts]     = useState<Record<string, number | null>>({});
  const [error, setError]       = useState("");
  const [ready, setReady]       = useState(false);
  // Đầu vào: các mã trong giỏ; đầu ra: thông tin sản phẩm từ API hoặc lỗi rõ ràng. Ví dụ: hai dòng giỏ sẽ tải hai sản phẩm trước khi hiện giỏ.
  useEffect(() => { const current = readCart(); setLines(current); if (current.length) Promise.all(current.map(line => api<Product>(`/products/${encodeURIComponent(line.product_id)}`))).then(setProducts).catch(e => setError(e.message)).finally(() => setReady(true)); else setReady(true); }, []);
  /** Lưu số lượng hợp lệ hoặc xóa dòng. Đầu vào: mã sản phẩm, số lượng; đầu ra: giỏ mới trong bộ nhớ và localStorage. Ví dụ: update("p1", 2). */
  const update = (id: string, quantity: number) => {
    const next = lines.map(line => line.product_id === id ? { ...line, quantity } : line).filter(line => line.quantity > 0);
    setLines(next);
    writeCart(next);
  };

  // Số đang nhập được giữ riêng để không tự sửa 400 thành tồn kho 10. Chỉ số hợp lệ mới được lưu vào giỏ.
  const invalidIds = new Set(lines.filter(line => {
    const product  = products.find(item => item.id === line.product_id);
    const entered  = Object.hasOwn(drafts, line.product_id) ? drafts[line.product_id] : line.quantity;
    return !product || entered === null || !Number.isInteger(entered) || entered < 1 || (line.preorder ? product.stock_quantity > 0 : entered > product.stock_quantity);
  }).map(line => line.product_id));

  return <Shell>
    <h1 className="mb-7 text-3xl font-bold">Giỏ hàng</h1>
    {!ready ? <BrandLoading label="Đang tải giỏ hàng..." /> : error ? <ErrorState error={error} /> : !lines.length ? <Empty description="Giỏ hàng đang trống"><Link href="/san-pham"><Button type="primary">Mua sắm ngay</Button></Link></Empty> : <>
      {([false, true] as const).map(preorder => {
        const groupLines = lines.filter(line => Boolean(line.preorder) === preorder);
        if (!groupLines.length) return null;
        return <section key={String(preorder)} className="mb-8">
          <div className="mb-4 flex flex-wrap items-end justify-between gap-2"><div><h2 className="text-2xl font-black text-forest">{preorder ? "Sản phẩm đặt trước" : "Sản phẩm có sẵn"}</h2><p className="mt-1 text-sm text-stone-500">{preorder ? "Chờ hàng về rồi cửa hàng sẽ xử lý và hẹn giao." : "Có thể xác nhận và xử lý đơn ngay."}</p></div><span className="text-sm font-semibold text-olive">{groupLines.length} sản phẩm</span></div>
          <div className="space-y-4">{groupLines.map(line => {
        const product = products.find(item => item.id === line.product_id);
        const entered = Object.hasOwn(drafts, line.product_id) ? drafts[line.product_id] : line.quantity;
        const warning = product && line.preorder && product.stock_quantity > 0
          ? "Sản phẩm đã có hàng. Vui lòng chuyển sang mua ngay."
          : product && !line.preorder && product.stock_quantity <= 0
          ? "Sản phẩm đã hết hàng. Bạn có thể chuyển sang đặt trước."
          : product && !line.preorder && entered !== null && entered > product.stock_quantity
          ? `Chỉ còn ${product.stock_quantity} ${product.unit} trong kho.`
          : entered === null || !Number.isInteger(entered) || entered < 1 ? "Vui lòng nhập số lượng hợp lệ." : "";

        return <Card key={line.product_id}>
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              {product && <Link href={`/san-pham/${encodeURIComponent(product.slug)}`} aria-label={`Xem chi tiết ${product.name}`} className="flex h-20 w-20 shrink-0 items-center justify-center overflow-hidden rounded-xl bg-[#f1f3e9] sm:h-24 sm:w-24">{product.image_url ? <img src={product.image_url} alt={product.name} className="h-full w-full object-cover" /> : <span aria-hidden="true" className="text-3xl text-olive">✳</span>}</Link>}
              <div>{product && <Link href={`/san-pham/${encodeURIComponent(product.slug)}`} className="font-semibold">{product.name}</Link>}{line.preorder && <Tag className="ml-2" color="gold">Đặt trước</Tag>}<p className="text-sm text-stone-500">{product && `${money(product.price)} / ${product.unit}`}</p></div>
            </div>
            <div><Space>
              <InputNumber aria-label={`Số lượng ${product?.name || "sản phẩm"}`} min={1} value={entered} status={warning ? "error" : undefined} onChange={value => {
                setDrafts(current => ({ ...current, [line.product_id] : value }));
                // Đầu vào: số vừa nhập vượt tồn; đầu ra: thông báo nổi không làm card đổi chiều cao. Ví dụ: nhập 401 khi chỉ còn 400 kg.
                if (product && !line.preorder && value !== null && value > product.stock_quantity && product.stock_quantity > 0) message.warning({ content: `Chỉ còn ${product.stock_quantity} ${product.unit} trong kho.`, key: `stock-${line.product_id}`, duration: 2 });
                if (product && value !== null && Number.isInteger(value) && value >= 1 && (line.preorder ? product.stock_quantity <= 0 : value <= product.stock_quantity)) update(line.product_id, value);
              }} />
              <Button danger onClick={() => { update(line.product_id, 0); setDrafts(current => { const next = { ...current }; delete next[line.product_id]; return next; }); }}>Xóa</Button>
            </Space>{product && ((line.preorder && product.stock_quantity > 0) || (!line.preorder && product.stock_quantity <= 0)) && <Button type="link" className="block p-0" onClick={() => {
              const preorder = product.stock_quantity <= 0;
              if (!preorder && entered !== null && entered > product.stock_quantity) { message.warning(`Chỉ còn ${product.stock_quantity} ${product.unit}. Hãy giảm số lượng trước.`); return; }
              const next = lines.map(item => item.product_id === line.product_id ? { ...item, preorder } : item);
              setLines(next);
              writeCart(next);
            }}>{product.stock_quantity <= 0 ? "Chuyển sang đặt trước" : "Chuyển sang mua ngay"}</Button>}</div>
          </div>
        </Card>;
      })}</div>
          <Button type="primary" size="large" className="mt-4" disabled={groupLines.some(line => invalidIds.has(line.product_id))} onClick={() => router.push(preorder ? "/thanh-toan/dat-truoc" : "/thanh-toan")}>{preorder ? "Đặt trước" : "Thanh toán hàng có sẵn"}</Button>
        </section>;
      })}
    </>}
  </Shell>;
}

type CheckoutValues = { name: string; phone: string; email?: string; address: string; province: string; note?: string; coupon_code?: string };

/** Thanh toán yêu cầu backend báo giá trước khi tạo đơn. Đầu vào: giỏ và thông tin giao hàng; đầu ra: báo giá và mã đơn. Ví dụ: /thanh-toan. */
