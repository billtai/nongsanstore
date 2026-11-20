/** Hiển thị trạng thái tải bằng logo Vườn Nhà. Đầu vào: label và compact tùy chọn; đầu ra: biểu tượng và thông báo. Ví dụ: <BrandLoading label="Đang tải sản phẩm..." compact />. */
export function BrandLoading({ label = "Đang tải dữ liệu...", compact = false }: { label?: string; compact?: boolean }) {
  return <div className={`brand-loading ${compact ? "brand-loading-compact" : ""}`} role="status" aria-live="polite">
    <div className="brand-loading-mark" aria-hidden="true">
      <span className="brand-loading-ring" />
      <img src="/icon.svg" alt="" width={60} height={60} />
    </div>
    <p>{label}</p>
  </div>;
}
