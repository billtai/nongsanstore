"use client";

import { Alert, Button, Card, Drawer, Empty, Form, Input, InputNumber, Modal, Select, Space, Table, Tabs, Tag, message } from "antd";
import type { ColumnsType } from "antd/es/table";
import { useCallback, useEffect, useState } from "react";
import { adminApi as api } from "./api";
import { day, money } from "./constants";
import type { PageData, Row } from "./types";

type Kind = "suppliers" | "purchases";
const statusLabels: Record<string, string> = { draft: "Bản nháp", ordered: "Đã ghi nhận đặt", received: "Đã nhận hàng", cancelled: "Đã hủy" };

/** Chọn bản ghi từ API có tìm kiếm/phân trang; đầu vào loại, ID, nhãn; đầu ra ID. Ví dụ gõ "rau" tải 20 sản phẩm. */
function RemoteSelect({ kind, value, onChange, currentLabel }: { kind: "suppliers" | "products"; value?: number; onChange?: (id: number) => void; currentLabel?: string }) {
  const [query, setQuery]     = useState("");
  const [search, setSearch]   = useState("");
  const [page, setPage]       = useState(1);
  const [options, setOptions] = useState<{ value: number; label: string }[]>([]);
  const [more, setMore]       = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError]     = useState("");
  useEffect(() => { const timer = setTimeout(() => { setPage(1); setSearch(query.trim()); }, 300); return () => clearTimeout(timer); }, [query]);
  useEffect(() => {
    let active = true;
    setLoading(true);
    setError("");
    const params = new URLSearchParams({ page: String(page), limit: "20", [kind === "suppliers" ? "active" : "visible"]: "true" });
    if (search) params.set("q", search);
    void api(`/admin/${kind}?${params}`).then((data: PageData) => {
      if (!active) return;
      const fetched = data.items.map((row) => ({ value: row.id, label: kind === "products" ? `${row.name} · ${row.unit}` : row.name }));
      const initial = value && currentLabel ? [{ value, label: currentLabel }] : [];
      setOptions((previous) => [...new Map((page === 1 ? [...initial, ...fetched] : [...previous, ...fetched]).map((item) => [item.value, item])).values()]);
      setMore(page * 20 < data.total);
    }).catch((reason) => { if (active) setError(reason instanceof Error ? reason.message : "Không thể tải lựa chọn."); }).finally(() => { if (active) setLoading(false); });
    return () => { active = false; };
  }, [kind, page, search, value, currentLabel]);
  return <><Select<number> value={value} onChange={onChange} options={options} showSearch filterOption={false} searchValue={query} onSearch={setQuery} loading={loading} placeholder="Tìm và chọn" style={{ width: "100%" }} onPopupScroll={(event) => { const target = event.currentTarget; if (more && !loading && target.scrollTop + target.clientHeight >= target.scrollHeight - 24) setPage((current) => current + 1); }} />{error && <Alert type="error" message={error} showIcon className="mt-2" />}</>;
}

/** Quản lý nhà cung cấp và đơn nhập; đầu vào thao tác admin, đầu ra bảng, biểu mẫu và lô kho. Ví dụ nhận đơn #2 tạo lô. */
export function ProcurementPanel() {
  const [kind, setKind]           = useState<Kind>("suppliers");
  const [rows, setRows]           = useState<Row[]>([]);
  const [page, setPage]           = useState(1);
  const [total, setTotal]         = useState(0);
  const [query, setQuery]         = useState("");
  const [search, setSearch]       = useState("");
  const [filter, setFilter]       = useState("");
  const [loading, setLoading]     = useState(false);
  const [error, setError]         = useState("");
  const [editing, setEditing]     = useState<Row | null>(null);
  const [formOpen, setFormOpen]   = useState(false);
  const [detail, setDetail]       = useState<Row | null>(null);
  const [historySupplier, setHistorySupplier] = useState<Row | null>(null);
  const [historyRows, setHistoryRows]         = useState<Row[]>([]);
  const [historyPage, setHistoryPage]         = useState(1);
  const [historyTotal, setHistoryTotal]       = useState(0);
  const [historyLoading, setHistoryLoading]   = useState(false);
  const [historyError, setHistoryError]       = useState("");
  const [prefillSupplier, setPrefillSupplier] = useState<Row | null>(null);
  const [receiving, setReceiving] = useState(false);
  const [saving, setSaving]       = useState(false);
  const [pendingAction, setPendingAction] = useState<{ label: string; path: string; method: string; body?: object; detailId?: number } | null>(null);
  const [form]                    = Form.useForm();
  const [receiveForm]             = Form.useForm();
  const [notice, context]         = message.useMessage();
  const load = useCallback(async () => {
    setLoading(true); setError("");
    const params = new URLSearchParams({ page: String(page), limit: "10" });
    if (search) params.set("q", search);
    if (filter) params.set(kind === "suppliers" ? "active" : "status", filter);
    try { const data: PageData = await api(`/admin/${kind}?${params}`); setRows(data.items); setTotal(data.total); }
    catch (reason) { setRows([]); setTotal(0); setError(reason instanceof Error ? reason.message : "Không thể tải dữ liệu."); }
    finally { setLoading(false); }
  }, [kind, page, search, filter]);
  useEffect(() => { void load(); }, [load]);

  /** Mở form với chi tiết mới nhất; đầu vào hàng tùy chọn, đầu ra form thêm/sửa. Ví dụ mở đơn nháp #3. */
  async function openForm(row?: Row) {
    form.resetFields(); setEditing(row || null); setPrefillSupplier(null);
    if (row && kind === "purchases") {
      try { const data = await api(`/admin/purchases/${row.id}`); form.setFieldsValue(data); setEditing(data); }
      catch (reason) { notice.error(reason instanceof Error ? reason.message : "Không thể tải đơn."); return; }
    } else if (row) form.setFieldsValue(row);
    else if (kind === "purchases") form.setFieldsValue({ items: [{}] });
    setFormOpen(true);
  }

  /** Tạo đơn từ hàng nhà cung cấp; đầu vào Supplier, đầu ra form đơn nháp chọn sẵn nhà cung cấp. Ví dụ trang trại #2. */
  function createForSupplier(supplier: Row) {
    form.resetFields();
    setEditing(null);
    setPrefillSupplier(supplier);
    setKind("purchases");
    setPage(1);
    setQuery("");
    setSearch("");
    setFilter("");
    form.setFieldsValue({ supplier_id: supplier.id, items: [{}] });
    setFormOpen(true);
  }

  /** Tải một trang lịch sử đơn từ API; đầu vào nhà cung cấp/trang, đầu ra bảng đơn. Ví dụ nhà cung cấp #2, trang 3. */
  async function showSupplierHistory(supplier: Row, targetPage = 1) {
    setHistorySupplier(supplier);
    setHistoryPage(targetPage);
    setHistoryLoading(true);
    setHistoryError("");
    try {
      const params = new URLSearchParams({ supplier_id: String(supplier.id), page: String(targetPage), limit: "10" });
      const data: PageData = await api(`/admin/purchases?${params}`);
      setHistoryRows(data.items);
      setHistoryTotal(data.total);
    } catch (reason) {
      setHistoryRows([]);
      setHistoryTotal(0);
      setHistoryError(reason instanceof Error ? reason.message : "Không thể tải lịch sử đơn.");
    } finally { setHistoryLoading(false); }
  }

  /** Lưu bản ghi; đầu vào giá trị form, đầu ra thông báo và bảng mới. Ví dụ thêm đơn nháp. */
  async function save(values: Row) {
    setSaving(true);
    try {
      const body = kind === "purchases" ? { supplier_id: values.supplier_id, expected_date: values.expected_date || null, notes: values.notes || "", items: values.items.map((item: Row) => ({ product_id: item.product_id, quantity: item.quantity, unit_cost_vnd: item.unit_cost_vnd })) } : { name: values.name, contact_name: values.contact_name || "", phone: values.phone || "", email: values.email || "", address: values.address || "", tax_code: values.tax_code || "", notes: values.notes || "" };
      await api(`/admin/${kind}${editing ? `/${editing.id}` : ""}`, { method: editing ? "PATCH" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
      notice.success(editing ? "Đã cập nhật." : "Đã thêm mới."); setFormOpen(false); void load();
    } catch (reason) { notice.error(reason instanceof Error ? reason.message : "Không thể lưu."); }
    finally { setSaving(false); }
  }

  /** Tải chi tiết đơn; đầu vào ID, đầu ra ngăn chi tiết. Ví dụ xem đơn #4. */
  async function showDetail(id: number) {
    try { setDetail(await api(`/admin/purchases/${id}`)); }
    catch (reason) { notice.error(reason instanceof Error ? reason.message : "Không thể tải đơn nhập."); }
  }

  /** Xác nhận thao tác nhạy cảm; đầu vào nhãn/path/method/body, đầu ra bảng và chi tiết mới. Ví dụ ẩn nhà cung cấp. */
  function confirm(label: string, path: string, method: string, body?: object, detailId?: number) {
    setPendingAction({ label, path, method, body, detailId });
  }

  /** Thực hiện hành động đã xác nhận; đầu vào pendingAction, đầu ra bảng và chi tiết mới. Ví dụ chuyển đơn sang ordered. */
  async function runConfirmedAction() {
    if (!pendingAction) return;
    setSaving(true);
    try {
      await api(pendingAction.path, { method: pendingAction.method, headers: { "Content-Type": "application/json" }, body: pendingAction.body ? JSON.stringify(pendingAction.body) : undefined });
      notice.success(`Đã ${pendingAction.label}.`);
      void load();
      if (pendingAction.detailId) void showDetail(pendingAction.detailId);
      if (historySupplier) void showSupplierHistory(historySupplier, historyPage);
      setPendingAction(null);
    } catch (reason) { notice.error(reason instanceof Error ? reason.message : "Thao tác thất bại."); }
    finally { setSaving(false); }
  }

  /** Nhận hàng; đầu vào thông tin lô từng dòng, đầu ra tồn kho và mã lô mới. Ví dụ 2 kg cà rốt tạo lô 2 kg. */
  async function receive(values: { batches: Row[] }) {
    if (!detail) return;
    setSaving(true);
    try {
      const batches = values.batches.map((row) => ({ item_id: row.item_id, growing_region: row.growing_region, origin: row.origin, harvest_date: row.harvest_date }));
      setDetail(await api(`/admin/purchases/${detail.id}/status`, { method: "PATCH", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ status: "received", batches }) }));
      setReceiving(false); notice.success("Đã nhận hàng và tạo lô trong kho."); void load();
      if (historySupplier) void showSupplierHistory(historySupplier, historyPage);
    } catch (reason) { notice.error(reason instanceof Error ? reason.message : "Không thể nhận hàng."); }
    finally { setSaving(false); }
  }

  const columns: ColumnsType<Row> = kind === "suppliers" ? [
    { title: "Nhà cung cấp", dataIndex: "name" }, { title: "Liên hệ", render: (_, row) => <>{row.contact_name}<br />{row.phone}</> },
    { title: "Email", dataIndex: "email" }, { title: "Số đơn", dataIndex: "order_count" },
    { title: "Trạng thái", dataIndex: "is_active", render: (value: boolean) => <Tag color={value ? "green" : "default"}>{value ? "Đang dùng" : "Đã ẩn"}</Tag> },
    { title: "Thao tác", render: (_, row) => <Space wrap><Button size="small" type="primary" disabled={!row.is_active} onClick={() => createForSupplier(row)}>Tạo đơn</Button><Button size="small" onClick={() => void showSupplierHistory(row)}>Lịch sử đơn</Button><Button size="small" onClick={() => void openForm(row)}>Sửa</Button><Button size="small" danger={row.is_active} onClick={() => confirm(row.is_active ? "ẩn nhà cung cấp" : "hiện nhà cung cấp", `/admin/suppliers/${row.id}`, "PATCH", { is_active: !row.is_active })}>{row.is_active ? "Ẩn" : "Hiện"}</Button>{!row.order_count && <Button size="small" danger onClick={() => confirm("xóa nhà cung cấp", `/admin/suppliers/${row.id}`, "DELETE")}>Xóa</Button>}</Space> },
  ] : [
    { title: "Đơn nhập", dataIndex: "id", render: (value: number) => `#${value}` }, { title: "Nhà cung cấp", dataIndex: "supplier_name" },
    { title: "Ngày tạo", dataIndex: "created_at", render: day }, { title: "Dự kiến nhận", dataIndex: "expected_date", render: day },
    { title: "Tổng tiền", dataIndex: "total_vnd", render: money }, { title: "Trạng thái", dataIndex: "status", render: (value: string) => <Tag>{statusLabels[value]}</Tag> },
    { title: "Thao tác", render: (_, row) => <Space wrap><Button size="small" onClick={() => void showDetail(row.id)}>Chi tiết</Button>{row.status === "draft" && <Button size="small" onClick={() => void openForm(row)}>Sửa</Button>}</Space> },
  ];
  return <>
    {context}
    <Modal title={`Xác nhận ${pendingAction?.label || "thao tác"}?`} open={!!pendingAction} zIndex={1300} okText="Xác nhận" cancelText="Bỏ qua" confirmLoading={saving} onOk={() => void runConfirmedAction()} onCancel={() => setPendingAction(null)}>
      {pendingAction?.detailId ? `Đơn nhập #${pendingAction.detailId}` : "Vui lòng kiểm tra trước khi tiếp tục."}
    </Modal>
    <Tabs activeKey={kind} onChange={(key) => { setKind(key as Kind); setPage(1); setQuery(""); setSearch(""); setFilter(""); setDetail(null); }} items={[{ key: "suppliers", label: "Thông tin nhà cung cấp" }, { key: "purchases", label: "Đơn nhập hàng" }]} />
    <div className="admin-toolbar"><Space wrap><Input.Search placeholder={kind === "suppliers" ? "Tìm tên, điện thoại, email" : "Tìm nhà cung cấp"} value={query} onChange={(event) => setQuery(event.target.value)} onSearch={(value) => { setPage(1); setSearch(value.trim()); }} allowClear style={{ width: 260 }} /><Select placeholder="Tất cả trạng thái" allowClear value={filter || undefined} onChange={(value) => { setFilter(value || ""); setPage(1); }} style={{ width: 190 }} options={kind === "suppliers" ? [{ value: "true", label: "Đang dùng" }, { value: "false", label: "Đã ẩn" }] : Object.entries(statusLabels).map(([value, label]) => ({ value, label }))} /></Space><Button type="primary" onClick={() => void openForm()}>{kind === "suppliers" ? "Thêm nhà cung cấp" : "Tạo đơn nhập"}</Button></div>
    {error && <Alert type="error" message={error} showIcon style={{ marginBottom: 16 }} action={<Button size="small" onClick={() => void load()}>Thử lại</Button>} />}
    <Table<Row> rowKey="id" columns={columns} dataSource={rows} loading={loading} scroll={{ x: 750 }} locale={{ emptyText: <Empty description="Chưa có dữ liệu phù hợp" /> }} pagination={{ current: page, pageSize: 10, total, showSizeChanger: false, onChange: setPage, showTotal: (value) => `${value} mục` }} />
    <Drawer title={kind === "suppliers" ? editing ? "Sửa nhà cung cấp" : "Thêm nhà cung cấp" : editing ? "Sửa đơn nháp" : "Tạo đơn nhập"} open={formOpen} width="min(100vw, 640px)" onClose={() => setFormOpen(false)} destroyOnClose><Form form={form} layout="vertical" onFinish={save}>
      {kind === "suppliers" ? <><Form.Item name="name" label="Tên nhà cung cấp" rules={[{ required: true }]}><Input maxLength={180} /></Form.Item><Form.Item name="contact_name" label="Người liên hệ"><Input maxLength={120} /></Form.Item><Form.Item name="phone" label="Điện thoại"><Input maxLength={30} /></Form.Item><Form.Item name="email" label="Email" rules={[{ type: "email" }]}><Input maxLength={180} /></Form.Item><Form.Item name="address" label="Địa chỉ"><Input maxLength={255} /></Form.Item><Form.Item name="tax_code" label="Mã số thuế"><Input maxLength={30} /></Form.Item><Form.Item name="notes" label="Ghi chú"><Input.TextArea rows={3} maxLength={2000} /></Form.Item></> : <>
        <Form.Item name="supplier_id" label="Nhà cung cấp" rules={[{ required: true }]}><RemoteSelect kind="suppliers" currentLabel={editing?.supplier_name || prefillSupplier?.name} /></Form.Item><Form.Item name="expected_date" label="Ngày dự kiến nhận"><Input type="date" /></Form.Item><Form.Item name="notes" label="Ghi chú"><Input.TextArea rows={2} maxLength={2000} /></Form.Item>
        <Form.List name="items" rules={[{ validator: async (_, items) => { if (!items?.length) throw new Error("Cần ít nhất một sản phẩm."); } }]}>{(fields, { add, remove }, { errors }) => <>{fields.map((field, index) => <Card size="small" key={field.key} title={`Sản phẩm ${index + 1}`} extra={<Button size="small" danger onClick={() => remove(field.name)}>Bỏ</Button>} style={{ marginBottom: 12 }}><Form.Item name={[field.name, "product_id"]} label="Sản phẩm" rules={[{ required: true }]}><RemoteSelect kind="products" currentLabel={editing?.items?.[index]?.product_name} /></Form.Item><Space wrap><Form.Item name={[field.name, "quantity"]} label="Số lượng" rules={[{ required: true }]}><InputNumber min={0.001} precision={3} style={{ width: 145 }} /></Form.Item><Form.Item name={[field.name, "unit_cost_vnd"]} label="Giá nhập / đơn vị (₫)" rules={[{ required: true }]}><InputNumber min={0} precision={0} style={{ width: 180 }} /></Form.Item></Space></Card>)}<Form.ErrorList errors={errors} /><Button onClick={() => add({})} style={{ marginBottom: 20 }}>Thêm sản phẩm</Button></>}</Form.List>
      </>}<Button type="primary" htmlType="submit" loading={saving}>Lưu</Button>
    </Form></Drawer>
    <Drawer title={`Lịch sử đơn: ${historySupplier?.name || ""}`} open={!!historySupplier} width="min(100vw, 720px)" onClose={() => setHistorySupplier(null)}>
      {historyError && <Alert type="error" message={historyError} showIcon style={{ marginBottom: 16 }} action={<Button size="small" onClick={() => historySupplier && void showSupplierHistory(historySupplier, historyPage)}>Thử lại</Button>} />}
      <Table<Row> rowKey="id" size="small" dataSource={historyRows} loading={historyLoading} scroll={{ x: 540 }} locale={{ emptyText: <Empty description="Nhà cung cấp chưa có đơn nhập" /> }} columns={[{ title: "Đơn", dataIndex: "id", render: (value: number) => `#${value}` }, { title: "Ngày tạo", dataIndex: "created_at", render: day }, { title: "Tổng tiền", dataIndex: "total_vnd", render: money }, { title: "Trạng thái", dataIndex: "status", render: (value: string) => statusLabels[value] }, { title: "Chi tiết", render: (_, row) => <Button type="link" onClick={() => void showDetail(row.id)}>Xem đơn</Button> }]} pagination={{ current: historyPage, pageSize: 10, total: historyTotal, showSizeChanger: false, onChange: (targetPage) => { if (historySupplier) void showSupplierHistory(historySupplier, targetPage); } }} />
    </Drawer>
    <Drawer title={`Đơn nhập #${detail?.id || ""}`} open={!!detail} width="min(100vw, 620px)" zIndex={1200} onClose={() => setDetail(null)}>{detail && <><p><b>Nhà cung cấp:</b> {detail.supplier_name}</p><p><b>Trạng thái:</b> {statusLabels[detail.status]}</p><p><b>Ngày tạo:</b> {day(detail.created_at)}</p><p><b>Ngày dự kiến nhận:</b> {day(detail.expected_date)}</p>{detail.notes && <p><b>Ghi chú:</b> {detail.notes}</p>}{detail.items?.map((item: Row) => <Card size="small" key={item.id} style={{ marginBottom: 8 }}><b>{item.product_name}</b><br />{item.quantity} {item.unit} × {money(item.unit_cost_vnd)} = {money(item.line_total_vnd)}{item.batch_code && <><br />Lô: {item.batch_code}</>}</Card>)}<p><b>Tổng tiền:</b> {money(detail.total_vnd)}</p><Space wrap>{detail.status === "draft" && <Button type="primary" onClick={() => confirm("ghi nhận đã đặt", `/admin/purchases/${detail.id}/status`, "PATCH", { status: "ordered" }, detail.id)}>Ghi nhận đã đặt</Button>}{detail.status === "ordered" && <Button type="primary" onClick={() => { receiveForm.setFieldsValue({ batches: detail.items.map((item: Row) => ({ item_id: item.id })) }); setReceiving(true); }}>Nhận hàng vào kho</Button>}{["draft", "ordered"].includes(detail.status) && <Button danger onClick={() => confirm("hủy đơn nhập", `/admin/purchases/${detail.id}/status`, "PATCH", { status: "cancelled" }, detail.id)}>Hủy đơn</Button>}</Space></>}</Drawer>
    <Drawer title={`Nhận hàng đơn #${detail?.id || ""}`} open={receiving} width="min(100vw, 620px)" zIndex={1250} onClose={() => setReceiving(false)} destroyOnClose><Alert type="info" showIcon message="Mỗi sản phẩm sẽ tạo một lô mới và tăng tồn kho đúng số lượng trong đơn." style={{ marginBottom: 16 }} /><Form form={receiveForm} layout="vertical" onFinish={receive}>{detail?.items?.map((item: Row, index: number) => <Card size="small" key={item.id} title={`${item.product_name} · ${item.quantity} ${item.unit}`} style={{ marginBottom: 12 }}><Form.Item name={["batches", index, "item_id"]} hidden><Input /></Form.Item><Form.Item name={["batches", index, "growing_region"]} label="Vùng trồng" rules={[{ required: true }]}><Input maxLength={180} /></Form.Item><Form.Item name={["batches", index, "origin"]} label="Nguồn gốc" rules={[{ required: true }]}><Input maxLength={255} /></Form.Item><Form.Item name={["batches", index, "harvest_date"]} label="Ngày thu hoạch" rules={[{ required: true }]}><Input type="date" /></Form.Item></Card>)}<Button type="primary" htmlType="submit" loading={saving}>Xác nhận nhận hàng</Button></Form></Drawer>
  </>;
}
