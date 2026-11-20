/**
 * Cho ảnh sản phẩm bay từ vị trí đang xem tới biểu tượng giỏ hàng.
 * Đầu vào: URL ảnh và phần tử bắt đầu (ảnh hoặc nút thêm); đầu ra: hiệu ứng không đổi dữ liệu giỏ.
 * Ví dụ: flyToCart(product.image_url, imageElement) sau khi thêm sản phẩm thành công.
 */
export function flyToCart(imageUrl: string | undefined, source: Element | null): void {
  const cart = document.querySelector("header .cart-link");
  if (!cart || !source || window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

  const start          = source.getBoundingClientRect();
  const end            = cart.getBoundingClientRect();
  const size           = 64;
  const startX         = start.left + start.width / 2 - size / 2;
  const startY         = start.top + start.height / 2 - size / 2;
  const endX           = end.left + end.width / 2 - size / 2;
  const endY           = end.top + end.height / 2 - size / 2;
  const flyingImage    = document.createElement(imageUrl ? "img" : "span");

  if (imageUrl && flyingImage instanceof HTMLImageElement) {
    flyingImage.src = imageUrl;
    flyingImage.alt = "";
    flyingImage.style.objectFit = "cover";
  } else {
    flyingImage.textContent = "✳";
    flyingImage.style.display = "grid";
    flyingImage.style.placeItems = "center";
    flyingImage.style.color = "#1e4b32";
    flyingImage.style.fontSize = "36px";
  }

  Object.assign(flyingImage.style, {
    position      : "fixed",
    left          : `${startX}px`,
    top           : `${startY}px`,
    width         : `${size}px`,
    height        : `${size}px`,
    borderRadius  : "16px",
    background    : "#edf3e3",
    boxShadow     : "0 8px 24px #173d2a40",
    pointerEvents : "none",
    zIndex        : "1000",
  });
  document.body.appendChild(flyingImage);

  // Đi qua điểm cao hơn đường thẳng để ảnh có cảm giác nhảy vào giỏ.
  // Ví dụ: ảnh ở giữa trang sẽ nhô lên trước khi thu nhỏ tại biểu tượng giỏ.
  const animation = flyingImage.animate([
    { transform : "translate(0, 0) scale(1)", opacity : 1 },
    { transform : `translate(${(endX - startX) * .5}px, ${Math.min(endY - startY, -80) - 70}px) scale(.9)`, opacity : 1, offset : .5 },
    { transform : `translate(${endX - startX}px, ${endY - startY}px) scale(.25)`, opacity : .2 },
  ], { duration : 700, easing : "ease-in-out" });
  animation.onfinish = () => flyingImage.remove();
  animation.oncancel = () => flyingImage.remove();
}
