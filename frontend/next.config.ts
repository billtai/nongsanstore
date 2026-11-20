import type { NextConfig } from "next";

// Chuyển API qua cùng origin để cookie phiên được gửi ổn định khi dùng frontend.
// Đầu vào: yêu cầu /api/v1/*; đầu ra: phản hồi Flask tương ứng.
// Ví dụ: /api/v1/admin/products được chuyển đến backend.
const nextConfig: NextConfig = {
  // Tách cache dev khỏi build production để lệnh build không làm mất chunk của server đang chạy.
  // Đầu vào: NODE_ENV; đầu ra: thư mục cache. Ví dụ: next dev dùng .next-dev.
  distDir: process.env.NODE_ENV === "development" ? ".next-dev" : ".next",
  async rewrites() {
    const backend = process.env.API_URL || "http://127.0.0.1:5000";
    return [
      { source : "/api/v1/:path*", destination : `${backend}/api/v1/:path*` },
      { source : "/assets/:path*", destination : `${backend}/assets/:path*` },
    ];
  },
};

export default nextConfig;
