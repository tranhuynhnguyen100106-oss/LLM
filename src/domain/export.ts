import type { UnderwritingResult } from "./engine";
import { NHAN_TRANG_THAI, tien, so_thap_phan } from "./engine";

export function generateMarkdownReport(result: UnderwritingResult, aiSummary = ""): string {
  const d = result.du_lieu;
  const metricLines = result.chi_so
    .map((m) => `- **${m.label}:** ${m.value_display} — ${m.formula} (${m.status})`)
    .join("\n");

  const riskLines =
    result.canh_bao
      .map((r) => `- **${r.code} · ${r.name} [${r.severity}]:** ${r.description}`)
      .join("\n") || "- Không phát hiện mâu thuẫn trọng yếu theo các quy tắc minh họa đã cấu hình.";

  const missingLines =
    result.thong_tin_thieu.map((item) => `- ${item}`).join("\n") ||
    "- Không phát hiện hạng mục bắt buộc còn thiếu.";

  const questionLines = result.cau_hoi_xac_minh.map((item) => `- ${item}`).join("\n");

  const evidenceLines =
    result.canh_bao
      .flatMap((r) =>
        r.evidence.map(
          (e) =>
            `- **${r.code}:** ${e.document}, trang ${e.page ?? "không xác định"}, ${e.field} = ${e.value}`
        )
      )
      .join("\n") || "- Không có bằng chứng rủi ro được tạo.";

  let report = `# TÓM TẮT THẨM ĐỊNH TÍN DỤNG

**Mã hồ sơ:** ${result.ma_ho_so}  
**Trạng thái thẩm định:** ${NHAN_TRANG_THAI[result.trang_thai] ?? result.trang_thai}  
**Thời điểm xử lý:** ${result.thoi_diem_xu_ly}

## 1. Tổng quan khách hàng
- **Khách hàng:** ${d.ho_ten_khach_hang ?? "Thông tin chưa đủ"}
- **Đơn vị công tác:** ${d.don_vi_cong_tac_ke_khai ?? "Thông tin chưa đủ"}
- **Chức danh:** ${d.chuc_danh_ke_khai ?? "Thông tin chưa đủ"}

## 2. Đề nghị vay vốn
- **Số tiền đề nghị vay:** ${tien(d.so_tien_de_nghi_vay)}
- **Thời hạn:** ${d.thoi_han_vay_thang !== null ? `${d.thoi_han_vay_thang} tháng` : "—"}
- **Mục đích:** ${d.muc_dich_vay ?? "Thông tin chưa đủ"}

## 3. Thông tin tài chính dùng để tính
- **Thu nhập dùng để tính:** ${tien(result.thu_nhap_dung_de_tinh)}
- **Nguồn / cơ sở lựa chọn:** ${result.nguon_thu_nhap_dung_de_tinh}
- **Trạng thái nguồn:** ${
    result.thu_nhap_duoc_xac_minh_doc_lap
      ? "Đã có nguồn đối chiếu độc lập (lương hoặc sao kê)"
      : "Chỉ kê khai hoặc chưa đủ dữ liệu"
  }
- **Khoản trả nợ quan sát hàng tháng:** ${tien(d.nghia_vu_no_quan_sat)}
- **Số dư bình quân:** ${tien(d.so_du_binh_quan)}

## 4. Chỉ số tín dụng chính
${metricLines}

## 5. Kiểm tra nhất quán và cảnh báo rủi ro
${riskLines}

## 6. Thông tin còn thiếu
${missingLines}

## 7. Câu hỏi cần chuyên viên xác minh
${questionLines}

## 8. Bằng chứng tham chiếu
${evidenceLines}
`;

  if (aiSummary.trim()) {
    report += `\n## 9. Diễn giải bổ sung bằng AI\n${aiSummary.trim()}\n`;
  }

  report += `\n## 10. Trạng thái xem xét của con người
**${NHAN_TRANG_THAI[result.trang_thai] ?? result.trang_thai}**. Ứng dụng này chỉ hỗ trợ thẩm định tín dụng, không tự phê duyệt hoặc từ chối khoản vay. Quyết định cuối cùng bắt buộc do con người xem xét.
`;

  return report;
}

export function generateStructuredJson(result: UnderwritingResult): string {
  return JSON.stringify(result, null, 2);
}

export function downloadFile(filename: string, content: string, mimeType: string): void {
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
}
