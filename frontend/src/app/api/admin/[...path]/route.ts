import { NextRequest, NextResponse } from "next/server";

const backend = process.env.API_URL || "http://127.0.0.1:5000";

/**
 * Chuyển yêu cầu admin đến Flask với Bearer token trong cookie HttpOnly.
 * Đầu vào: path, phương thức và body; đầu ra: response API tương ứng.
 * Ví dụ: GET /api/admin/products?page=1 gọi GET /api/v1/admin/products?page=1.
 */
async function proxy(request: NextRequest, context: { params: Promise<{ path: string[] }> }) {
  const token = request.cookies.get("admin_token")?.value;
  if (!token) return NextResponse.json({ error: { message: "Vui lòng đăng nhập." } }, { status: 401 });
  const { path } = await context.params;
  const target   = new URL(`${backend}/api/v1/admin/${path.join("/")}`);
  target.search  = request.nextUrl.search;
  try {
    const contentType = request.headers.get("content-type") || "application/json";
    const response = await fetch(target, {
      method  : request.method,
      headers : { Authorization: `Bearer ${token}`, "Content-Type": contentType },
      body    : ["GET", "HEAD"].includes(request.method) ? undefined : await request.arrayBuffer(),
      cache   : "no-store",
    });
    return new NextResponse(await response.text(), { status: response.status, headers: { "Content-Type": "application/json" } });
  } catch {
    return NextResponse.json({ error: { message: "Không thể kết nối API." } }, { status: 502 });
  }
}

export const GET    = proxy;
export const POST   = proxy;
export const PATCH  = proxy;
export const DELETE = proxy;
