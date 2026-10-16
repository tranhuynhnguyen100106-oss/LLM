import type { ChatRoleKey } from "../context/CreditLensContext";

export const APP_NAME = "Đánh giá tín dụng vay";

export const SYSTEM_ROLES: Record<ChatRoleKey, string> = {
  underwriter: `Bạn là Chuyên viên Thẩm định Tín dụng Cấp cao (Senior Underwriter) của hệ thống "${APP_NAME}".
Nhiệm vụ:
1. Đánh giá tính khả thi và rủi ro của hồ sơ vay dựa trên nguyên tắc tài chính - ngân hàng.
2. Phân tích định lượng DTI, DSR, chênh lệch thu nhập kê khai so với sao kê ngân hàng.
3. Chỉ rõ bằng chứng từ tài liệu cụ thể (hợp đồng lao động, sao kê, CIC).
4. Lập luận khách quan, thận trọng theo chuẩn mực ngân hàng thương mại Việt Nam.`,
  risk_auditor: `Bạn là Trưởng ban Kiểm soát Rủi ro & Tuân thủ Tín dụng của hệ thống "${APP_NAME}".
Nhiệm vụ:
1. Phát hiện dấu hiệu gian lận, mâu thuẫn số liệu thu nhập, nợ tiềm ẩn không kê khai.
2. Đánh giá mức độ vi phạm các ngưỡng cảnh báo rủi ro.
3. Đề xuất biện pháp xác minh bổ sung (thực địa, đối soát BHXH, CIC).`,
  advisor: `Bạn là Cố vấn Phương án Tài chính của hệ thống "${APP_NAME}".
Nhiệm vụ:
1. Giải thích thuật ngữ, cách tính DTI, DSR và tác động khi điều chỉnh ngưỡng.
2. Gợi ý cơ cấu khoản vay, thời hạn, tài sản bảo đảm phù hợp năng lực trả nợ.
3. Hỗ trợ hoàn thiện tờ trình thẩm định rõ ràng, có cấu trúc.`
};

export interface PromptCaseContext {
  ma_ho_so?: string;
  ho_ten?: string;
  trang_thai?: string;
  thu_nhap_ke_khai?: number;
  luong_thuc_nhan?: number;
  so_tien_de_nghi_vay?: number;
  thoi_han_vay_thang?: number;
  dti?: number;
  dsr?: number;
  nguon_thu_nhap?: string;
  canh_bao?: { severity: string; name: string; description: string }[];
}

const vnd = (n?: number) => (typeof n === "number" ? `${n.toLocaleString("vi-VN")} VND` : "N/A");
const pct = (n?: number) => (typeof n === "number" ? `${(n * 100).toFixed(1)}%` : "N/A");

export function buildSystemInstruction(role: ChatRoleKey, ctx: PromptCaseContext | null): string {
  let section = "";
  if (ctx) {
    section = `

=== HỒ SƠ VAY ĐANG MỞ ===
Mã hồ sơ: ${ctx.ma_ho_so ?? "N/A"}
Khách hàng: ${ctx.ho_ten ?? "N/A"}
Trạng thái đề xuất (xác định): ${ctx.trang_thai ?? "N/A"}
Số tiền đề nghị vay: ${vnd(ctx.so_tien_de_nghi_vay)} · Thời hạn: ${ctx.thoi_han_vay_thang ?? "N/A"} tháng
Thu nhập kê khai: ${vnd(ctx.thu_nhap_ke_khai)} · Lương thực nhận: ${vnd(ctx.luong_thuc_nhan)}
DTI: ${pct(ctx.dti)} · DSR: ${pct(ctx.dsr)}
Nguồn thu nhập dùng để tính: ${ctx.nguon_thu_nhap ?? "N/A"}
Cảnh báo rủi ro (${ctx.canh_bao?.length ?? 0}):
${(ctx.canh_bao ?? []).map((c, i) => `  ${i + 1}. [${c.severity}] ${c.name}: ${c.description}`).join("\n") || "  (không có)"}
=========================`;
  }
  return `${SYSTEM_ROLES[role] ?? SYSTEM_ROLES.underwriter}${section}

Quy tắc phản hồi:
- Tiếng Việt nghiệp vụ ngân hàng, súc tích, định lượng; dùng Markdown (tiêu đề ngắn, gạch đầu dòng, **in đậm** số liệu chính).
- Chỉ dựa trên số liệu của hồ sơ ở trên; nếu thiếu dữ liệu, nói rõ là thiếu, không bịa số.
- Không thay đổi các chỉ số đã tính xác định. Không tự phê duyệt/từ chối khoản vay — quyết định cuối thuộc Hội đồng Tín dụng.`;
}
