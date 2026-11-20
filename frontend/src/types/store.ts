/** Kiểu dữ liệu cửa hàng; đầu vào là JSON API, đầu ra là dữ liệu cho giao diện. */
export type Product = {
  id: string;
  slug: string;
  name: string;
  description?: string;
  image_url?: string;
  images?: { id: number; image_url: string }[];
  category: string;
  season?: string;
  growing_region?: string;
  harvest_date?: string;
  batch_code?: string;
  unit: string;
  price: number;
  stock_quantity: number;
};

export type CartLine = { product_id: string; quantity: number; preorder?: boolean };
export type ProductPage = { items: Product[]; total: number; page: number; page_size: number };
export type Quote = {
  items: { product_id: number; name: string; quantity: string; unit: string; unit_price_vnd: number; line_total_vnd: number; preorder: boolean }[];
  is_preorder: boolean;
  subtotal_vnd: number;
  discount_vnd: number;
  shipping_fee_vnd: number | null;
  total_vnd: number;
  currency: string;
  quote_id: string;
};
export type Order = {
  order_code       : string;
  is_preorder      : boolean;
  status           : string;
  created_at       : string;
  recipient_name   : string;
  recipient_phone  : string;
  delivery_address : string;
  payment_method   : string;
  payment_status   : string;
  pay_url          : string | null;
  sepay_checkout   : { action: string; fields: Record<string, string> } | null;
  bank_transfer    : {
    bank_code      : string;
    account_number : string;
    account_name   : string;
    amount_vnd     : number;
    payment_code   : string;
    qr_url         : string;
  } | null;
  bank_transfer_reported_at : string | null;
  payment_error?   : string;
  subtotal_vnd     : number;
  discount_vnd     : number;
  discount_code    : string | null;
  total_vnd        : number;
  initial_subtotal_vnd  : number | null;
  initial_discount_vnd  : number | null;
  initial_total_vnd     : number | null;
  proposed_subtotal_vnd : number | null;
  proposed_discount_vnd : number | null;
  proposed_total_vnd    : number | null;
  price_proposed_at     : string | null;
  price_approval_deadline : string | null;
  price_approved_at     : string | null;
  items            : {
    product_id     : number;
    product_name   : string;
    image_url      : string | null;
    unit           : string;
    quantity       : string;
    unit_price_vnd : number;
    line_total_vnd : number;
    is_preorder    : boolean;
    initial_unit_price_vnd  : number | null;
    initial_line_total_vnd  : number | null;
    proposed_unit_price_vnd : number | null;
    proposed_line_total_vnd : number | null;
  }[];
  history          : {
    from_status : string | null;
    to_status   : string;
    reason      : string | null;
    created_at  : string;
  }[];
};

