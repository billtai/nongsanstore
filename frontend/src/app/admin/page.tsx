import { AdminDashboard } from "@/features/admin/dashboard";

/** Điểm vào trang quản trị; không nhận đầu vào, trả giao diện quản trị. Ví dụ: GET /admin. */
export default function AdminPage() {
  return <AdminDashboard />;
}
