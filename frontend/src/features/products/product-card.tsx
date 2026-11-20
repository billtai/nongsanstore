"use client";

import { Button } from "antd";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { readCart, writeCart } from "@/features/cart/storage";
import { flyToCart } from "@/features/cart/fly-to-cart";
import { money } from "@/lib/format";
import type { Product } from "@/types/store";

/** Thẻ sản phẩm thật từ API. Đầu vào: Product; đầu ra: ảnh, giá, tồn và nút thêm giỏ. Ví dụ: <ProductCard product={item} />. */
export function ProductCard({ product }: { product: Product }) {
  const router           = useRouter();
  const [added, setAdded] = useState(false);
  const feedbackTimer  = useRef<ReturnType<typeof setTimeout> | null>(null);
  const soldOut        = product.stock_quantity <= 0;
  const detailUrl      = `/san-pham/${encodeURIComponent(product.slug)}`;

  useEffect(() => () => { if (feedbackTimer.current) clearTimeout(feedbackTimer.current); }, []);

  const add = (event: React.MouseEvent<HTMLElement>) => {
    const lines    = readCart();
    const existing = lines.find(line => line.product_id === product.id);
    // Đầu vào: sản phẩm đang bán hoặc hết hàng; đầu ra: dòng mua thường hoặc đặt trước trong giỏ.
    // Ví dụ: cà chua tồn 0 được thêm với preorder=true để khách xác nhận ở thanh toán.
    if (existing && !soldOut && existing.quantity >= product.stock_quantity) return;
    if (existing) {
      existing.quantity = soldOut ? existing.quantity + 1 : Math.min(product.stock_quantity, existing.quantity + 1);
      existing.preorder = soldOut;
    } else lines.push({ product_id : product.id, quantity : 1, preorder : soldOut });
    writeCart(lines);
    flyToCart(product.image_url, event.currentTarget.closest("article")?.querySelector("img") || event.currentTarget);
    // Đầu vào: lần bấm thêm sản phẩm; đầu ra: dấu xác nhận trên nút trong 2 giây.
    // Ví dụ: bấm dấu + thì nút chuyển thành ✓ và hiện chữ "Đã thêm vào giỏ".
    setAdded(true);
    if (feedbackTimer.current) clearTimeout(feedbackTimer.current);
    feedbackTimer.current = setTimeout(() => setAdded(false), 2000);
  };

  // Đầu vào: cú bấm vào nền card; đầu ra: trang chi tiết. Ví dụ: bấm vùng giá mở sản phẩm, bấm nút + chỉ thêm giỏ.
  return <article
    className={`product-card group flex h-full cursor-pointer flex-col overflow-hidden rounded-3xl border shadow-sm transition duration-300 hover:-translate-y-1 hover:shadow-xl focus-visible:outline focus-visible:outline-2 focus-visible:outline-forest ${soldOut ? "border-stone-200 bg-stone-50" : "border-stone-100 bg-white"}`}
    role="link"
    tabIndex={0}
    aria-label={`Xem chi tiết ${product.name}`}
    onClick={event => { if (!(event.target as HTMLElement).closest("a, button")) router.push(detailUrl); }}
    onKeyDown={event => { if (event.target === event.currentTarget && (event.key === "Enter" || event.key === " ")) { event.preventDefault(); router.push(detailUrl); } }}
  >
    <Link href={`/san-pham/${encodeURIComponent(product.slug)}`} className="relative block overflow-hidden bg-[#f1f3e9]">
      {/* Chỉ làm mờ ảnh để tên và giá vẫn dễ đọc. Ví dụ: tồn kho 0 hiện ảnh xám và nhãn Hết hàng. */}
      {product.image_url ? <img className={`aspect-[4/3] w-full object-cover transition duration-500 ${soldOut ? "grayscale opacity-50" : "group-hover:scale-105"}`} src={product.image_url} alt={product.name} /> : <div className={`flex aspect-[4/3] items-center justify-center bg-gradient-to-br from-[#e9eddb] to-[#faf3de] ${soldOut ? "grayscale opacity-50" : ""}`}><span className="text-6xl opacity-60">✳</span></div>}
      {soldOut ? <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-forest px-5 py-2 text-sm font-bold text-white shadow-lg">Hết hàng</span> : <span className="absolute left-4 top-4 rounded-full bg-white/95 px-3 py-1 text-xs font-bold text-forest shadow-sm">Tươi mỗi ngày</span>}
    </Link>
    <div className="flex flex-1 flex-col p-5"><p className="mb-2 text-xs font-bold uppercase tracking-[.14em] text-olive">{product.category || "Nông sản"}</p><Link href={`/san-pham/${encodeURIComponent(product.slug)}`} className="line-clamp-2 text-lg font-bold leading-snug text-stone-900">{product.name}</Link><p className="mt-2 text-sm text-stone-500">{product.growing_region || "Xem thông tin vùng trồng"}</p><div className="mt-auto flex items-end justify-between gap-3 pt-5"><div><p className="text-xl font-black text-forest">{money(product.price)}</p><p className="text-xs text-stone-500">/ {product.unit}</p></div><div className="relative"><Button type="primary" shape={soldOut ? undefined : "circle"} size="large" className={added ? "cart-add-success" : ""} aria-label={added ? `${product.name} đã thêm vào giỏ` : soldOut ? `Đặt trước ${product.name}` : `Thêm ${product.name} vào giỏ`} onClick={add}>{added ? "✓" : soldOut ? "Đặt trước" : "＋"}</Button>{added && <span role="status" className="cart-add-label">{soldOut ? "Đã thêm đặt trước" : "Đã thêm vào giỏ"}</span>}</div></div></div>
  </article>;
}
