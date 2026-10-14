import {
  type RawCaseData,
  type DocumentDescriptor,
  type UnderwritingThresholds,
  DEFAULT_THRESHOLDS,
  runUnderwriting,
  type UnderwritingResult
} from "./engine";
import type { DemoCaseItem } from "./contracts";

export const BASE_DATA: RawCaseData = {
  ho_ten_khach_hang: "Nguyễn Minh Anh",
  don_vi_cong_tac_ke_khai: "Công ty Cổ phần Công nghệ Aurora",
  don_vi_cong_tac_chung_tu: "Công ty Cổ phần Công nghệ Aurora",
  chuc_danh_ke_khai: "Chuyên viên phân tích dữ liệu",
  chuc_danh_chung_tu: "Chuyên viên phân tích dữ liệu",
  ngay_bat_dau_ke_khai: "2022-06-01",
  ngay_bat_dau_chung_tu: "2022-06-01",
  tham_nien_lam_viec_thang: 48,
  thu_nhap_ke_khai: 25_000_000,
  luong_thuc_nhan: 24_000_000,
  thu_nhap_qua_sao_ke: 23_800_000,
  so_tien_de_nghi_vay: 300_000_000,
  thoi_han_vay_thang: 36,
  khoan_tra_du_kien: 7_500_000,
  nghia_vu_no_ke_khai: 2_000_000,
  nghia_vu_no_quan_sat: 2_000_000,
  chi_phi_sinh_hoat: 9_000_000,
  so_du_binh_quan: 18_000_000,
  bien_dong_thu_nhap: 0.06,
  muc_dich_vay: "Sửa chữa nhà ở"
};

export interface DemoCaseDefinition {
  case_name: string;
  case_code: string;
  title: string;
  description: string;
  overrides: Partial<RawCaseData>;
  confidenceOverrides: Record<string, number>;
  missingDocs: ("application" | "income" | "statement" | "debt")[];
}

export const DEMO_CASES: DemoCaseDefinition[] = [
  {
    case_name: "CASE-01 — Hồ sơ bình thường",
    case_code: "CASE-01",
    title: "Hồ sơ bình thường và nhất quán",
    description: "Bộ chứng từ đầy đủ, thu nhập và công tác khớp nhau qua cả 3 nguồn; DTI và DSR trong ngưỡng an toàn.",
    overrides: {},
    confidenceOverrides: {},
    missingDocs: []
  },
  {
    case_name: "CASE-02 — Thiếu thu nhập",
    case_code: "CASE-02",
    title: "Thiếu dữ liệu thu nhập",
    description: "Không có thông tin thu nhập kê khai, chứng từ lương hoặc ghi có sao kê; kích hoạt trạng thái thiếu thông tin.",
    overrides: {
      luong_thuc_nhan: null,
      thu_nhap_qua_sao_ke: null,
      thu_nhap_ke_khai: null
    },
    confidenceOverrides: {},
    missingDocs: []
  },
  {
    case_name: "CASE-03 — Thu nhập không nhất quán",
    case_code: "CASE-03",
    title: "Thu nhập chênh lệch đáng kể giữa các nguồn",
    description: "Kê khai 25M, lương thực nhận 18M, sao kê 14M; chênh lệch 44% vượt ngưỡng cảnh báo nghiêm trọng.",
    overrides: {
      thu_nhap_ke_khai: 25_000_000,
      luong_thuc_nhan: 18_000_000,
      thu_nhap_qua_sao_ke: 14_000_000
    },
    confidenceOverrides: {},
    missingDocs: []
  },
  {
    case_name: "CASE-04 — Đơn vị công tác không khớp",
    case_code: "CASE-04",
    title: "Đơn vị công tác không trùng khớp",
    description: "Đơn vay ghi Aurora nhưng chứng từ ghi Công ty TNHH Bán lẻ Zenith; kích hoạt cảnh báo cấp cao.",
    overrides: {
      don_vi_cong_tac_chung_tu: "Công ty TNHH Bán lẻ Zenith"
    },
    confidenceOverrides: {},
    missingDocs: []
  },
  {
    case_name: "CASE-05 — Nghĩa vụ nợ không nhất quán",
    case_code: "CASE-05",
    title: "Nghĩa vụ nợ quan sát cao hơn kê khai",
    description: "Kê khai 2M nợ nhưng quan sát sao kê thanh toán 5M; chênh lệch 150% chỉ ra có thể có khoản vay ngoài.",
    overrides: {
      nghia_vu_no_ke_khai: 2_000_000,
      nghia_vu_no_quan_sat: 5_000_000
    },
    confidenceOverrides: {},
    missingDocs: []
  },
  {
    case_name: "CASE-06 — DTI cao",
    case_code: "CASE-06",
    title: "Tỷ lệ gánh nặng nợ DTI cao",
    description: "Thu nhập 18M nhưng nghĩa vụ nợ 8M (DTI 44,4%), vượt ngưỡng an toàn minh họa 40%.",
    overrides: {
      thu_nhap_ke_khai: 18_000_000,
      luong_thuc_nhan: 18_000_000,
      thu_nhap_qua_sao_ke: 18_000_000,
      nghia_vu_no_ke_khai: 8_000_000,
      nghia_vu_no_quan_sat: 8_000_000
    },
    confidenceOverrides: {},
    missingDocs: []
  },
  {
    case_name: "CASE-07 — Sao kê không đọc được",
    case_code: "CASE-07",
    title: "Tài liệu sao kê không đọc được",
    description: "Tệp sao kê thiếu lớp văn bản hoặc bị mã hóa, thiếu cơ sở xác minh dòng tiền và số dư bình quân.",
    overrides: {
      thu_nhap_qua_sao_ke: null,
      so_du_binh_quan: null,
      bien_dong_thu_nhap: null
    },
    confidenceOverrides: {},
    missingDocs: ["statement"]
  },
  {
    case_name: "CASE-08 — Đơn vay chưa đầy đủ",
    case_code: "CASE-08",
    title: "Đơn vay thiếu số tiền và kỳ hạn đề nghị",
    description: "Thiếu các thông số cốt lõi của đề xuất tín dụng; hệ thống gắn nhãn Thông tin chưa đủ.",
    overrides: {
      so_tien_de_nghi_vay: null,
      thoi_han_vay_thang: null
    },
    confidenceOverrides: {},
    missingDocs: []
  },
  {
    case_name: "CASE-09 — Độ tin cậy thấp",
    case_code: "CASE-09",
    title: "Độ tin cậy trích xuất tài liệu thấp",
    description: "Các trường dữ liệu quan trọng có điểm confidence < 75% do bản scan mờ; yêu cầu cán bộ đối chiếu thủ công.",
    overrides: {},
    confidenceOverrides: {
      luong_thuc_nhan: 0.58,
      don_vi_cong_tac_chung_tu: 0.61
    },
    missingDocs: []
  },
  {
    case_name: "CASE-10 — Nhiều cảnh báo đồng thời",
    case_code: "CASE-10",
    title: "Nhiều cảnh báo rủi ro đồng thời",
    description: "Mâu thuẫn thu nhập, sai lệch đơn vị công tác, nợ ngoài kê khai, đệm số dư thấp và biến động tiền tệ cao.",
    overrides: {
      thu_nhap_ke_khai: 28_000_000,
      luong_thuc_nhan: 19_000_000,
      thu_nhap_qua_sao_ke: 15_000_000,
      don_vi_cong_tac_chung_tu: "Công ty TNHH Bán lẻ Zenith",
      nghia_vu_no_ke_khai: 2_000_000,
      nghia_vu_no_quan_sat: 8_000_000,
      khoan_tra_du_kien: 9_000_000,
      so_du_binh_quan: 5_000_000,
      bien_dong_thu_nhap: 0.34
    },
    confidenceOverrides: {},
    missingDocs: []
  }
];

export function getDemoCaseItems(): DemoCaseItem[] {
  return DEMO_CASES.map((item) => ({
    case_name: item.case_name,
    case_code: item.case_code,
    title: item.title,
    description: item.description
  }));
}

export function evaluateDemoCase(
  caseName: string,
  thresholds: UnderwritingThresholds = DEFAULT_THRESHOLDS
): UnderwritingResult {
  const definition = DEMO_CASES.find((c) => c.case_name === caseName) ?? DEMO_CASES[0]!;
  const mergedData: RawCaseData = {
    ...BASE_DATA,
    ...definition.overrides
  };

  const docs: DocumentDescriptor[] = [];
  if (!definition.missingDocs.includes("application")) {
    docs.push({
      name: "don_de_nghi_vay.pdf",
      expectedType: "application",
      detectedType: "application",
      pages: 2,
      status: "Đã trích xuất",
      confidence: 0.99
    });
  }
  if (!definition.missingDocs.includes("income")) {
    docs.push({
      name: "chung_tu_thu_nhap.pdf",
      expectedType: "income",
      detectedType: "income",
      pages: 2,
      status: "Đã trích xuất",
      confidence: 0.99
    });
  }
  if (!definition.missingDocs.includes("statement")) {
    docs.push({
      name: "sao_ke_ngan_hang_6_thang.pdf",
      expectedType: "statement",
      detectedType: "statement",
      pages: 6,
      status: "Đã trích xuất",
      confidence: 0.99
    });
  } else {
    docs.push({
      name: "sao_ke_ngan_hang_6_thang.pdf",
      expectedType: "statement",
      detectedType: "unknown",
      pages: 6,
      status: "Không đọc được",
      confidence: 0.25
    });
  }
  docs.push({
    name: "thong_tin_nghia_vu_no.pdf",
    expectedType: "debt",
    detectedType: "debt",
    pages: 1,
    status: "Đã trích xuất",
    confidence: 0.99
  });

  return runUnderwriting(
    definition.case_code,
    definition.case_name,
    mergedData,
    docs,
    thresholds,
    definition.confidenceOverrides
  );
}
