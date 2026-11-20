"use client";

import { Alert, Select, Spin } from "antd";
import { useEffect, useState } from "react";
import { adminApi } from "./api";

type Option = { value: string; label: string };

/**
 * Chọn đơn vị đang bật từ API với tìm kiếm/phân trang trên server.
 * Đầu vào: mã đang chọn và onChange; đầu ra: mã đơn vị cho form sản phẩm.
 * Ví dụ: tìm "thùng" chỉ yêu cầu /admin/units?q=thùng&active=true.
 */
export function UnitSelect({ value, onChange }: { value?: string; onChange?: (value: string) => void }) {
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
    const params = new URLSearchParams({ page: String(page), limit: "20", active: "true" });
    if (debounced) params.set("q", debounced);
    void adminApi(`/admin/units?${params}`)
      .then((data: { items: { code: string }[]; total: number }) => {
        if (!active) return;
        const fetched = data.items.map((item) => ({ value: item.code, label: item.code }));
        setOptions((previous) => {
          const current = value ? [{ value, label: value }] : [];
          const combined = page === 1 ? [...current, ...fetched] : [...previous, ...fetched];
          return [...new Map(combined.map((item) => [item.value, item])).values()];
        });
        setHasMore(page * 20 < data.total);
      })
      .catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "Không thể tải đơn vị."); })
      .finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [debounced, page, value]);

  return <>
    <Select<string>
      value={value}
      onChange={onChange}
      options={options}
      showSearch
      filterOption={false}
      searchValue={search}
      onSearch={setSearch}
      placeholder="Tìm và chọn đơn vị"
      loading={loading}
      notFoundContent={loading ? <Spin size="small" /> : "Không tìm thấy đơn vị"}
      onPopupScroll={(event) => {
        const target = event.currentTarget;
        if (hasMore && !loading && target.scrollTop + target.clientHeight >= target.scrollHeight - 24) setPage((current) => current + 1);
      }}
      style={{ width: "100%" }}
    />
    {error && <Alert type="error" message={error} showIcon className="mt-2" />}
  </>;
}
