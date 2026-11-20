import { Suspense } from "react";
import { Catalog } from "@/features/products/catalog";
export default function Page() { return <Suspense fallback={<div className="p-8">Đang tải sản phẩm...</div>}><Catalog /></Suspense>; }
