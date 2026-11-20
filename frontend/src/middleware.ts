import { NextRequest, NextResponse } from "next/server";

/**
 * Kiểm tra token với Flask trước khi hiển thị trang admin.
 * Đầu vào: request /admin; đầu ra: cho qua hoặc chuyển đến trang đăng nhập.
 * Ví dụ: token của customer bị từ chối dù cookie vẫn còn.
 */
export async function middleware(request: NextRequest) {
  if (request.nextUrl.pathname === "/admin/dang-nhap") return NextResponse.next();
  const token = request.cookies.get("admin_token")?.value;
  if (token) {
    try {
      const backend  = process.env.API_URL || "http://127.0.0.1:5000";
      const response = await fetch(`${backend}/api/v1/auth/me`, { headers: { Authorization: `Bearer ${token}` }, cache: "no-store" });
      if (response.ok && (await response.json()).role === "admin") return NextResponse.next();
    } catch {
      // API không phản hồi thì route quản trị không được hiển thị.
    }
  }
  return NextResponse.redirect(new URL("/admin/dang-nhap", request.url));
}

export const config = { matcher: ["/admin/:path*"] };
