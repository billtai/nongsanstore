"use client";

import { Button, Empty, InputNumber, Tabs, Tag } from "antd";
import Link from "next/link";
import { useParams } from "next/navigation";
import { useEffect, useRef, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { BrandLoading } from "@/components/shared/brand-loading";
import { ErrorState } from "@/components/shared/error-state";
import { ProductCard } from "@/features/products/product-card";
import { readCart, writeCart } from "@/features/cart/storage";
import { flyToCart } from "@/features/cart/fly-to-cart";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import type { Product, ProductPage } from "@/types/store";

type Batch = { id: number; batch_code: string; growing_region: string; origin: string; harvest_date: string; remaining_quantity: string };

/** Chi tiết theo slug, đọc ảnh và lô hàng công khai từ API. Đầu vào: slug URL; đầu ra: sản phẩm, tồn và thông tin nguồn gốc. Ví dụ: /san-pham/ca-rot-da-lat. */
export function ProductDetail() {
  const slug                                = useParams<{ slug: string }>().slug;
  const [product, setProduct]               = useState<Product>();
  const [batches, setBatches]               = useState<Batch[]>([]);
  const [related, setRelated]               = useState<Product[]>([]);
  const [categories, setCategories]         = useState<string[]>([]);
  const [error, setError]                   = useState("");
  const [quantity, setQuantity]             = useState(1);
  const [reload, setReload]                 = useState(0);
  const [selectedImage, setSelectedImage]   = useState("");
  const [added, setAdded]                   = useState(false);
  const feedbackTimer                       = useRef<ReturnType<typeof setTimeout> | null>(null);

  useEffect(() => () => { if (feedbackTimer.current) clearTimeout(feedbackTimer.current); }, []);

  useEffect(() => {
    setProduct(undefined);
    setError("");
    setRelated([]);
    api<{ items: string[] }>("/products/categories").then(data => setCategories(data.items)).catch(() => setCategories([]));
    api<Product>(`/products/by-slug/${encodeURIComponent(slug)}`).then(item => {
      setProduct(item);
      api<{ items: Batch[] }>(`/products/${item.id}/batches?limit=4`).then(data => setBatches(data.items)).catch(() => setBatches([]));
      api<ProductPage>(`/products?category=${encodeURIComponent(item.category)}&page=1&limit=5`).then(data => setRelated(data.items.filter(candidate => candidate.id !== item.id).slice(0, 4))).catch(() => setRelated([]));
    }).catch(error => setError(error.message));
  }, [slug, reload]);

  const add = (event: React.MouseEvent<HTMLElement>) => {
    if (!product) return;
    const lines    = readCart();
    const existing = lines.find(line => line.product_id === product.id);
    const preorder = product.stock_quantity <= 0;
    const next     = preorder ? (existing?.quantity || 0) + quantity : Math.min(product.stock_quantity, (existing?.quantity || 0) + quantity);
    if (existing && !preorder && existing.quantity >= product.stock_quantity) return;
    // Đầu vào: số lượng chọn và tồn kho; đầu ra: dòng đặt trước khi tồn 0, hoặc dòng mua thường khi còn hàng.
    // Ví dụ: 2 kg sản phẩm hết hàng được lưu với preorder=true, chờ xác nhận ở thanh toán.
    if (existing) { existing.quantity = next; existing.preorder = preorder; }
    else lines.push({ product_id : product.id, quantity : next, preorder });
    writeCart(lines);
    flyToCart(product.image_url, event.currentTarget.closest("section")?.querySelector("img") || event.currentTarget);
    // Đầu vào: số lượng vừa thêm; đầu ra: nút xác nhận trực quan trong 2 giây.
    // Ví dụ: thêm 2 sản phẩm thì nút hiện "✓ Đã thêm vào giỏ".
    setAdded(true);
    if (feedbackTimer.current) clearTimeout(feedbackTimer.current);
    feedbackTimer.current = setTimeout(() => setAdded(false), 2000);
  };

  const gallery = product ? [product.image_url, ...(product.images || []).map(image => image.image_url)].filter((url): url is string => !!url) : [];
  const soldOut = !!product && product.stock_quantity <= 0;

  return <Shell>{error ? <ErrorState error={error} retry={() => setReload(value => value + 1)} /> : !product ? <BrandLoading label="Đang tải chi tiết sản phẩm..." /> : <>
    <div className="mb-6 text-sm text-stone-500"><Link href="/">Trang chủ</Link> / <Link href="/san-pham">Sản phẩm</Link> / <span className="text-forest">{product.name}</span></div>
    <nav className="mb-7 flex flex-wrap items-center gap-2" aria-label="Danh mục sản phẩm"><span className="mr-2 text-sm font-bold text-forest">Danh mục:</span>{categories.map(category => <Link key={category} href={`/san-pham?category=${encodeURIComponent(category)}`} className={`rounded-full border px-4 py-2 text-xs font-semibold ${category === product.category ? "border-[#1e4b32] bg-[#e8eddb] text-forest" : "border-stone-200 bg-white text-stone-600"}`}>{category}</Link>)}</nav>
    <section className="grid gap-8 lg:grid-cols-[1.05fr_.95fr] lg:gap-12"><div><div className="relative flex min-h-[350px] items-center justify-center overflow-hidden rounded-[2rem] bg-[#edf0e5] sm:min-h-[500px]">{gallery.length ? <img src={gallery.includes(selectedImage) ? selectedImage : gallery[0]} alt={product.name} className={`h-full max-h-[620px] w-full object-cover ${soldOut ? "grayscale opacity-50" : ""}`} /> : <span className={`text-7xl text-olive ${soldOut ? "grayscale opacity-50" : ""}`}>✳</span>}{soldOut && <span className="absolute left-1/2 top-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full bg-forest px-6 py-3 text-base font-bold text-white shadow-lg">Hết hàng</span>}</div>{gallery.length > 1 && <div className="mt-4 flex flex-wrap gap-3">{gallery.map((url, index) => <button key={`${url}-${index}`} type="button" onClick={() => setSelectedImage(url)} aria-label={`Xem ảnh ${index + 1}`} className="overflow-hidden rounded-xl border-2 border-[#dbe7ce] focus:border-[#1e4b32]"><img src={url} alt={`${product.name} ${index + 1}`} className={`h-20 w-20 object-cover ${soldOut ? "grayscale opacity-50" : ""}`} /></button>)}</div>}</div>
    <div className="rounded-[2rem] border border-stone-100 bg-white p-6 shadow-sm md:p-9"><Tag color={soldOut ? "default" : "green"}>{soldOut ? "Hết hàng" : "Nông sản tươi"}</Tag><h1 className="mt-4 text-3xl font-black leading-tight text-forest md:text-4xl">{product.name}</h1><p className="mt-4 text-sm text-stone-500">Đơn vị bán: {product.unit}</p><p className="mt-6 text-4xl font-black text-forest">{money(product.price)} <span className="text-base font-medium text-stone-500">/ {product.unit}</span></p><div className="my-7 border-y border-stone-100 py-6"><p className="leading-7 text-stone-600">{product.description || "Thông tin mô tả đang được cập nhật."}</p></div><div className="grid gap-3 text-sm sm:grid-cols-2"><p className="rounded-xl bg-[#f4f6ee] p-4"><strong className="block text-forest">Tình trạng</strong>{product.stock_quantity > 0 ? `Còn ${product.stock_quantity} ${product.unit}` : "Tạm hết hàng"}</p><p className="rounded-xl bg-[#f4f6ee] p-4"><strong className="block text-forest">Nguồn gốc</strong>{batches[0]?.growing_region || "Đang cập nhật"}</p></div><div className="mt-7 flex flex-wrap items-center gap-3"><InputNumber size="large" min={1} max={soldOut ? undefined : product.stock_quantity} value={quantity} onChange={value => setQuantity(value || 1)} /><Button type="primary" size="large" className={added ? "cart-add-success" : ""} onClick={add} aria-live="polite">{added ? "✓ Đã thêm vào giỏ" : soldOut ? "Đặt trước sản phẩm" : "Thêm vào giỏ hàng"}</Button></div>{soldOut && <p className="mt-4 text-sm text-stone-600">Sản phẩm đang hết hàng. Đơn đặt trước sẽ được xử lý khi có đủ hàng; thanh toán khi nhận hàng.</p>}</div></section>
    <section className="mt-12 rounded-[2rem] bg-white p-6 md:p-9"><Tabs items={[{ key : "description", label : "Mô tả sản phẩm", children : <p className="max-w-3xl whitespace-pre-line leading-8 text-stone-600">{product.description || "Thông tin mô tả đang được cập nhật."}</p> }, { key : "origin", label : "Lô hàng & vùng trồng", children : batches.length ? <div className="grid gap-4 md:grid-cols-2">{batches.map(batch => <div key={batch.id} className="rounded-2xl bg-[#f4f6ee] p-5 text-sm leading-7"><p><strong>Lô hàng:</strong> {batch.batch_code}</p><p><strong>Vùng trồng:</strong> {batch.growing_region}</p><p><strong>Nguồn gốc:</strong> {batch.origin}</p><p><strong>Ngày thu hoạch:</strong> {batch.harvest_date}</p></div>)}</div> : <Empty description="Chưa có thông tin lô hàng" /> }]} /></section>
    <section className="mt-14"><div className="section-heading"><div><p className="eyebrow">Cùng nhóm với {product.name}</p><h2>Thêm từ danh mục {product.category}</h2></div><Link href={`/san-pham?category=${encodeURIComponent(product.category)}`} className="section-link">Xem danh mục →</Link></div>{related.length ? <div className="mt-7 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">{related.map(item => <ProductCard key={item.id} product={item} />)}</div> : <p className="mt-6 rounded-2xl bg-[#eef2e7] p-6 text-sm text-stone-600">Hiện chưa có sản phẩm khác trong danh mục này.</p>}</section>
  </>}</Shell>;
}
