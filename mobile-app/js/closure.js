// Port của core/closure_check.py (Python) sang JS — dùng để cảnh báo sai số
// khép ngay tại hiện trường khi 1 tuyến khép kín (điểm đầu = điểm cuối).
// Giữ đúng công thức/ngưỡng để 2 bên (app hiện trường & chương trình bình sai
// chính) luôn ra cùng 1 kết luận cho cùng 1 tuyến.

export const NEAR_LIMIT_RATIO = 0.9;
export const STATUS_OK = "Đạt";
export const STATUS_FAIL = "Không đạt";
export const FLAG_NEAR_LIMIT = "sát giới hạn";
export const FLAG_OVER_LIMIT = "Vượt giới hạn";

/**
 * @param {number} whMm sai số khép độ cao (mm), có dấu
 * @param {number} totalStations tổng số trạm đo trong tuyến ([N])
 * @param {number} kCoefficientMm hệ số k (mặc định 0.3)
 */
export function checkClosure(whMm, totalStations, kCoefficientMm = 0.3) {
  const whGhMm = kCoefficientMm * Math.sqrt(totalStations);
  let status;
  let flag = null;

  if (Math.abs(whMm) <= whGhMm) {
    status = STATUS_OK;
    const ratio = whGhMm > 0 ? Math.abs(whMm) / whGhMm : 0;
    if (ratio >= NEAR_LIMIT_RATIO) flag = FLAG_NEAR_LIMIT;
  } else {
    status = STATUS_FAIL;
    flag = FLAG_OVER_LIMIT;
  }

  return { whMm, whGhMm, status, flag };
}
