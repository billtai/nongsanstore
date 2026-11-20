"use client";

import { Button, Empty } from "antd";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { BrandLoading } from "@/components/shared/brand-loading";
import { ErrorState } from "@/components/shared/error-state";
import { ProductCard } from "@/features/products/product-card";
import { LatestBanner } from "@/features/products/latest-banner";
import { api } from "@/lib/api";
import type { ProductPage } from "@/types/store";

const categoryIdeas = [
  { name : "Rau ăn lá", search : "cải", icon : "🥬", tone : "sage" },
  { name : "Củ quả", search : "cà", icon : "🥕", tone : "peach" },
  { name : "Trái cây", search : "trái cây", icon : "🍊", tone : "sun" },
  { name : "Nấm & gia vị", search : "nấm", icon : "🍄", tone : "cream" },
];

/** Trang chủ dùng sản phẩm API và danh mục gợi ý biên tập. Đầu vào: không có; đầu ra: hero, lối khám phá và sản phẩm. Ví dụ: truy cập /. */
export function Home() {
  const [data, setData]     = useState<ProductPage>();
  const [error, setError]   = useState("");
  const [reload, setReload] = useState(0);
  const [loadingMore, setLoadingMore] = useState(false);
  const [loadMoreError, setLoadMoreError] = useState("");
  const nextPage  = useRef(2);
  const pending   = useRef(false);
  const sentinel  = useRef<HTMLDivElement>(null);
  const requestId = useRef(0);

  useEffect(() => {
    // Nạp trang đầu và bỏ kết quả cũ khi tải lại; đầu vào: reload, đầu ra: 8 sản phẩm đầu.
    // Ví dụ: bấm Thử lại không nối dữ liệu của lần tải trước vào danh sách mới.
    const currentRequest = ++requestId.current;
    nextPage.current     = 2;
    pending.current      = false;
    setData(undefined);
    setError("");
    setLoadMoreError("");
    api<ProductPage>("/products?page=1&limit=8")
      .then(result => { if (requestId.current === currentRequest) setData(result); })
      .catch(reason => { if (requestId.current === currentRequest) setError(reason.message); });
    return () => { requestId.current++; };
  }, [reload]);

  useEffect(() => {
    if (!data || data.items.length >= data.total || !sentinel.current || pending.current || loadMoreError) return;
    // Cuộn gần cuối danh sách mới gọi trang kế; đầu vào: phần tử cuối và trang tiếp theo,
    // đầu ra: nối sản phẩm thật từ API. Ví dụ: xem hết 8 sản phẩm sẽ gọi page=2.
    const observer = new IntersectionObserver(entries => {
      if (!entries[0].isIntersecting || pending.current) return;
      pending.current = true;
      setLoadingMore(true);
      const currentRequest = requestId.current;
      const page           = nextPage.current;
      api<ProductPage>(`/products?page=${page}&limit=8`)
        .then(result => {
          if (requestId.current !== currentRequest) return;
          nextPage.current = page + 1;
          setData(current => current ? { ...result, items: [...current.items, ...result.items] } : result);
        })
        .catch(reason => { if (requestId.current === currentRequest) setLoadMoreError(reason.message); })
        .finally(() => { if (requestId.current === currentRequest) { pending.current = false; setLoadingMore(false); } });
    }, { rootMargin: "300px 0px" });
    observer.observe(sentinel.current);
    return () => observer.disconnect();
  }, [data, loadingMore, loadMoreError]);

  return <Shell>
    <section className="hero-panel relative flex min-h-[400px] overflow-hidden rounded-[2rem] bg-[#f6ead1] md:min-h-[460px]">
      <div className="hero-copy relative z-10 flex w-full flex-col justify-center p-7 sm:p-12 md:w-[56%] lg:p-16"><span className="mb-5 w-fit rounded-full bg-white/80 px-4 py-2 text-xs font-extrabold uppercase tracking-[.17em] text-olive">Tươi từ vườn · Ngon trên bàn</span><h1 className="max-w-xl text-[2.7rem] font-black leading-[1.08] tracking-tight text-forest sm:text-6xl">Mang vị tươi lành về căn bếp của bạn.</h1><p className="mt-6 max-w-md text-base leading-7 text-stone-700 sm:text-lg">Mỗi món rau củ có một câu chuyện. Khám phá mùa vụ, vùng trồng và chọn nguyên liệu cho bữa ăn thật ngon.</p><div className="mt-8 flex flex-wrap gap-3"><Link href="/san-pham"><Button type="primary" size="large">Mua sắm ngay <span aria-hidden>→</span></Button></Link><Link href="#kham-pha"><Button size="large">Khám phá danh mục</Button></Link></div></div>
    </section>
    {data?.items.length ? <LatestBanner products={data.items.slice(0, 3)} /> : null}
    <div className="mt-7 grid gap-3 sm:grid-cols-3"><div className="benefit-card"><span>✿</span><div><strong>Chọn theo mùa</strong><p>Gợi ý món ngon đúng vụ.</p></div></div><div className="benefit-card"><span>◎</span><div><strong>Rõ nguồn gốc</strong><p>Xem vùng trồng và lô hàng khi có.</p></div></div><div className="benefit-card"><span>♡</span><div><strong>Dễ dàng đặt hàng</strong><p>Báo giá rõ ràng trước khi xác nhận.</p></div></div></div>
    <section id="kham-pha" className="pt-16"><div className="section-heading"><div><p className="eyebrow">Lên thực đơn mỗi ngày</p><h2>Khám phá theo sở thích</h2><p>Gợi ý danh mục để tìm nhanh sản phẩm phù hợp.</p></div><Link href="/san-pham" className="section-link">Xem tất cả →</Link></div><div className="mt-7 grid grid-cols-2 gap-4 lg:grid-cols-4">{categoryIdeas.map(category => <Link key={category.name} href={`/san-pham?q=${encodeURIComponent(category.search)}`} className={`category-card ${category.tone}`}><span className="text-5xl" aria-hidden>{category.icon}</span><span className="mt-7 text-lg font-bold text-forest">{category.name}</span><span className="mt-1 text-sm text-stone-600">Tìm sản phẩm →</span></Link>)}</div></section>
    <section className="pt-16"><div className="section-heading"><div><p className="eyebrow">Từ cửa hàng</p><h2>Nông sản đang có</h2><p>Chọn món tươi ngon cho bữa ăn hôm nay.</p></div><Link href="/san-pham" className="section-link">Xem tất cả →</Link></div>{error ? <div className="mt-7"><ErrorState error={error} retry={() => setReload(value => value + 1)} /></div> : !data ? <BrandLoading label="Đang tải nông sản mới..." /> : data.items.length ? <><div className="mt-7 grid gap-5 sm:grid-cols-2 lg:grid-cols-4">{data.items.map(product => <ProductCard key={product.id} product={product} />)}</div><div ref={sentinel} className="min-h-10" aria-hidden="true" />{loadingMore && <BrandLoading label="Đang tải thêm nông sản..." compact />}{loadMoreError && <div className="mt-4"><ErrorState error={loadMoreError} retry={() => setLoadMoreError("")} /></div>}</> : <Empty className="mt-8" description="Chưa có sản phẩm" />}</section>
    <section className="mt-16 flex flex-wrap items-center justify-between gap-6 rounded-[2rem] bg-[#e8eddb] px-7 py-10 md:px-12"><div><p className="eyebrow">Bữa ăn bắt đầu từ nguyên liệu tốt</p><h2 className="mt-2 text-3xl font-black text-forest">Hôm nay ăn gì ngon?</h2><p className="mt-2 text-stone-600">Tìm nguyên liệu phù hợp với bữa cơm nhà bạn.</p></div><Link href="/san-pham"><Button type="primary" size="large">Tìm nông sản →</Button></Link></section>
  </Shell>;
}
