"use client";

import { Alert, Select, Spin } from "antd";
import { useEffect, useState } from "react";
import { adminApi } from "./api";
import type { Row } from "./types";

type Option = { value: number; label: string };

/**
 * Chọn sản phẩm bằng tìm kiếm và phân trang API quản trị.
 * Đầu vào: value/onChange của Form và sản phẩm đang sửa; đầu ra: product_id đã chọn.
 * Ví dụ: gõ "cà rốt" chỉ yêu cầu /admin/products?q=cà%20rốt&limit=20.
 */
export function ProductSelect({ value, onChange, editing }: { value?: number; onChange?: (value: number) => void; editing: Row | null }) {
  const [search, setSearch]   = useState("");
  const [debounced, setDebounced] = useState("");
  const [page, setPage]       = useState(1);
  const [options, setOptions] = useState<Option[]>([]);
  const [hasMore, setHasMore] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");

  useEffect(() => {
    const timer = window.setTimeout(() => { setPage(1); setDebounced(search.trim()); }, 300);
    return () => window.clearTimeout(timer);
  }, [search]);

  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: String(page), limit: "20" });
    if (debounced) params.set("q", debounced);
    void adminApi(`/admin/products?${params}`)
      .then((data: { items: Row[]; total: number }) => {
        if (!active) return;
        const fetched = data.items.map((item) => ({ value: item.id, label: `${item.name} · ${item.unit}` }));
        const current = editing?.product_id && editing.product_name
          ? [{ value: editing.product_id, label: editing.product_name }]
          : [];
        setOptions((previous) => {
          const combined = page === 1 ? [...current, ...fetched] : [...previous, ...fetched];
          return [...new Map(combined.map((item) => [item.value, item])).values()];
        });
        setHasMore(page * 20 < data.total);
      })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "Không thể tải sản phẩm."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [debounced, page, editing?.product_id, editing?.product_name]);

  return <>
    <Select<number>
      value={value}
      disabled={!!editing}
      onChange={onChange}
      options={options}
      showSearch
      filterOption={false}
      searchValue={search}
      onSearch={setSearch}
      placeholder="Tìm và chọn sản phẩm"
      loading={loading}
      notFoundContent={loading ? <Spin size="small" /> : "Không tìm thấy sản phẩm"}
      onPopupScroll={(event) => {
        const target = event.currentTarget;
        if (hasMore && !loading && target.scrollTop + target.clientHeight >= target.scrollHeight - 24) setPage((current) => current + 1);
      }}
      style={{ width: "100%" }}
    />
    {error && <Alert type="error" message={error} showIcon className="mt-2" />}
  </>;
}
