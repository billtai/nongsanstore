import { NextRequest, NextResponse } from "next/server";

const backend = process.env.API_URL || "http://127.0.0.1:5000";

/**
 * Đăng nhập admin và lưu Bearer token vào cookie HttpOnly.
 * Đầu vào: email/password; đầu ra: user hoặc lỗi xác thực.
 * Ví dụ: POST /api/admin-session với tài khoản admin tạo phiên 24 giờ.
 */
export async function POST(request: NextRequest) {
  try {
    const response = await fetch(`${backend}/api/v1/auth/login`, { method: "POST", headers: { "Content-Type": "application/json" }, body: await request.text(), cache: "no-store" });
    const data     = await response.json();
    if (!response.ok) return NextResponse.json(data, { status: response.status });
    if (data.user?.role !== "admin") return NextResponse.json({ error: { message: "Tài khoản không có quyền quản trị." } }, { status: 403 });
    const result = NextResponse.json(data.user);
    result.cookies.set("admin_token", data.access_token, { httpOnly: true, sameSite: "lax", secure: process.env.NODE_ENV === "production", path: "/", maxAge: Math.min(data.expires_in || 86400, 86400) });
    return result;
  } catch {
    return NextResponse.json({ error: { message: "Không thể kết nối API." } }, { status: 502 });
  }
}

/** Xóa cookie phiên; không có đầu vào, đầu ra ok. Ví dụ DELETE /api/admin-session. */
export async function DELETE() {
  const result = NextResponse.json({ ok: true });
  result.cookies.delete("admin_token");
  return result;
}
