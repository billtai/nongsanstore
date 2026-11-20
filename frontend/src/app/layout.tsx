import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: {
    default  : "Vườn Nhà | Nông sản tươi",
    template : "%s | Vườn Nhà",
  },
  description : "Nông sản tươi theo mùa, rõ vùng trồng và lô hàng.",
  icons       : { icon : "/icon.svg" },
};

/**
 * Bọc mọi trang trong cấu trúc HTML chung.
 * Đầu vào: children là nội dung trang React; đầu ra: cây HTML của ứng dụng.
 * Ví dụ: trang chủ được đặt trong thẻ body khi truy cập /.
 */
export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="vi">
      <body>{children}</body>
    </html>
  );
}
