import type { Config } from "tailwindcss";

// Đầu vào: đường dẫn các trang và thành phần; đầu ra: danh sách lớp CSS cần tạo.
// Ví dụ: lớp min-h-screen trong page.tsx được Tailwind nhận diện.
const config: Config = {
  content: ["./src/**/*.{js,ts,jsx,tsx,mdx}"],
  theme: {
    extend: {},
  },
  plugins: [],
};

export default config;
