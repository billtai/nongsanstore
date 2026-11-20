/** Dữ liệu bảng quản trị; đầu vào JSON API, đầu ra hàng và phân trang. */
export type Row = Record<string, any> & { id: number };
export type Section = "overview" | "products" | "batches" | "orders" | "preorders" | "discounts" | "customers" | "units" | "procurement";
export type PageData = { items: Row[]; total: number; page: number; per_page: number };

