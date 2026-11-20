"""Trạng thái đơn hợp lệ; ví dụ pending có thể chuyển confirmed hoặc cancelled."""

TRANSITIONS = {
    "preordered" : {"cancelled"},
    "awaiting_price_approval" : {"cancelled"},
    "pending"    : {"confirmed", "cancelled"},
    "confirmed"  : {"preparing", "cancelled"},
    "preparing"  : {"delivering"},
    "delivering" : {"completed"},
    "completed"  : set(),
    "cancelled"  : set(),
}
