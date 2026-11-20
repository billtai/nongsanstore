"use client";

import { Alert, Button, Card, Empty, Form, Input, Radio, Space } from "antd";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { money } from "@/lib/format";
import { readCart, writeCart } from "@/features/cart/storage";
import { Shell } from "@/components/shared/shell";
import { BrandLoading } from "@/components/shared/brand-loading";
import type { CartLine, Order, Quote } from "@/types/store";

type CheckoutValues = {
  name         : string;
  phone        : string;
  email?       : string;
  address      : string;
  coupon_code? : string;
};

type LoginValues = { email: string; password: string; name?: string; phone?: string };
type CustomerProfile = { name: string; phone: string; email: string };

/**
 * Lấy báo giá và xác nhận đơn COD sau khi khách đăng nhập.
 * Đầu vào: giỏ cục bộ, địa chỉ và mã giảm; đầu ra: báo giá server và đơn mới.
 * Ví dụ: báo giá 2 kg cà rốt rồi xác nhận bằng quote_id trong 15 phút.
 */
export function Checkout({ kind = "regular" }: { kind?: "regular" | "preorder" }) {
  const router                          = useRouter();
  const [form]                          = Form.useForm<CheckoutValues>();
  const [loginForm]                     = Form.useForm<LoginValues>();
  const [lines, setLines]               = useState<CartLine[]>([]);
  const [quote, setQuote]               = useState<Quote>();
  const [baseQuote, setBaseQuote]       = useState<Quote>();
  const [quoteError, setQuoteError]     = useState("");
  const [quoteLoading, setQuoteLoading] = useState(false);
  const [quoteReload, setQuoteReload]   = useState(0);
  const [signedIn, setSignedIn]         = useState(false);
  const [registering, setRegistering]   = useState(false);
  const [error, setError]               = useState("");
  const [loading, setLoading]           = useState(false);
  const [paymentMethod, setPaymentMethod] = useState<"cod" | "momo" | "sepay_bank">("cod");
  const [momoEnabled, setMomoEnabled]   = useState(false);
  const [sepayEnabled, setSepayEnabled] = useState(false);
  const [checkingAccount, setCheckingAccount] = useState(true);
  const couponCode                      = Form.useWatch("coupon_code", form);
  const displayedQuote                  = quote || baseQuote;

  /** Điền địa chỉ của đơn mới nhất nếu khách chưa nhập địa chỉ mới.
   * Đầu vào: token của tài khoản vừa xác thực; đầu ra: cập nhật trường address.
   * Ví dụ: đơn gần nhất giao tới "Đà Lạt, Lâm Đồng" sẽ điền nguyên văn địa chỉ đó.
   */
  async function prefillLastDeliveryAddress(token: string) {
    try {
      const result = await api<{ items: Pick<Order, "delivery_address">[] }>("/orders?page=1&limit=1");
      const address = result.items[0]?.delivery_address;
      if (sessionStorage.getItem("nong-san-customer-token") !== token) return;
      if (!form.isFieldTouched("address") && !form.getFieldValue("address") && address) {
        form.setFieldValue("address", address);
      }
    } catch {
      // Tài khoản chưa có đơn hoặc API tạm lỗi: khách vẫn tự điền địa chỉ như trước.
    }
  }

  useEffect(() => {
    // Đầu vào: cấu hình backend; đầu ra: chỉ hiển thị MoMo Test khi đủ khóa và callback HTTPS.
    // Ví dụ: backend chưa đặt MOMO_SECRET_KEY thì chỉ còn lựa chọn COD.
    api<{ items: string[] }>("/orders/payment-methods")
      .then(result => {
        setMomoEnabled(result.items.includes("momo"));
        setSepayEnabled(result.items.includes("sepay_bank"));
      })
      .catch(() => { setMomoEnabled(false); setSepayEnabled(false); });
    // Mỗi lần thanh toán chỉ lấy một nhóm; ví dụ: /thanh-toan/dat-truoc không chứa hàng có sẵn.
    setLines(readCart().filter(line => Boolean(line.preorder) === (kind === "preorder")));
    const token = sessionStorage.getItem("nong-san-customer-token");
    if (!token) { setCheckingAccount(false); return; }
    // Lấy dữ liệu từ tài khoản đã đăng nhập để điền sẵn thông tin người nhận.
    // Ví dụ: tài khoản có tên và số điện thoại sẽ hiện hai giá trị này trong biểu mẫu giao hàng.
    api<CustomerProfile>("/auth/me")
      .then((customer) => {
        form.setFieldsValue({ name: customer.name, phone: customer.phone, email: customer.email });
        setSignedIn(true);
        void prefillLastDeliveryAddress(token);
      })
      .catch(() => {
        sessionStorage.removeItem("nong-san-customer-token");
        setSignedIn(false);
      }).finally(() => setCheckingAccount(false));
  }, [form, kind]);

  useEffect(() => {
    // Tự lấy báo giá sau đăng nhập và khi đổi mã; đầu vào giỏ/mã, đầu ra giá từ backend.
    // Ví dụ: nhập GIAM10, sau 600 ms giao diện hiện mức giảm do /orders/quote trả về.
    if (!signedIn || !lines.length) return;
    const code       = String(couponCode || "").trim();
    const controller = new AbortController();
    const timer      = window.setTimeout(async () => {
      setQuoteLoading(true);
      setQuoteError("");
      try {
        const result = await api<Quote>("/orders/quote", {
          method : "POST",
          body   : JSON.stringify({ items: lines, discount_code: code || null }),
          signal : controller.signal,
        });
        if (result.is_preorder !== (kind === "preorder")) throw new Error("Giỏ hàng đã thay đổi. Vui lòng quay lại giỏ hàng.");
        setQuote(result);
        if (result.is_preorder) setPaymentMethod("cod");
        if (!code) setBaseQuote(result);
      } catch (reason) {
        if (controller.signal.aborted) return;
        setQuote(undefined);
        setQuoteError(reason instanceof Error ? reason.message : "Không thể kiểm tra báo giá.");
      } finally {
        if (!controller.signal.aborted) setQuoteLoading(false);
      }
    }, code ? 600 : 0);
    return () => { window.clearTimeout(timer); controller.abort(); };
  }, [signedIn, lines, couponCode, quoteReload]);

  async function signIn(values: LoginValues) {
    /** Đầu vào: thông tin tài khoản; đầu ra: Bearer token lưu trong tab hiện tại. */
    setLoading(true);
    setError("");
    try {
      if (registering) {
        await api("/auth/register", { method: "POST", body: JSON.stringify({ name: values.name, phone: values.phone, email: values.email, password: values.password }) });
      }
      const result = await api<{ access_token: string }>("/auth/login", { method: "POST", body: JSON.stringify({ email: values.email, password: values.password }) });
      sessionStorage.setItem("nong-san-customer-token", result.access_token);
      // Đầu vào: token vừa đăng nhập; đầu ra: tên, email, điện thoại đúng theo tài khoản.
      // Ví dụ: đăng nhập tài khoản cũ vẫn tự điền tên dù biểu mẫu đăng nhập chỉ có email.
      const customer = await api<CustomerProfile>("/auth/me");
      form.setFieldsValue({ name: customer.name, phone: customer.phone, email: customer.email });
      setSignedIn(true);
      await prefillLastDeliveryAddress(result.access_token);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể đăng nhập.");
    } finally {
      setLoading(false);
    }
  }

  async function confirmOrder() {
    /** Đầu vào: quote_id, địa chỉ, phương thức; đầu ra: đơn COD hoặc pay_url MoMo Test. */
    if (!quote) return;
    setLoading(true);
    setError("");
    try {
      const values = await form.validateFields();
      const order  = await api<Order>("/orders/confirm", {
        method : "POST",
        body   : JSON.stringify({
          quote_id         : quote.quote_id,
          recipient_name   : values.name,
          recipient_phone  : values.phone,
          delivery_address : values.address.trim(),
          payment_method   : paymentMethod,
        }),
      });
      // Giữ nguyên nhóm còn lại sau khi tạo đơn; ví dụ: đặt trước xong vẫn còn hàng có sẵn trong giỏ.
      const orderedIds = new Set(lines.map(line => line.product_id));
      writeCart(readCart().filter(line => !orderedIds.has(line.product_id)));
      if (paymentMethod === "momo") {
        if (order.pay_url?.startsWith("https://test-payment.momo.vn/")) window.location.assign(order.pay_url);
        else router.push(`/don-hang/${encodeURIComponent(order.order_code)}`);
      } else {
        router.push(`/don-hang/${encodeURIComponent(order.order_code)}`);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Đặt hàng thất bại.");
      setQuote(undefined);
      setQuoteReload(value => value + 1);
    } finally {
      setLoading(false);
    }
  }

  return <Shell>
    <h1 className="mb-2 text-3xl font-bold">{kind === "preorder" ? "Xác nhận đặt trước" : "Thanh toán hàng có sẵn"}</h1>
    <p className="mb-7 text-sm text-stone-500">{kind === "preorder" ? "Đơn đặt trước được xử lý khi hàng về. Hàng có sẵn trong giỏ được đặt riêng." : "Hàng có sẵn được xử lý riêng để không phải chờ sản phẩm đặt trước."}</p>
    {checkingAccount ? <BrandLoading label="Đang kiểm tra tài khoản..." /> : !lines.length ? <Empty description={kind === "preorder" ? "Không có sản phẩm đặt trước" : "Không có sản phẩm có sẵn"}><Button href="/gio-hang">Quay lại giỏ hàng</Button></Empty> : <div className="grid gap-8 lg:grid-cols-2">
      <div className="space-y-5">
        <Card title={signedIn ? "Tài khoản khách hàng" : "Đăng nhập để đặt hàng"}>
          {signedIn ? <Button onClick={() => { sessionStorage.removeItem("nong-san-customer-token"); form.resetFields(); setSignedIn(false); setQuote(undefined); setBaseQuote(undefined); setQuoteError(""); setQuoteLoading(false); }}>Đổi tài khoản</Button> : <Form form={loginForm} layout="vertical" onFinish={signIn}>
            {registering && <><Form.Item name="name" label="Họ và tên" rules={[{ required: true }]}><Input /></Form.Item><Form.Item name="phone" label="Số điện thoại" rules={[{ required: true }]}><Input /></Form.Item></>}
            <Form.Item name="email" label="Email" rules={[{ required: true, type: "email" }]}><Input /></Form.Item>
            <Form.Item name="password" label="Mật khẩu" rules={[{ required: true, min: 8 }]}><Input.Password /></Form.Item>
            <Space><Button type="primary" htmlType="submit" loading={loading}>{registering ? "Tạo tài khoản" : "Đăng nhập"}</Button><Button onClick={() => setRegistering(!registering)}>{registering ? "Đã có tài khoản" : "Tạo tài khoản mới"}</Button></Space>
          </Form>}
        </Card>
        <Card title="Thông tin giao hàng"><Form form={form} layout="vertical" onValuesChange={changed => { if ("coupon_code" in changed) { setQuote(undefined); setQuoteError(""); } }}>
          <Form.Item name="name" label="Họ và tên" rules={[{ required: true, message: "Vui lòng nhập họ tên" }]}><Input /></Form.Item>
          <Form.Item name="phone" label="Số điện thoại" rules={[{ required: true, message: "Vui lòng nhập số điện thoại" }]}><Input /></Form.Item>
          <Form.Item name="email" label="Email" rules={[{ type: "email" }]}><Input /></Form.Item>
          <Form.Item name="address" label="Địa chỉ giao hàng đầy đủ" rules={[{ required: true, message: "Vui lòng nhập địa chỉ" }]}><Input.TextArea rows={3} placeholder="Số nhà, đường, phường/xã, tỉnh/thành phố" /></Form.Item>
          <Form.Item name="coupon_code" label="Mã giảm giá" validateStatus={quoteError && couponCode ? "error" : quote && couponCode ? "success" : undefined} help={quoteError && couponCode ? quoteError : quote && couponCode ? `Đã áp dụng mã, giảm ${money(quote.discount_vnd)}.` : "Mã sẽ được kiểm tra tự động khi bạn nhập."}><Input placeholder="Nếu có" /></Form.Item>
        </Form></Card>
      </div>
      <Card title="Tóm tắt đơn hàng">
        {displayedQuote ? <><div className="space-y-2">{displayedQuote.items.map((item) => <div key={item.product_id} className="flex justify-between gap-3"><span>{item.name} × {item.quantity} {item.unit}{item.preorder && <span className="ml-2 rounded-full bg-amber-100 px-2 py-0.5 text-xs font-semibold text-amber-900">Đặt trước</span>}</span><span>{money(item.line_total_vnd)}</span></div>)}</div>
          <div className="mt-5 space-y-2 border-t pt-4"><p className="flex justify-between"><span>Tiền hàng</span><span>{money(displayedQuote.subtotal_vnd)}</span></p><p className="flex justify-between"><span>Giảm giá</span><span>−{money(displayedQuote.discount_vnd)}</span></p><p className="flex justify-between"><span>Phí giao hàng</span><span>{displayedQuote.shipping_fee_vnd === null ? "Chưa xác định" : money(displayedQuote.shipping_fee_vnd)}</span></p><p className="flex justify-between text-lg font-bold"><span>{displayedQuote.is_preorder ? "Tổng tiền dự kiến" : "Tiền hàng sau giảm giá"}</span><span>{money(displayedQuote.total_vnd)}</span></p></div>
          <Alert className="mt-4" type="info" showIcon message="Phí giao hàng chưa được xác định; số tiền trên chưa bao gồm phí giao hàng." />
          {displayedQuote.is_preorder && <Alert className="mt-3" type="warning" showIcon message="Giá đặt trước là dự kiến" description="Khi hàng về, cửa hàng sẽ gửi giá mới để bạn so sánh và đồng ý trước khi xác nhận đơn. Bạn có thể hủy nếu không đồng ý." />}
        </> : signedIn ? quoteError ? <Alert type="error" showIcon message="Chưa thể hiển thị tổng tiền" description="Vui lòng kiểm tra mã giảm giá hoặc thử lại sau." /> : <BrandLoading label="Đang tính tổng tiền..." /> : <p className="text-stone-500">Đăng nhập để xem tổng tiền và ưu đãi của đơn hàng.</p>}
        {quoteLoading && displayedQuote && <div className="mt-3"><BrandLoading compact label="Đang kiểm tra mã và cập nhật báo giá..." /></div>}
        {quoteError && !couponCode && displayedQuote && <Alert className="mt-4" type="error" showIcon message={quoteError} />}
        {error && <Alert className="mt-5" type="error" showIcon message={error} />}
        <div className="mt-5"><p className="mb-2 font-semibold">Phương thức thanh toán</p><Radio.Group value={paymentMethod} onChange={event => setPaymentMethod(event.target.value)}><Space direction="vertical"><Radio value="cod">Thanh toán khi nhận hàng</Radio>{!displayedQuote?.is_preorder && momoEnabled && <Radio value="momo">Ví MoMo Test</Radio>}{!displayedQuote?.is_preorder && sepayEnabled && <Radio value="sepay_bank">Quét QR chuyển khoản ngân hàng</Radio>}</Space></Radio.Group></div>
        {paymentMethod !== "cod" && <Alert className="mt-4" type="info" showIcon message="Chỉ thanh toán tiền hàng sau giảm giá; phí giao hàng chưa được xác định." />}
        <Button className="mt-6" type="primary" onClick={confirmOrder} loading={loading} disabled={!quote || !signedIn || quoteLoading}>{quote?.is_preorder ? "Xác nhận đặt trước" : paymentMethod === "momo" ? "Tiếp tục tới MoMo Test" : paymentMethod === "sepay_bank" ? "Tạo đơn và xem mã QR" : "Xác nhận đặt hàng COD"}</Button>
        {loading && <div className="mt-3"><BrandLoading compact label="Đang xử lý yêu cầu của bạn..." /></div>}
      </Card>
    </div>}
  </Shell>;
}
