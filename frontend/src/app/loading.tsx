import { BrandLoading } from "@/components/shared/brand-loading";

/** Trạng thái chờ khi Next.js chuyển trang. Đầu vào: tiến trình điều hướng; đầu ra: logo và lời nhắc đang tải. Ví dụ: chuyển từ trang chủ sang trang sản phẩm. */
export default function Loading() {
  return <main className="store-shell min-h-screen px-4 py-20"><BrandLoading label="Đang mở trang..." /></main>;
}
