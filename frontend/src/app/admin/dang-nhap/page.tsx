"use client";

import { Alert, Button, Form, Input } from "antd";
import Link from "next/link";
import { useState } from "react";
import "../style.css";

/**
 * Đăng nhập phiên quản trị bằng tài khoản đã được cấp quyền ở backend.
 * Đầu vào: email và mật khẩu; đầu ra: chuyển đến /admin khi thành công.
 * Ví dụ: tài khoản khách hàng nhận thông báo không có quyền quản trị.
 */
export default function AdminLogin() {
  const [error, setError]     = useState("");
  const [loading, setLoading] = useState(false);

  async function submit(values: { email: string; password: string }) {
    setLoading(true);
    setError("");
    try {
      const response = await fetch("/api/admin-session", {
        method      : "POST",
        headers     : { "Content-Type": "application/json" },
        credentials : "include",
        body        : JSON.stringify(values),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.error?.message || "Đăng nhập thất bại.");
      window.location.href = "/admin";
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể kết nối API.");
    } finally {
      setLoading(false);
    }
  }

  return <main className="admin-login-page">
    <section className="admin-login-form-panel" aria-labelledby="login-title">
      <div className="admin-login-content">
        <Link href="/" className="admin-login-brand" aria-label="Về trang chủ cửa hàng nông sản">
          <img className="admin-login-brand-mark" src="/icon.svg" alt="" width={40} height={40} />
          <span>Cửa hàng nông sản</span>
        </Link>

        <div className="admin-login-heading">
          <span className="admin-login-eyebrow">KHU VỰC QUẢN TRỊ</span>
          <h1 id="login-title">Chào mừng trở lại</h1>
          <p>Đăng nhập để quản lý sản phẩm, đơn hàng và khách hàng của cửa hàng.</p>
        </div>

        {error && <Alert className="admin-login-error" type="error" message={error} showIcon role="alert" />}
        <Form layout="vertical" onFinish={submit} requiredMark={false} className="admin-login-form">
          <Form.Item name="email" label="Email quản trị" rules={[{ required: true, type: "email", message: "Nhập email hợp lệ" }]}>
            <Input size="large" autoComplete="username" placeholder="ten@cuahang.vn" />
          </Form.Item>
          <Form.Item name="password" label="Mật khẩu" rules={[{ required: true, message: "Nhập mật khẩu" }]}>
            <Input.Password size="large" autoComplete="current-password" placeholder="Nhập mật khẩu" />
          </Form.Item>
          <Button className="admin-login-submit" type="primary" htmlType="submit" size="large" loading={loading} block>
            Đăng nhập quản trị <span aria-hidden="true">→</span>
          </Button>
        </Form>
        <p className="admin-login-help">Chỉ tài khoản được cấp quyền quản trị mới có thể truy cập.</p>
        <Link href="/" className="admin-login-back">← Quay về cửa hàng</Link>
      </div>
    </section>

    <aside className="admin-login-visual" aria-hidden="true">
      <div className="admin-login-visual-shade" />
      <div className="admin-login-visual-content">
        <span className="admin-login-visual-kicker">NÔNG SẢN TƯƠI MỖI NGÀY</span>
        <p>Chăm chút từng sản phẩm, theo dõi từng đơn hàng.</p>
        <span className="admin-login-visual-rule" />
      </div>
    </aside>
  </main>;
}
