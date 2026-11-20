"use client";

import { Alert, Button, Card, Form, Input } from "antd";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { Shell } from "@/components/shared/shell";
import { api } from "@/lib/api";

type Credentials = { name?: string; phone?: string; email: string; password: string };

/** Cho khách đăng nhập hoặc tạo tài khoản; đầu vào: thông tin biểu mẫu, đầu ra: phiên trong tab và chuyển đến đơn hàng. Ví dụ: tài khoản mới đăng ký rồi đăng nhập tự động. */
export default function Page() {
  const router                  = useRouter();
  const [registering, setRegistering] = useState(false);
  const [saving, setSaving]     = useState(false);
  const [error, setError]       = useState("");

  useEffect(() => {
    // Nếu phiên còn hợp lệ, mở danh sách đơn; đầu vào: token đang lưu, đầu ra: điều hướng.
    // Ví dụ: khách đã đăng nhập không cần nhập mật khẩu lần nữa.
    if (!sessionStorage.getItem("nong-san-customer-token")) return;
    api("/auth/me").then(() => router.replace("/don-hang/lich-su")).catch(() => sessionStorage.removeItem("nong-san-customer-token"));
  }, [router]);

  /** Gửi biểu mẫu cho API xác thực; đầu vào: email, mật khẩu và thông tin đăng ký nếu có; đầu ra: phiên khách hàng. Ví dụ: đăng ký xong sẽ tự đăng nhập. */
  async function submit(values: Credentials) {
    setSaving(true);
    setError("");
    try {
      if (registering) await api("/auth/register", { method: "POST", body: JSON.stringify(values) });
      const result = await api<{ access_token: string; user: { role: string } }>("/auth/login", { method: "POST", body: JSON.stringify({ email: values.email, password: values.password }) });
      if (result.user.role !== "customer") throw new Error("Vui lòng dùng tài khoản khách hàng.");
      sessionStorage.setItem("nong-san-customer-token", result.access_token);
      router.replace("/don-hang/lich-su");
      router.refresh();
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể đăng nhập. Vui lòng thử lại.");
    } finally {
      setSaving(false);
    }
  }

  return <Shell><div className="mx-auto max-w-md py-8 sm:py-14"><Card className="rounded-3xl shadow-sm"><p className="eyebrow">Tài khoản Vườn Nhà</p><h1 className="mb-2 mt-2 text-3xl font-black text-forest">{registering ? "Tạo tài khoản" : "Đăng nhập"}</h1><p className="mb-6 text-sm text-stone-500">Theo dõi đơn hàng và đơn đặt trước của bạn.</p>{error && <Alert className="mb-5" type="error" showIcon message={error} />}<Form layout="vertical" onFinish={submit}>{registering && <><Form.Item name="name" label="Họ và tên" rules={[{ required: true, message: "Vui lòng nhập họ tên" }]}><Input autoComplete="name" /></Form.Item><Form.Item name="phone" label="Số điện thoại" rules={[{ required: true, message: "Vui lòng nhập số điện thoại" }]}><Input autoComplete="tel" /></Form.Item></>}<Form.Item name="email" label="Email" rules={[{ required: true, type: "email", message: "Vui lòng nhập email hợp lệ" }]}><Input autoComplete="email" /></Form.Item><Form.Item name="password" label="Mật khẩu" rules={[{ required: true, min: 8, message: "Mật khẩu cần ít nhất 8 ký tự" }]}><Input.Password autoComplete={registering ? "new-password" : "current-password"} /></Form.Item><Button className="w-full" type="primary" size="large" htmlType="submit" loading={saving}>{registering ? "Tạo tài khoản" : "Đăng nhập"}</Button></Form><button type="button" className="mt-5 font-semibold text-forest underline" onClick={() => { setRegistering(!registering); setError(""); }}>{registering ? "Đã có tài khoản? Đăng nhập" : "Chưa có tài khoản? Đăng ký"}</button><p className="mt-5 text-sm text-stone-500"><Link href="/san-pham">← Tiếp tục xem sản phẩm</Link></p></Card></div></Shell>;
}
