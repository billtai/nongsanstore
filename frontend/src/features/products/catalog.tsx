"use client";

import { Empty, Input, Pagination, Select } from "antd";
import Link from "next/link";
import { useRouter, useSearchParams } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { BrandLoading } from "@/components/shared/brand-loading";
import { ErrorState } from "@/components/shared/error-state";
import { ProductCard } from "@/features/products/product-card";
import { api } from "@/lib/api";
import type { ProductPage } from "@/types/store";

/** Danh sách dùng tham số q/unit/page/limit của backend. Đầu vào: URL tìm kiếm; đầu ra: sản phẩm và phân trang. Ví dụ: /san-pham?q=ca&page=2. */
export function Catalog() {
  const router              = useRouter();
  const search              = useSearchParams();
  const [data, setData]     = useState<ProductPage>();
  const [error, setError]   = useState("");
  const [categories, setCategories] = useState<string[]>([]);
  const [reload, setReload] = useState(0);
  const query               = search.toString();

  useEffect(() => {
    setData(undefined);
    setError("");
    api<ProductPage>(`/products?${query || "page=1"}`).then(setData).catch(error => setError(error.message));
  }, [query, reload]);
  useEffect(() => { api<{ items: string[] }>("/products/categories").then(data => setCategories(data.items)).catch(() => setCategories([])); }, []);

  const change = (key: string, value: string) => {
    const next = new URLSearchParams(query);
    value ? next.set(key, value) : next.delete(key);
    next.set("page", "1");
    router.push(`/san-pham?${next}`);
  };

  return <Shell>
    <div className="mb-6 text-sm text-stone-500"><Link href="/">Trang chủ</Link> / <span className="text-forest">Sản phẩm</span></div>
    <div className="rounded-[2rem] bg-[#e8eddb] px-6 py-10 md:px-12"><p className="eyebrow">Chợ nông sản</p><h1 className="mt-2 text-4xl font-black text-forest md:text-5xl">Chọn món tươi cho hôm nay</h1><p className="mt-3 max-w-xl leading-7 text-stone-600">Tìm nguyên liệu tươi ngon cho bữa cơm nhà.</p></div>
    <div className="my-7 flex flex-wrap items-center gap-3 rounded-2xl border border-stone-100 bg-white p-4 shadow-sm"><Input.Search key={search.get("q") || ""} className="min-w-[220px] flex-1" placeholder="Tìm tên sản phẩm..." defaultValue={search.get("q") || ""} onSearch={value => change("q", value.trim())} allowClear size="large" /><Select className="w-full sm:w-52" size="large" aria-label="Danh mục" placeholder="Danh mục" value={search.get("category") || undefined} allowClear onChange={value => change("category", value || "")} options={categories.map(value => ({ value, label : value }))} /><Select className="w-full sm:w-44" size="large" aria-label="Đơn vị bán" placeholder="Đơn vị bán" value={search.get("unit") || undefined} allowClear onChange={value => change("unit", value || "")} options={[{ value : "kg", label : "Theo kg" }, { value : "bó", label : "Theo bó" }, { value : "hộp", label : "Theo hộp" }]} /></div>
    <div className="mb-5 flex flex-wrap items-center justify-between gap-2"><div><h2 className="text-2xl font-black text-forest">Tất cả sản phẩm</h2><p className="mt-1 text-sm text-stone-500">{data ? `${data.total} sản phẩm phù hợp` : "Đang cập nhật danh sách"}</p></div><span className="rounded-full bg-[#edf3e3] px-4 py-2 text-xs font-semibold text-forest">Tươi ngon mỗi ngày</span></div>
    {error ? <ErrorState error={error} retry={() => setReload(value => value + 1)} /> : !data ? <BrandLoading label="Đang tìm sản phẩm..." /> : data.items.length ? <><div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">{data.items.map(product => <ProductCard key={product.id} product={product} />)}</div><div className="mt-9 flex justify-center"><Pagination current={Number(search.get("page") || 1)} pageSize={data.page_size} total={data.total} onChange={page => { const next = new URLSearchParams(query); next.set("page", String(page)); router.push(`/san-pham?${next}`); }} /></div></> : <Empty className="py-16" description="Không tìm thấy sản phẩm phù hợp" />}
  </Shell>;
}
