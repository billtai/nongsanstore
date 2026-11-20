"use client";

import { Button } from "antd";
import Link from "next/link";
import { useEffect, useState } from "react";
import { money } from "@/lib/format";
import type { Product } from "@/types/store";

/** Banner luân phiên tối đa ba sản phẩm mới nhất. Đầu vào: mảng Product đã sắp theo ngày tạo; đầu ra: banner đổi mỗi 5 giây. Ví dụ: <LatestBanner products={items.slice(0, 3)} />. */
export function LatestBanner({ products }: { products: Product[] }) {
  const [active, setActive] = useState(0);
  const [paused, setPaused] = useState(false);
  const current             = Math.min(active, products.length - 1);

  useEffect(() => {
    if (paused || products.length < 2) return;
    const timer = window.setTimeout(() => setActive(index => (index + 1) % products.length), 5000);
    return () => window.clearTimeout(timer);
  }, [active, paused, products.length]);

  if (!products.length) return null;

  return <section className="latest-section mt-12" aria-label="Ba sản phẩm mới nhất"><div className="section-heading mb-6"><div><p className="eyebrow">Vừa lên kệ</p><h2>Mới từ Vườn Nhà</h2><p>Ba sản phẩm được thêm gần đây nhất.</p></div><Link href="/san-pham" className="section-link">Xem tất cả →</Link></div>
    <div className="latest-banner relative isolate overflow-hidden rounded-[2rem]" onMouseEnter={() => setPaused(true)} onMouseLeave={() => setPaused(false)} onFocusCapture={() => setPaused(true)} onBlurCapture={event => { if (!event.currentTarget.contains(event.relatedTarget)) setPaused(false); }}>
      {products.map((product, index) => <div key={product.id} className={`latest-slide ${index === current ? "is-active" : ""}`} aria-hidden={index !== current}>
        {/* Ảnh nền phủ nhẹ và ảnh chính vừa khung; đầu vào là ảnh đại diện API, ví dụ củ sâm vẫn thấy trọn trên banner. */}
        <div className="latest-photo">{product.image_url ? <><img className="latest-photo-backdrop" src={product.image_url} alt="" aria-hidden="true" /><img className="latest-photo-main" src={product.image_url} alt={index === current ? product.name : ""} /></> : <div className="latest-photo-missing"><span>✳</span><p>Chưa có ảnh đại diện</p></div>}</div>
        <div className="latest-shade" />
        <div className="latest-content"><span className="latest-kicker">Mới lên kệ <span>0{index + 1} / 0{products.length}</span></span><h3>{product.name}</h3><p className="latest-description">{product.description || "Khám phá sản phẩm tươi từ cửa hàng."}</p><p className="latest-price">{money(product.price)} <span>/ {product.unit}</span></p><Link href={`/san-pham/${encodeURIComponent(product.slug)}`} tabIndex={index === current ? 0 : -1}><Button size="large">Xem sản phẩm <span aria-hidden>↗</span></Button></Link></div>
      </div>)}
      <div className="latest-controls" role="group" aria-label="Chọn sản phẩm trong banner">{products.map((product, index) => <button key={product.id} type="button" className={`latest-dot ${index === current ? "is-active" : ""}`} onClick={() => setActive(index)} aria-label={`Hiển thị ${product.name}`} aria-current={index === current ? "true" : undefined}><span className="latest-dot-progress" key={index === current ? `${product.id}-${active}-${paused}` : product.id} style={{ animationPlayState : paused ? "paused" : "running", animationDuration : products.length < 2 ? "0s" : "5s" }} /></button>)}</div>
    </div>
  </section>;
}
