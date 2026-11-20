"use client";

import { Alert, Button, Card, DatePicker, Empty, Skeleton, Table } from "antd";
import dayjs from "dayjs";
import { useCallback, useEffect, useState } from "react";
import { adminApi } from "./api";
import { money } from "./constants";

type Counts = Record<"today" | "previous_day" | "month" | "previous_month" | "year" | "previous_year", number>;
type AgingBatch = { id: number; batch_code: string; product_name: string; unit: string; remaining_quantity: string; created_at: string };
type OverviewData = { timezone: string; as_of: string; counts: Counts; monthly: { month: string; orders: number }[]; aging_batches: { items: AgingBatch[]; total: number; page: number; limit: number; threshold_hours: number } };
type RevenueDay = { day: string; order_count: number; total_vnd: number };
type RevenuePage = { items: RevenueDay[]; page: number; limit: number; total: number; timezone: string };

/**
 * Hiển thị thống kê đơn quản trị từ API tổng hợp.
 * Đầu vào: callback mở đơn/lô; đầu ra: thẻ thống kê, biểu đồ, báo cáo doanh thu và lô tồn lâu.
 * Ví dụ: hai đơn completed tạo cùng ngày Việt Nam hiện một dòng báo cáo.
 */
export function AdminOverview({ onOpenOrders, onOpenBatches }: { onOpenOrders: () => void; onOpenBatches: () => void }) {
  const [data, setData]       = useState<OverviewData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState("");
  const [agingPage, setAgingPage] = useState(1);
  const [revenue, setRevenue] = useState<RevenuePage | null>(null);
  const [revenueLoading, setRevenueLoading] = useState(true);
  const [revenueError, setRevenueError] = useState("");
  const [revenuePage, setRevenuePage] = useState(1);
  const [revenueRange, setRevenueRange] = useState<[string, string] | null>(null);

  const load = useCallback(async (page = 1) => {
    setLoading(true);
    setError("");
    try {
      setData(await adminApi(`/admin/overview?aging_page=${page}`));
      setAgingPage(page);
    } catch (reason) {
      const message = reason instanceof Error ? reason.message : "Không tải được thống kê.";
      // Đầu vào: lỗi 404 từ API; đầu ra: chỉ dẫn đúng cho route thống kê mới.
      // Ví dụ: backend cũ chưa khởi động lại sẽ được báo cần nạp API mới.
      setError(message.includes("not found") || message.includes("404") ? "API thống kê chưa có trên backend đang chạy. Hãy khởi động lại backend với mã mới và kiểm tra API_URL của frontend trỏ đúng cổng." : message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { void load(); }, [load]);

  const loadRevenue = useCallback(async (page = 1) => {
    // Đầu vào: số trang và khoảng ngày đã chọn; đầu ra: tối đa 10 dòng từ API.
    // Ví dụ: page=2, from_date=2026-11-01 chỉ lấy ngày thuộc khoảng lọc ở trang 2.
    setRevenueLoading(true);
    setRevenueError("");
    try {
      const params = new URLSearchParams({ page: String(page), limit: "10" });
      if (revenueRange) {
        params.set("from_date", revenueRange[0]);
        params.set("to_date", revenueRange[1]);
      }
      setRevenue(await adminApi(`/admin/overview/daily-revenue?${params}`));
      setRevenuePage(page);
    } catch (reason) {
      setRevenueError(reason instanceof Error ? reason.message : "Không tải được báo cáo doanh thu.");
    } finally {
      setRevenueLoading(false);
    }
  }, [revenueRange]);

  useEffect(() => { void loadRevenue(); }, [loadRevenue]);

  if (loading && !data) return <div className="admin-stat-loading"><Skeleton active paragraph={{ rows: 8 }} /></div>;
  if (error && !data) return <Alert type="error" showIcon message={error} action={<Button onClick={() => void load(agingPage)}>Thử lại</Button>} />;
  if (!data) return <Empty description="Chưa có thống kê" />;

  const metrics = [
    { label: "Đơn hôm nay", current: data.counts.today, previous: data.counts.previous_day, comparison: "so với hôm qua", icon: "◷", tone: "green" },
    { label: "Đơn tháng này", current: data.counts.month, previous: data.counts.previous_month, comparison: "so với tháng trước", icon: "▦", tone: "blue" },
    { label: "Đơn năm nay", current: data.counts.year, previous: data.counts.previous_year, comparison: "so với năm trước", icon: "◫", tone: "gold" },
  ];
  const maxOrders = Math.max(1, ...data.monthly.map((item) => item.orders));
  const chartHeight = 220;
  const chartWidth  = 840;
  const points = data.monthly.map((item, index) => ({
    x      : 32 + index * (chartWidth - 64) / 11,
    y      : chartHeight - 28 - item.orders / maxOrders * (chartHeight - 58),
    orders : item.orders,
    month  : item.month,
  }));
  const line = points.map((point, index) => `${index ? "L" : "M"}${point.x},${point.y}`).join(" ");

  return <div className="admin-stat-page">
    {error && <Alert type="warning" showIcon message={error} action={<Button onClick={() => void load(agingPage)}>Thử lại</Button>} />}
    <div className="admin-stat-grid">{metrics.map((item) => {
      const difference = item.current - item.previous;
      const percent    = item.previous ? Math.round(difference / item.previous * 100) : null;
      return <Card key={item.label} className={`admin-stat-card admin-stat-${item.tone}`}>
        <div className="admin-stat-card-top"><span>{item.label}</span><span className="admin-stat-icon" aria-hidden="true">{item.icon}</span></div>
        <strong>{item.current.toLocaleString("vi-VN")}</strong>
        <div className="admin-stat-comparison"><span className={difference > 0 ? "is-up" : difference < 0 ? "is-down" : "is-even"}>{difference > 0 ? "↑" : difference < 0 ? "↓" : "→"} {percent === null ? (difference ? `+${difference} đơn` : "0 đơn") : `${Math.abs(percent)}%`}</span> {item.comparison} · kỳ trước {item.previous.toLocaleString("vi-VN")}</div>
      </Card>;
    })}</div>
    <Card className="admin-stat-chart-card">
      <div className="admin-stat-chart-head"><div><span className="admin-page-eyebrow">XU HƯỚNG ĐẶT HÀNG</span><h2>Đơn hàng theo tháng</h2><p>12 tháng gần nhất · múi giờ Việt Nam · gồm mọi trạng thái đơn</p></div><Button onClick={onOpenOrders}>Xem đơn hàng →</Button></div>
      <div className="admin-chart-scroll"><div className="admin-chart-inner"><svg viewBox={`0 0 ${chartWidth} ${chartHeight}`} role="img" aria-label="Biểu đồ số đơn theo 12 tháng gần nhất" preserveAspectRatio="none">
        <defs><linearGradient id="admin-chart-fill" x1="0" x2="0" y1="0" y2="1"><stop offset="0%" stopColor="#44a873" stopOpacity=".24" /><stop offset="100%" stopColor="#44a873" stopOpacity="0" /></linearGradient></defs>
        {[0, 1, 2, 3].map((step) => <line key={step} x1="32" x2="808" y1={26 + step * 54} y2={26 + step * 54} stroke="#e9edf2" strokeDasharray="5 5" />)}
        <path d={`${line} L${points[points.length - 1].x},${chartHeight - 28} L${points[0].x},${chartHeight - 28} Z`} fill="url(#admin-chart-fill)" />
        <path d={line} fill="none" stroke="#399b66" strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" />
        {points.map((point) => <circle key={point.month} cx={point.x} cy={point.y} r="5" fill="#fff" stroke="#399b66" strokeWidth="3"><title>{point.month}: {point.orders} đơn</title></circle>)}
      </svg><div className="admin-chart-labels">{points.map((point) => <span key={point.month} title={`${point.month}: ${point.orders} đơn`}>{point.month.slice(5)}/{point.month.slice(2, 4)}</span>)}</div></div></div>
      <div className="admin-chart-foot"><span>● Số đơn phát sinh</span><span>Cập nhật lúc {new Date(data.as_of).toLocaleString("vi-VN", { timeZone: data.timezone })}</span></div>
    </Card>
    <Card className="admin-stat-chart-card admin-revenue-card">
      <div className="admin-stat-chart-head"><div><span className="admin-page-eyebrow">BÁO CÁO BÁN HÀNG</span><h2>Doanh thu theo ngày</h2><p>Theo ngày tạo đơn tại Việt Nam · chỉ tính đơn Đã giao</p></div><Button onClick={onOpenOrders}>Xem đơn hàng →</Button></div>
      <div className="admin-revenue-filters"><DatePicker.RangePicker format="DD/MM/YYYY" placeholder={["Từ ngày", "Đến ngày"]} value={revenueRange ? [dayjs(revenueRange[0]), dayjs(revenueRange[1])] : null} onChange={(dates) => {
        // Đầu vào: khoảng ngày người dùng chọn; đầu ra: bộ lọc API và trang đầu.
        // Ví dụ: chọn 01–18/11 sẽ chỉ yêu cầu doanh thu các ngày trong khoảng này.
        setRevenueRange(dates?.[0] && dates?.[1] ? [dates[0].format("YYYY-MM-DD"), dates[1].format("YYYY-MM-DD")] : null);
        setRevenue(null);
        setRevenuePage(1);
      }} allowClear /></div>
      {revenueError && <Alert className="admin-report-error" type="error" showIcon message={revenueError} action={<Button size="small" onClick={() => void loadRevenue(revenuePage)}>Thử lại</Button>} />}
      <Table<RevenueDay> className="admin-aging-table" rowKey="day" dataSource={revenue?.items || []} loading={revenueLoading} scroll={{ x: 520 }} locale={{ emptyText: <Empty description="Chưa có đơn Đã giao" /> }} columns={[
        { title: "Ngày tạo đơn", dataIndex: "day", render: (value: string) => `${value.slice(8, 10)}/${value.slice(5, 7)}/${value.slice(0, 4)}` },
        { title: "Số đơn", dataIndex: "order_count", render: (value: number) => value.toLocaleString("vi-VN") },
        { title: "Tổng thành tiền", dataIndex: "total_vnd", render: (value: number) => money(value) },
      ]} pagination={{ current: revenue?.page || revenuePage, pageSize: revenue?.limit || 10, total: revenue?.total || 0, showSizeChanger: false, onChange: (page) => void loadRevenue(page) }} />
    </Card>
    <Card className="admin-stat-chart-card admin-aging-card">
      <div className="admin-stat-chart-head"><div><span className="admin-page-eyebrow">CẦN KIỂM TRA TỒN KHO</span><h2>Sản phẩm nhập quá 3 ngày còn tồn</h2><p>Tính từ lúc tạo lô · gồm cả lô đang ẩn · tổng {data.aging_batches.total.toLocaleString("vi-VN")} lô</p></div><Button onClick={onOpenBatches}>Xem lô nông sản →</Button></div>
      <Table<AgingBatch> className="admin-aging-table" rowKey="id" dataSource={data.aging_batches.items} loading={loading} scroll={{ x: 640 }} locale={{ emptyText: <Empty description="Không có lô nào nhập quá 3 ngày còn tồn" /> }} columns={[
        { title: "Sản phẩm", dataIndex: "product_name" },
        { title: "Mã lô", dataIndex: "batch_code" },
        { title: "Ngày nhập", dataIndex: "created_at", render: (value: string) => new Date(value).toLocaleString("vi-VN", { timeZone: data.timezone }) },
        { title: "Tồn kho", render: (_, row) => `${Number(row.remaining_quantity).toLocaleString("vi-VN")} ${row.unit}` },
      ]} pagination={{ current: data.aging_batches.page, pageSize: data.aging_batches.limit, total: data.aging_batches.total, showSizeChanger: false, onChange: (page) => void load(page) }} />
    </Card>
  </div>;
}
