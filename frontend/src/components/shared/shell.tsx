"use client";

import { Input } from "antd";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import { useEffect, useState } from "react";
import { readCart } from "@/features/cart/storage";
import { api } from "@/lib/api";

/** Khung giao diện khách hàng. Đầu vào: nội dung trang; đầu ra: tìm kiếm, điều hướng và chân trang. Ví dụ: <Shell>Trang chủ</Shell>. */
export function Shell({ children }: { children: React.ReactNode }) {
  const router              = useRouter();
  const pathname            = usePathname();
  const [count, setCount]   = useState(0);
  const [search, setSearch] = useState("");
  const [customer, setCustomer] = useState<{ name: string } | null>(null);

  useEffect(() => {
    // Đếm số sản phẩm khác nhau, không cộng số lượng từng dòng trong giỏ.
    // Ví dụ: 3 kg cà rốt và 2 hộp cà chua làm huy hiệu hiển thị 2.
    const update = () => setCount(new Set(readCart().filter(line => line.quantity > 0).map(line => line.product_id)).size);
    update();
    window.addEventListener("cart-change", update);
    return () => window.removeEventListener("cart-change", update);
  }, []);

  useEffect(() => {
    // Kiểm tra phiên khách hàng khi mở trang; đầu vào: token trong tab, đầu ra: tên trên thanh điều hướng.
    // Ví dụ: token hết hạn sẽ hiện lại nút Đăng nhập.
    const token = sessionStorage.getItem("nong-san-customer-token");
    if (!token) return;
    api<{ name: string }>("/auth/me").then(setCustomer).catch(() => {
      sessionStorage.removeItem("nong-san-customer-token");
      setCustomer(null);
    });
  }, []);

  /** Đăng xuất tài khoản trong tab; đầu vào: thao tác bấm nút, đầu ra: xóa phiên và tải lại trang. Ví dụ: sau đăng xuất, danh sách đơn yêu cầu đăng nhập lại. */
  function signOut() {
    sessionStorage.removeItem("nong-san-customer-token");
    setCustomer(null);
    window.location.assign("/");
  }

  return <div className="store-shell min-h-screen text-stone-900">
    <div className="bg-forest px-4 py-2 text-center text-xs font-medium tracking-wide text-white sm:text-sm">Nông sản tươi theo mùa · Thông tin nguồn gốc rõ ràng trên từng sản phẩm</div>
    <header className="sticky top-0 z-30 border-b border-stone-200 bg-white/95 backdrop-blur">
      <div className="mx-auto flex max-w-7xl flex-wrap items-center gap-x-5 gap-y-3 px-4 py-3 xl:flex-nowrap xl:gap-6">
        <Link href="/" className="flex shrink-0 items-center gap-2 text-2xl font-black tracking-tight text-forest"><img className="brand-mark" src="/icon.svg" alt="" width={36} height={36} /><span>Vườn Nhà</span></Link>
        <Input.Search className="order-3 w-full xl:order-none xl:min-w-0 xl:flex-1" placeholder="Hôm nay bạn muốn tìm gì?" value={search} onChange={event => setSearch(event.target.value)} onSearch={value => router.push(`/san-pham?q=${encodeURIComponent(value.trim())}`)} enterButton="Tìm" size="large" />
        <nav className="store-nav ml-auto flex shrink-0 items-center gap-4 text-sm font-semibold xl:gap-5">
          <Link href="/san-pham" className={pathname.startsWith("/san-pham") ? "store-nav-active" : undefined} aria-current={pathname.startsWith("/san-pham") ? "page" : undefined}>Sản phẩm</Link>
          <Link href="/don-hang/lich-su" className={pathname.startsWith("/don-hang") ? "store-nav-active" : undefined} aria-current={pathname.startsWith("/don-hang") ? "page" : undefined}>Đơn hàng</Link>
          <Link href="/gio-hang" className={`cart-link${pathname === "/gio-hang" || pathname.startsWith("/thanh-toan") ? " store-nav-active" : ""}`} aria-current={pathname === "/gio-hang" || pathname.startsWith("/thanh-toan") ? "page" : undefined}>Giỏ hàng <span>{count}</span></Link>
          {customer ? <div className="store-account"><span className="store-account-name" title={customer.name}>{customer.name}</span><button type="button" onClick={signOut}>Đăng xuất</button></div> : <Link href="/dang-nhap" className="store-login">Đăng nhập</Link>}
        </nav>
      </div>
    </header>
    <main className="mx-auto max-w-7xl px-4 pb-14 pt-6 md:pt-8">{children}</main>
    <footer className="bg-forest px-4 py-12 text-green-50"><div className="mx-auto grid max-w-7xl gap-8 md:grid-cols-3"><div><p className="flex items-center gap-2 text-2xl font-bold"><img src="/icon.svg" alt="" width={36} height={36} />Vườn Nhà</p><p className="mt-3 max-w-xs text-sm text-green-100">Nông sản gần gũi cho bữa ăn mỗi ngày. Chọn món ngon từ những thông tin minh bạch.</p></div><div><h3 className="font-bold">Khám phá</h3><div className="mt-3 flex flex-col gap-2 text-sm"><Link href="/san-pham">Tất cả sản phẩm</Link><Link href="/gio-hang">Giỏ hàng của bạn</Link><Link href="/don-hang/lich-su">Lịch sử đơn hàng</Link><Link href="/don-hang/dat-truoc">Đơn đặt trước</Link></div></div><div><h3 className="font-bold">Giá trị minh bạch</h3><p className="mt-3 text-sm text-green-100">Xem giá và ưu đãi trước khi đặt hàng. Khám phá vùng trồng, lô hàng của từng sản phẩm.</p></div></div></footer>
  </div>;
}
