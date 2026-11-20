"use client";

import { Alert, Button, Card, DatePicker, Drawer, Empty, Form, Input, InputNumber, Layout, Modal, Select, Space, Table, Tag, Typography, Upload, message } from "antd";
import dayjs from "dayjs";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useState } from "react";
import "@/app/admin/style.css";
import { AdminFormFields } from "./form-fields";
import { adminApi as api } from "./api";
import { statusText, nextStatus, money, day } from "./constants";
import type { Row, Section, PageData } from "./types";
import { ProcurementPanel } from "./procurement";
import { AdminOverview } from "./overview";

const sectionMeta: Record<Section, { label: string; subtitle: string; icon: string }> = {
  overview    : { label: "Trang chủ", subtitle: "Số đơn và xu hướng đặt hàng", icon: "⌂" },
  products    : { label: "Sản phẩm", subtitle: "Danh mục, giá bán và trạng thái hiển thị", icon: "◫" },
  batches     : { label: "Lô nông sản", subtitle: "Nguồn gốc, ngày thu hoạch và tồn kho", icon: "▤" },
  orders      : { label: "Đơn hàng", subtitle: "Theo dõi và xử lý đơn mua hàng", icon: "▣" },
  preorders   : { label: "Đơn đặt trước", subtitle: "Theo dõi đơn đặt trước và đề xuất giá", icon: "◷" },
  discounts   : { label: "Mã giảm giá", subtitle: "Ưu đãi và các đơn đã sử dụng", icon: "◇" },
  customers   : { label: "Khách hàng", subtitle: "Thông tin khách và lịch sử mua", icon: "◎" },
  units       : { label: "Đơn vị", subtitle: "Đơn vị đo lường dùng cho sản phẩm", icon: "⊞" },
  procurement : { label: "Nhà cung cấp & nhập hàng", subtitle: "Nhà cung cấp, đơn nhập và nhận hàng", icon: "↟" },
};

const navigationGroups: { label: string; sections: Section[] }[] = [
  { label: "TỔNG QUAN", sections: ["overview"] },
  { label: "BÁN HÀNG", sections: ["orders", "preorders", "customers", "discounts"] },
  { label: "KHO & SẢN PHẨM", sections: ["products", "batches", "units", "procurement"] },
];

/**
 * Hiển thị bảng quản trị và chỉ tải đúng trang, bộ lọc đang xem từ API.
 * Đầu vào: thao tác của người dùng; đầu ra: bảng, form và thông báo tương ứng.
 * Ví dụ: tìm 'rau' gửi q=rau lên /admin/products, không lọc trên dữ liệu đã tải.
 */
export function AdminDashboard() {
  const [section, setSection]       = useState<Section>("overview");
  const [sidebarOpen, setSidebarOpen] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);
  const [rows, setRows]             = useState<Row[]>([]);
  const [total, setTotal]           = useState(0);
  const [page, setPage]             = useState(1);
  const [query, setQuery]           = useState("");
  const [search, setSearch]         = useState("");
  const [filter, setFilter]         = useState("");
  const [orderDate, setOrderDate]   = useState("");
  const [loading, setLoading]       = useState(false);
  const [error, setError]           = useState("");
  const [editing, setEditing]       = useState<Row | null>(null);
  const [drawer, setDrawer]         = useState(false);
  const [detail, setDetail]         = useState<Row | null>(null);
  const [pendingStatus, setPendingStatus] = useState<string | null>(null);
  const [statusSaving, setStatusSaving]   = useState(false);
  const [bankConfirmOpen, setBankConfirmOpen] = useState(false);
  const [bankConfirmSaving, setBankConfirmSaving] = useState(false);
  const [proposalSaving, setProposalSaving] = useState(false);
  const [statusConfirmOpen, setStatusConfirmOpen] = useState(false);
  const [historyPage, setHistoryPage] = useState(1);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyRows, setHistoryRows] = useState<Row[]>([]);
  const [customerOrder, setCustomerOrder] = useState<Row | null>(null);
  const [customerOrderLoading, setCustomerOrderLoading] = useState(false);
  const [discountHistory, setDiscountHistory] = useState<Row | null>(null);
  const [discountOrders, setDiscountOrders]   = useState<Row[]>([]);
  const [discountPage, setDiscountPage]       = useState(1);
  const [discountTotal, setDiscountTotal]     = useState(0);
  const [discountLoading, setDiscountLoading] = useState(false);
  const [discountError, setDiscountError]     = useState("");
  const [pendingAction, setPendingAction]     = useState<{ row: Row; label: string; path: string; method: string; body?: object } | null>(null);
  const [saving, setSaving]         = useState(false);
  const [mainFile, setMainFile]     = useState<File | null>(null);
  const [detailFiles, setDetailFiles] = useState<File[]>([]);
  const [removedImageIds, setRemovedImageIds] = useState<number[]>([]);
  const [form]                      = Form.useForm();
  const [notice, noticeContext]     = message.useMessage();

  const load = useCallback(async () => {
    if (section === "procurement" || section === "overview") return;
    setLoading(true);
    setError("");
    try {
      const params = new URLSearchParams({ page: String(page), limit: "10" });
      if (search) params.set("q", search);
      if (filter) params.set(["orders", "preorders"].includes(section) ? "status" : ["products", "batches"].includes(section) ? "visible" : "active", filter);
      if (section === "orders" || section === "preorders") params.set("kind", section === "preorders" ? "preorder" : "regular");
      if ((section === "orders" || section === "preorders") && orderDate) params.set("date", orderDate);
      const endpoint       = section === "preorders" ? "orders" : section;
      const data: PageData = await api(`/admin/${endpoint}?${params}`);
      setRows(data.items);
      setTotal(data.total);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Không thể tải dữ liệu.");
      setRows([]);
      setTotal(0);
    } finally {
      setLoading(false);
    }
  }, [section, page, search, filter, orderDate]);

  useEffect(() => { void load(); }, [load]);

  useEffect(() => {
    // Đầu vào: thay đổi chiều rộng trình duyệt; đầu ra: trạng thái menu phù hợp màn hình.
    // Ví dụ: thu gọn menu ở máy tính rồi chuyển sang 390px sẽ mở menu di động bình thường.
    const syncSidebar = () => {
      if (window.innerWidth <= 900) setSidebarCollapsed(false);
      else setSidebarOpen(false);
    };
    window.addEventListener("resize", syncSidebar);
    return () => window.removeEventListener("resize", syncSidebar);
  }, []);

  function changeSection(key: string) {
    setSection(key as Section);
    setSidebarOpen(false);
    setPage(1);
    setQuery("");
    setSearch("");
    setFilter("");
    setOrderDate("");
    setDetail(null);
    setCustomerOrder(null);
    setPendingStatus(null);
    setDiscountHistory(null);
  }

  function openForm(row?: Row) {
    setEditing(row || null);
    setMainFile(null);
    setDetailFiles([]);
    setRemovedImageIds([]);
    form.resetFields();
    if (row) form.setFieldsValue({ ...row, harvest_date: row.harvest_date?.slice(0, 10), starts_at: row.starts_at?.slice(0, 16), ends_at: row.ends_at?.slice(0, 16) });
    setDrawer(true);
  }

  async function saveForm(values: Row) {
    setSaving(true);
    try {
      const saved = await api(`/admin/${section}${editing ? `/${editing.id}` : ""}`, {
        method  : editing ? "PATCH" : "POST",
        headers : { "Content-Type": "application/json" },
        body    : JSON.stringify(section === "batches" ? {
          product_id     : values.product_id,
          growing_region : values.growing_region,
          origin         : values.origin,
          harvest_date   : values.harvest_date,
          quantity       : values.remaining_quantity,
        } : section === "products" && editing ? { name: values.name, category: values.category, description: values.description, price_vnd: values.price_vnd, unit: values.unit }
          : section === "units" && editing ? { allows_fraction: values.allows_fraction } : values),
      });
      if (section === "products" && (mainFile || detailFiles.length || removedImageIds.length)) {
        // Đầu vào: ảnh mới và ID ảnh bỏ; đầu ra: ảnh được lưu cùng sản phẩm vừa tạo/sửa.
        // Ví dụ: một ảnh chính và hai ảnh chi tiết gửi bằng multipart/form-data.
        const images = new FormData();
        if (mainFile) images.append("main", mainFile);
        detailFiles.forEach((file) => images.append("details", file));
        images.append("remove_ids", JSON.stringify(removedImageIds));
        try {
          await api(`/admin/products/${saved.id}/images`, { method: "POST", body: images });
        } catch (reason) {
          setEditing(saved);
          void load();
          throw new Error(`Đã lưu sản phẩm nhưng chưa lưu ảnh: ${reason instanceof Error ? reason.message : "lỗi tải ảnh"}`);
        }
      }
      notice.success(editing ? "Đã cập nhật." : "Đã thêm mới.");
      setDrawer(false);
      void load();
    } catch (reason) {
      notice.error(reason instanceof Error ? reason.message : "Không thể lưu.");
    } finally {
      setSaving(false);
    }
  }

  function confirmAction(row: Row, label: string, path: string, method: string, body?: object) {
    setPendingAction({ row, label, path, method, body });
  }

  /** Thực hiện thao tác đã xác nhận; đầu vào pendingAction, đầu ra bảng mới. Ví dụ ẩn lô #2. */
  async function runConfirmedAction() {
    if (!pendingAction) return;
    setSaving(true);
    try {
      await api(pendingAction.path, { method: pendingAction.method, headers: { "Content-Type": "application/json" }, body: pendingAction.body ? JSON.stringify(pendingAction.body) : undefined });
      notice.success(`Đã ${pendingAction.label}.`);
      setPendingAction(null);
      void load();
    } catch (reason) { notice.error(reason instanceof Error ? reason.message : "Thao tác thất bại."); }
    finally { setSaving(false); }
  }

  /** Lấy một trang đơn dùng mã giảm giá; đầu vào mã/trang, đầu ra danh sách. Ví dụ mã #3 trang 2. */
  async function showDiscountOrders(discount: Row, targetPage = 1) {
    setDiscountHistory(discount);
    setDiscountPage(targetPage);
    setDiscountLoading(true);
    setDiscountError("");
    try {
      const data: PageData = await api(`/admin/discounts/${discount.id}/orders?page=${targetPage}&limit=10`);
      setDiscountOrders(data.items);
      setDiscountTotal(data.total);
    } catch (reason) {
      setDiscountOrders([]);
      setDiscountTotal(0);
      setDiscountError(reason instanceof Error ? reason.message : "Không thể tải đơn dùng mã.");
    } finally { setDiscountLoading(false); }
  }

  async function showOrder(id: number) {
    setDetail(null);
    setPendingStatus(null);
    try { setDetail(await api(`/admin/orders/${id}`)); }
    catch (reason) { notice.error(reason instanceof Error ? reason.message : "Không thể tải đơn."); }
  }

  async function showCustomer(id: number, targetPage = 1) {
    try {
      const data: PageData = await api(`/admin/customers/${id}/orders?page=${targetPage}&limit=10`);
      setHistoryRows(data.items);
      setHistoryTotal(data.total);
      setHistoryPage(targetPage);
      setDetail({ id, name: rows.find((row) => row.id === id)?.name || detail?.name });
    } catch (reason) { notice.error(reason instanceof Error ? reason.message : "Không thể tải lịch sử."); }
  }

  /**
   * Lấy chi tiết một đơn từ lịch sử mua của khách hàng.
   * Đầu vào: ID đơn; đầu ra: mở chi tiết hoặc báo lỗi.
   * Ví dụ: bấm đơn #12 gọi GET /admin/orders/12.
   */
  async function showCustomerOrder(id: number) {
    setCustomerOrderLoading(true);
    try {
      setCustomerOrder(await api(`/admin/orders/${id}`));
    } catch (reason) {
      notice.error(reason instanceof Error ? reason.message : "Không thể tải chi tiết đơn.");
    } finally {
      setCustomerOrderLoading(false);
    }
  }

  async function updateStatus() {
    if (!detail || !pendingStatus) return;
    setStatusSaving(true);
    try {
      const updated = await api(`/admin/orders/${detail.id}/transitions`, {
        method  : "POST",
        headers : { "Content-Type": "application/json" },
        body    : JSON.stringify({ to_status: pendingStatus }),
      });
      setDetail(updated);
      setPendingStatus(null);
      setStatusConfirmOpen(false);
      notice.success("Đã cập nhật trạng thái.");
      void load();
    } catch (reason) {
      notice.error(reason instanceof Error ? reason.message : "Không thể đổi trạng thái.");
    } finally {
      setStatusSaving(false);
    }
  }

  /** Xác nhận khoản tiền đã đối soát trên sao kê; đầu vào đơn QR đang chờ, đầu ra đơn paid. Ví dụ: admin kiểm tra đúng 235.200đ rồi xác nhận. */
  async function confirmBankPayment() {
    if (!detail) return;
    setBankConfirmSaving(true);
    try {
      const updated = await api(`/admin/orders/${detail.id}/confirm-bank-payment`, { method: "POST" });
      setDetail(updated);
      setBankConfirmOpen(false);
      notice.success("Đã xác nhận nhận tiền. Có thể tiếp tục xử lý đơn.");
      void load();
    } catch (reason) {
      notice.error(reason instanceof Error ? reason.message : "Không thể xác nhận khoản chuyển.");
    } finally {
      setBankConfirmSaving(false);
    }
  }

  /** Gửi giá hiện tại của hàng đã về cho khách duyệt; đầu vào: đơn đặt trước đang chờ, đầu ra: đề xuất giá API. Ví dụ: giá tăng sẽ hiển thị cả giá cũ và mới trong chi tiết đơn. */
  async function proposePrice() {
    if (!detail) return;
    setProposalSaving(true);
    try {
      const updated = await api(`/admin/orders/${detail.id}/price-proposal`, { method: "POST" });
      setDetail(updated);
      notice.success("Đã gửi giá mới để khách xác nhận.");
      void load();
    } catch (reason) {
      notice.error(reason instanceof Error ? reason.message : "Không thể gửi giá.");
    } finally {
      setProposalSaving(false);
    }
  }

  const actions = (row: Row) => <Space size={6} wrap={section !== "batches"} className={section === "batches" ? "admin-batch-actions" : undefined}>
    {(section === "orders" || section === "preorders") && <Button size="small" onClick={() => void showOrder(row.id)}>Chi tiết</Button>}
    {section === "customers" && <Button size="small" onClick={() => void showCustomer(row.id)}>Lịch sử mua</Button>}
    {["products", "batches", "discounts", "units"].includes(section) && <Button size="small" onClick={() => openForm(row)}>Sửa</Button>}
    {section === "products" && <Button size="small" danger={row.is_visible} onClick={() => confirmAction(row, row.is_visible ? "ẩn" : "hiện", `/admin/products/${row.id}`, "PATCH", { is_visible: !row.is_visible })}>{row.is_visible ? "Ẩn" : "Hiện"}</Button>}
    {section === "batches" && <Button size="small" danger={row.is_visible} onClick={() => confirmAction(row, row.is_visible ? "ẩn lô" : "hiện lô", `/admin/batches/${row.id}`, "PATCH", { is_visible: !row.is_visible })}>{row.is_visible ? "Ẩn" : "Hiện"}</Button>}
    {section === "batches" && <Button size="small" danger onClick={() => confirmAction(row, "xóa lô", `/admin/batches/${row.id}`, "DELETE")}>Xóa</Button>}
    {section === "discounts" && <Button size="small" danger={row.is_active} onClick={() => confirmAction(row, row.is_active ? "tắt mã" : "bật mã", `/admin/discounts/${row.id}`, "PATCH", { is_active: !row.is_active })}>{row.is_active ? "Tắt" : "Bật"}</Button>}
    {section === "discounts" && <Button size="small" onClick={() => void showDiscountOrders(row)}>Đơn đã dùng</Button>}
    {section === "units" && <Button size="small" danger={row.is_active} onClick={() => confirmAction(row, row.is_active ? "tắt đơn vị" : "bật đơn vị", `/admin/units/${row.id}`, "PATCH", { is_active: !row.is_active })}>{row.is_active ? "Tắt" : "Bật"}</Button>}
    {section === "units" && !row.product_count && <Button size="small" danger onClick={() => confirmAction(row, "xóa đơn vị", `/admin/units/${row.id}`, "DELETE")}>Xóa</Button>}
  </Space>;

  const sectionColumns: Record<Section, ColumnsType<Row>> = {
    products: [
      { title: "Ảnh chính", dataIndex: "image_url", render: (url: string | null, row: Row) => url ? <img src={url} alt={row.name} className="h-12 w-12 rounded object-cover" /> : "Chưa có" },
      { title: "Sản phẩm", dataIndex: "name" }, { title: "Danh mục", dataIndex: "category" }, { title: "Đơn vị", dataIndex: "unit" }, { title: "Giá", dataIndex: "price_vnd", render: money },
      { title: "Hiển thị", dataIndex: "is_visible", render: (value: boolean) => <Tag color={value ? "green" : "default"}>{value ? "Đang bán" : "Đã ẩn"}</Tag> },
    ],
    batches: [
      { title: "Mã lô", dataIndex: "batch_code", width: 340, ellipsis: true }, { title: "Sản phẩm", dataIndex: "product_name", width: 160 }, { title: "Vùng trồng", dataIndex: "growing_region", width: 160 },
      { title: "Ngày thu hoạch", dataIndex: "harvest_date", render: day, width: 130 },
      { title: "Còn lại", dataIndex: "remaining_quantity", width: 130, render: (value: string, row: Row) => `${Number(value).toLocaleString("vi-VN", { maximumFractionDigits: 3 })} ${row.unit || ""}`.trim() },
      { title: "Hiển thị", dataIndex: "is_visible", width: 130, render: (value: boolean) => <Tag color={value ? "green" : "default"}>{value ? "Đang dùng" : "Đã ẩn"}</Tag> },
    ],
    orders: [
      { title: "Mã đơn", dataIndex: "order_code" }, { title: "Người nhận", dataIndex: "recipient_name" },
      { title: "Ngày đặt", dataIndex: "created_at", render: day }, { title: "Tổng", dataIndex: "total_vnd", render: money },
      { title: "Trạng thái", dataIndex: "status", render: (value: string) => <Tag>{statusText[value] || value}</Tag> },
    ],
    preorders: [
      { title: "Mã đơn đặt trước", dataIndex: "order_code" }, { title: "Người nhận", dataIndex: "recipient_name" },
      { title: "Ngày đặt", dataIndex: "created_at", render: day }, { title: "Tổng", dataIndex: "total_vnd", render: money },
      { title: "Trạng thái", dataIndex: "status", render: (value: string) => <Tag>{statusText[value] || value}</Tag> },
    ],
    discounts: [
      { title: "Mã", dataIndex: "code" }, { title: "Giảm", render: (_, row) => row.kind === "percent" ? `${row.value}%` : money(row.value) },
      { title: "Đã dùng", dataIndex: "used_count" }, { title: "Hiệu lực", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "default"}>{value ? "Đang bật" : "Đã tắt"}</Tag> },
    ],
    customers: [
      { title: "Khách hàng", dataIndex: "name" }, { title: "Email", dataIndex: "email" }, { title: "Điện thoại", dataIndex: "phone" },
      { title: "Ngày tạo", dataIndex: "created_at", render: day },
    ],
    units: [
      { title: "Đơn vị", dataIndex: "code" },
      { title: "Số lẻ", dataIndex: "allows_fraction", render: (value: boolean) => value ? "Cho phép" : "Chỉ số nguyên" },
      { title: "Sản phẩm dùng", dataIndex: "product_count" },
      { title: "Trạng thái", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "default"}>{value ? "Đang bật" : "Đã tắt"}</Tag> },
    ],
    procurement: [],
    overview: [],
  };
  const columns: ColumnsType<Row> = [...sectionColumns[section], { title: "Thao tác", key: "actions", width: section === "batches" ? 200 : undefined, render: (_: unknown, row: Row) => actions(row) }];

  return <Layout className={`admin-shell${sidebarCollapsed ? " is-collapsed" : ""}`}>
    {noticeContext}
    <Modal title={`Xác nhận ${pendingAction?.label || "thao tác"}?`} open={!!pendingAction} zIndex={1300} okText="Xác nhận" cancelText="Bỏ qua" confirmLoading={saving} onOk={() => void runConfirmedAction()} onCancel={() => setPendingAction(null)}>
      Thao tác với {pendingAction?.row.name || pendingAction?.row.batch_code || pendingAction?.row.code || `#${pendingAction?.row.id || ""}`}.
    </Modal>
    <Modal
      title="Xác nhận đổi trạng thái đơn"
      open={statusConfirmOpen}
      zIndex={1200}
      okText="Cập nhật"
      cancelText="Bỏ qua"
      confirmLoading={statusSaving}
      onOk={() => void updateStatus()}
      onCancel={() => setStatusConfirmOpen(false)}
    >
      Đơn {detail?.order_code}: {statusText[detail?.status || ""]} → {statusText[pendingStatus || ""]}
    </Modal>
    <Modal title="Xác nhận đã nhận tiền" open={bankConfirmOpen} zIndex={1250} okText="Đã đối chiếu, xác nhận" cancelText="Quay lại" confirmLoading={bankConfirmSaving} onOk={() => void confirmBankPayment()} onCancel={() => setBankConfirmOpen(false)}>
      Chỉ xác nhận sau khi đã thấy khoản chuyển đúng <b>{money(detail?.total_vnd || 0)}</b> vào tài khoản nhận, với nội dung <b>{detail?.bank_transfer?.payment_code}</b>. Thao tác này đánh dấu đơn đã thanh toán.
    </Modal>
    {sidebarOpen && <button className="admin-sidebar-backdrop" type="button" aria-label="Đóng menu" onClick={() => setSidebarOpen(false)} />}
    <aside id="admin-sidebar" className={`admin-sidebar${sidebarOpen ? " is-open" : ""}`} aria-label="Điều hướng quản trị">
      <div className="admin-brand"><img className="admin-brand-mark" src="/icon.svg" alt="" width={37} height={37} /><span className="admin-brand-name"><strong>Vườn Nhà</strong><small>ADMIN CONSOLE</small></span><button className={`admin-menu-button admin-brand-toggle${sidebarCollapsed || sidebarOpen ? " is-active" : ""}`} type="button" aria-label={sidebarOpen ? "Đóng menu" : sidebarCollapsed ? "Mở rộng menu" : "Thu gọn menu"} aria-controls="admin-sidebar" aria-pressed={sidebarCollapsed || sidebarOpen} onClick={() => {
        // Đầu vào: nút menu trong khối logo; đầu ra: thu gọn sidebar hoặc đóng menu di động.
        // Ví dụ: màn hình 1440px thu gọn còn biểu tượng, màn hình 390px đóng menu nổi.
        if (window.innerWidth <= 900) setSidebarOpen(false);
        else setSidebarCollapsed((collapsed) => !collapsed);
      }}><span /><span /><span /></button></div>
      <div className="admin-sidebar-scroll">
        {navigationGroups.map((group) => <nav className="admin-nav-group" key={group.label} aria-label={group.label}>
          <div className="admin-nav-heading">{group.label}</div>
          {group.sections.map((item) => <button className={`admin-nav-item${section === item ? " is-active" : ""}`} key={item} type="button" aria-current={section === item ? "page" : undefined} onClick={() => changeSection(item)}><span className="admin-nav-icon" aria-hidden="true">{sectionMeta[item].icon}</span><span>{sectionMeta[item].label}</span><span className="admin-nav-chevron" aria-hidden="true">›</span></button>)}
        </nav>)}
      </div>
      <div className="admin-sidebar-foot"><span className="admin-sidebar-avatar">QT</span><span><strong>Quản trị viên</strong><small>Quản lý cửa hàng</small></span><span className="admin-sidebar-online" /></div>
    </aside>
    <div className="admin-workspace">
      <header className="admin-header"><div className="admin-header-start"><button className={`admin-menu-button admin-mobile-toggle${sidebarOpen ? " is-active" : ""}`} type="button" aria-label="Mở menu" aria-controls="admin-sidebar" aria-expanded={sidebarOpen} onClick={() => setSidebarOpen(true)}><span /><span /><span /></button><span className="admin-header-divider" /><span className="admin-header-path">Quản trị <span>/</span> <strong>{sectionMeta[section].label}</strong></span></div><div className="admin-header-actions"><a className="admin-store-link" href="/" target="_blank" rel="noreferrer">Xem cửa hàng ↗</a><span className="admin-header-avatar">QT</span><Button onClick={async () => { await fetch("/api/admin-session", { method: "DELETE" }); window.location.href = "/admin/dang-nhap"; }}>Đăng xuất</Button></div></header>
      <main className="admin-main">
        <div className="admin-page-heading"><div className="admin-page-icon" aria-hidden="true">{sectionMeta[section].icon}</div><div><span className="admin-page-eyebrow">QUẢN LÝ CỬA HÀNG</span><h1>{sectionMeta[section].label}</h1><p>{sectionMeta[section].subtitle}</p></div></div>
        {section === "overview" ? <AdminOverview onOpenOrders={() => changeSection("orders")} onOpenBatches={() => changeSection("batches")} /> : <>
        <div className="admin-overview-row"><div className="admin-overview-card"><span className="admin-overview-symbol">▦</span><div><small>KHU VỰC ĐANG XEM</small><strong>{sectionMeta[section].label}</strong></div></div><div className="admin-overview-card"><span className="admin-overview-symbol admin-overview-symbol-blue">≡</span><div><small>SỐ MỤC PHÙ HỢP</small><strong>{section === "procurement" ? "Xem theo danh mục" : loading ? "Đang tải" : total.toLocaleString("vi-VN")}</strong></div></div><div className="admin-overview-card admin-overview-note"><span className="admin-overview-symbol admin-overview-symbol-gold">↗</span><div><small>DỮ LIỆU TRỰC TIẾP</small><strong>Tìm kiếm và phân trang từ API</strong></div></div></div>
        <Card className="admin-content-card"><div className="admin-content-heading"><div><h2>{sectionMeta[section].label}</h2><p>{sectionMeta[section].subtitle}</p></div><span className="admin-content-count">{section === "procurement" ? "Quản lý" : `${total.toLocaleString("vi-VN")} mục`}</span></div>
      {section === "procurement" ? <ProcurementPanel /> : <>
      <div className="admin-toolbar"><Space wrap>
        <Input.Search placeholder={section === "orders" || section === "preorders" ? "Tên sản phẩm, khách, mã đơn" : "Tìm kiếm"} value={query} onChange={(event) => setQuery(event.target.value)} onSearch={(value) => { setPage(1); setSearch(value.trim()); }} allowClear style={{ width: 240 }} />
        {(section === "orders" || section === "preorders") && <Select placeholder="Trạng thái" value={filter || undefined} allowClear style={{ width: 175 }} onChange={(value) => { setFilter(value || ""); setPage(1); }} options={Object.entries(statusText).filter(([value]) => section === "preorders" || value !== "preordered").map(([value, label]) => ({ value, label }))} />}
        {(section === "orders" || section === "preorders") && <DatePicker placeholder="Ngày đặt hàng" format="DD/MM/YYYY" value={orderDate ? dayjs(orderDate) : null} onChange={value => { setOrderDate(value?.format("YYYY-MM-DD") || ""); setPage(1); }} allowClear style={{ width: 175 }} />}
        {(section === "products" || section === "batches" || section === "discounts" || section === "units") && <Select placeholder="Tất cả" value={filter || undefined} allowClear style={{ width: 155 }} onChange={(value) => { setFilter(value || ""); setPage(1); }} options={[{ value: "true", label: "Đang bật" }, { value: "false", label: "Đã tắt" }]} />}
      </Space>{["products", "batches", "discounts", "units"].includes(section) && <Button type="primary" onClick={() => openForm()}>Thêm mới</Button>}</div>
      {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} action={<Button size="small" onClick={() => void load()}>Thử lại</Button>} />}
      <Table<Row> rowKey="id" columns={columns} dataSource={rows} loading={loading} scroll={{ x: section === "batches" ? 1250 : 750 }} locale={{ emptyText: <Empty description="Chưa có dữ liệu phù hợp" /> }} pagination={{ current: page, pageSize: 10, total, showSizeChanger: false, onChange: setPage, showTotal: (value) => `${value} mục` }} />
      </>}
        </Card>
        </>}
      </main>
    </div>
    <Drawer title={editing ? "Chỉnh sửa" : "Thêm mới"} open={drawer} width={480} onClose={() => setDrawer(false)} destroyOnClose><Form form={form} layout="vertical" onFinish={saveForm}>
      <AdminFormFields section={section} editing={editing} />
      {section === "products" && <div className="mb-5 space-y-4">
        <div><Typography.Text strong>Ảnh chính</Typography.Text><div className="mt-2 flex items-center gap-3">{editing?.image_url && <img src={editing.image_url} alt="Ảnh chính hiện tại" className="h-20 w-20 rounded object-cover" />}<Upload accept="image/jpeg,image/png,image/webp" maxCount={1} showUploadList={false} beforeUpload={(file) => { setMainFile(file); return false; }}><Button>Chọn ảnh chính</Button></Upload></div>{mainFile && <Typography.Text type="secondary">Đã chọn: {mainFile.name}</Typography.Text>}</div>
        <div><Typography.Text strong>Ảnh chi tiết (tối đa 10)</Typography.Text><div className="mt-2 flex flex-wrap gap-2">{(editing?.images || []).filter((image: { id: number }) => !removedImageIds.includes(image.id)).map((image: { id: number; image_url: string }) => <div key={image.id}><img src={image.image_url} alt="Ảnh chi tiết" className="h-20 w-20 rounded object-cover" /><Button size="small" danger onClick={() => setRemovedImageIds((ids) => [...ids, image.id])}>Bỏ</Button></div>)}</div><Upload accept="image/jpeg,image/png,image/webp" multiple showUploadList={false} beforeUpload={(file) => { setDetailFiles((files) => [...files, file]); return false; }}><Button className="mt-2">Thêm ảnh chi tiết</Button></Upload>{detailFiles.map((file, index) => <div key={`${file.name}-${index}`} className="flex items-center gap-2 text-sm"><span>{file.name}</span><Button size="small" onClick={() => setDetailFiles((files) => files.filter((_, position) => position !== index))}>Bỏ</Button></div>)}</div>
        <Typography.Text type="secondary">JPEG, PNG hoặc WebP; tối đa 5 MB mỗi ảnh.</Typography.Text>
      </div>}
      <Button type="primary" htmlType="submit" loading={saving}>Lưu</Button>
    </Form></Drawer>
    <Drawer title={`Đơn dùng mã ${discountHistory?.code || ""}`} open={!!discountHistory} width="min(100vw, 720px)" onClose={() => { setDiscountHistory(null); setDetail(null); }}>
      {discountError && <Alert type="error" message={discountError} showIcon style={{ marginBottom: 16 }} action={<Button size="small" onClick={() => discountHistory && void showDiscountOrders(discountHistory, discountPage)}>Thử lại</Button>} />}
      <Table<Row> rowKey="id" size="small" dataSource={discountOrders} loading={discountLoading} scroll={{ x: 570 }} locale={{ emptyText: <Empty description="Chưa có đơn dùng mã này" /> }} columns={[{ title: "Mã đơn", dataIndex: "order_code" }, { title: "Người nhận", dataIndex: "recipient_name" }, { title: "Ngày đặt", dataIndex: "created_at", render: day }, { title: "Giảm", dataIndex: "discount_vnd", render: money }, { title: "Tổng", dataIndex: "total_vnd", render: money }, { title: "Chi tiết", render: (_: unknown, row: Row) => <Button type="link" onClick={() => void showOrder(row.id)}>Xem đơn</Button> }]} pagination={{ current: discountPage, pageSize: 10, total: discountTotal, showSizeChanger: false, onChange: (targetPage) => { if (discountHistory) void showDiscountOrders(discountHistory, targetPage); } }} />
    </Drawer>
    <Drawer title={section === "orders" || section === "preorders" || section === "discounts" ? `${detail?.is_preorder ? "Đơn đặt trước" : "Đơn hàng"} ${detail?.order_code || ""}` : `Lịch sử mua: ${detail?.name || ""}`} open={!!detail} width={560} zIndex={1100} onClose={() => { setDetail(null); setCustomerOrder(null); setPendingStatus(null); setStatusConfirmOpen(false); }}>
      {(section === "orders" || section === "preorders" || section === "discounts") && detail && <><p><b>Khách:</b> #{detail.customer_id}</p><p><b>Người nhận:</b> {detail.recipient_name} · {detail.recipient_phone}</p><p><b>Địa chỉ:</b> {detail.delivery_address}</p>
        <div className="mb-4 rounded-lg bg-green-50 p-4">
          <p><b>Tạm tính:</b> {money(detail.subtotal_vnd)}</p>
          <p><b>Mã khuyến mãi:</b> {detail.discount_code || "Không áp dụng"}</p>
          <p><b>Giảm giá:</b> {money(detail.discount_vnd)}</p>
          <p className="mb-0"><b>Thành tiền:</b> {money(detail.total_vnd)}</p>
        </div>
        <p><b>Trạng thái:</b> {statusText[detail.status]}</p>{detail.payment_method === "sepay_bank" && <div className="mb-5 rounded-lg border border-blue-200 bg-blue-50 p-4"><p><b>Thanh toán QR:</b> {detail.payment_status === "paid" ? "Đã xác nhận nhận tiền" : "Chờ xác nhận tiền vào"}</p><p><b>Khách báo chuyển khoản:</b> {detail.bank_transfer_reported_at ? day(detail.bank_transfer_reported_at) : "Chưa báo"}</p><p><b>Số tiền cần đối chiếu:</b> {money(detail.total_vnd)}</p><p><b>Nội dung chuyển khoản:</b> {detail.bank_transfer?.payment_code}</p>{detail.bank_payment_confirmed_at && <p><b>Admin đối soát:</b> {day(detail.bank_payment_confirmed_at)}</p>}{detail.payment_status === "pending" && detail.status !== "cancelled" && <Button type="primary" onClick={() => setBankConfirmOpen(true)}>Xác nhận đã nhận tiền</Button>}</div>}{detail.is_preorder && <div className="mb-5 rounded-lg border border-amber-200 bg-amber-50 p-4"><b>Giá đặt trước</b>{detail.items?.map((item: Row) => <p key={item.product_id} className="mt-2 mb-0">{item.product_name}: {money(item.initial_unit_price_vnd ?? item.unit_price_vnd)} → {item.proposed_unit_price_vnd === null ? "Chưa gửi giá" : money(item.proposed_unit_price_vnd)} / {item.unit}</p>)}<p className="mt-3 mb-0 font-semibold">Tổng: {money(detail.initial_total_vnd ?? detail.total_vnd)} → {detail.proposed_total_vnd === null ? "Chưa gửi giá" : money(detail.proposed_total_vnd)}</p>{(detail.status === "preordered" || detail.status === "awaiting_price_approval") && <Button className="mt-4" type="primary" loading={proposalSaving} onClick={() => void proposePrice()}>{detail.status === "awaiting_price_approval" ? "Cập nhật và gửi lại giá" : "Gửi giá khi hàng về"}</Button>}</div>}{nextStatus[detail.status]?.length > 0 && <div className="mb-5 flex flex-wrap items-center gap-2"><Select placeholder="Chọn trạng thái mới" style={{ width: 220 }} value={pendingStatus} onChange={setPendingStatus} options={nextStatus[detail.status].map((value) => ({ value, label: statusText[value] }))} /><Button type="primary" disabled={!pendingStatus} onClick={() => setStatusConfirmOpen(true)}>Cập nhật trạng thái</Button></div>}<Typography.Title level={5}>Sản phẩm</Typography.Title>{detail.items?.map((item: Row) => <p key={item.product_id}>{item.product_name} · {item.quantity} {item.unit} · {money(item.line_total_vnd)}{item.is_preorder && <Tag className="ml-2" color="gold">Đặt trước</Tag>}</p>)}<Typography.Title level={5}>Lịch sử trạng thái</Typography.Title>{detail.history?.length ? detail.history.map((event: Row) => <Card size="small" key={`${event.created_at}-${event.to_status}`} style={{ marginBottom: 8 }}><b>{statusText[event.from_status] || "Tạo đơn"} → {statusText[event.to_status]}</b><br />{day(event.created_at)}{event.reason && <p>{event.reason}</p>}</Card>) : <Empty description="Chưa có lịch sử chuyển trạng thái" />}</>}
      {section === "customers" && detail && <Table<Row> rowKey="id" size="small" dataSource={historyRows} loading={customerOrderLoading} onRow={(row) => ({ onClick: () => void showCustomerOrder(row.id), style: { cursor: "pointer" } })} columns={[{ title: "Mã đơn", dataIndex: "order_code" }, { title: "Ngày", dataIndex: "created_at", render: day }, { title: "Tổng", dataIndex: "total_vnd", render: money }, { title: "Trạng thái", dataIndex: "status", render: (value: string) => statusText[value] }, { title: "Chi tiết", key: "detail", render: (_: unknown, row: Row) => <Button type="link" onClick={(event) => { event.stopPropagation(); void showCustomerOrder(row.id); }}>Xem đơn</Button> }]} pagination={{ current: historyPage, pageSize: 10, total: historyTotal, showSizeChanger: false, onChange: (value) => void showCustomer(detail.id, value) }} scroll={{ x: 500 }} />}
    </Drawer>
    <Drawer title={`Đơn hàng ${customerOrder?.order_code || ""}`} open={!!customerOrder} width={560} onClose={() => setCustomerOrder(null)} zIndex={1100}>
      {customerOrder && <>
        <p><b>Ngày đặt:</b> {day(customerOrder.created_at)}</p>
        <p><b>Trạng thái:</b> {statusText[customerOrder.status] || customerOrder.status}</p>
        <p><b>Người nhận:</b> {customerOrder.recipient_name} · {customerOrder.recipient_phone}</p>
        <p><b>Địa chỉ:</b> {customerOrder.delivery_address}</p>
        <Typography.Title level={5}>Sản phẩm</Typography.Title>
        {customerOrder.items?.map((item: Row) => <p key={item.product_id}>{item.product_name} · {item.quantity} {item.unit} · {money(item.line_total_vnd)}</p>)}
        <div className="mb-4 rounded-lg bg-green-50 p-4">
          <p><b>Tạm tính:</b> {money(customerOrder.subtotal_vnd)}</p>
          <p><b>Mã khuyến mãi:</b> {customerOrder.discount_code || "Không áp dụng"}</p>
          <p><b>Giảm giá:</b> {money(customerOrder.discount_vnd)}</p>
          <p className="mb-0"><b>Thành tiền:</b> {money(customerOrder.total_vnd)}</p>
        </div>
        <Typography.Title level={5}>Lịch sử trạng thái</Typography.Title>
        {customerOrder.history?.length ? customerOrder.history.map((event: Row) => <Card size="small" key={`${event.created_at}-${event.to_status}`} style={{ marginBottom: 8 }}><b>{statusText[event.from_status] || "Tạo đơn"} → {statusText[event.to_status]}</b><br />{day(event.created_at)}{event.reason && <p>{event.reason}</p>}</Card>) : <Empty description="Chưa có lịch sử chuyển trạng thái" />}
      </>}
    </Drawer>
  </Layout>;
}
