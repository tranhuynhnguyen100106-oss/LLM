import type {
  CrossDocumentComparison,
  DocumentItem,
  EvidenceReference,
  ExtractedFieldItem,
  FindingItem,
  MetricItem,
  RiskItem,
  SourceRole,
  StatusTone,
  ThresholdReference,
  V2CorePageViewModel,
  V2SummaryPageViewModel,
  V2MethodologyPageViewModel,
  ThemeMode
} from "./contracts";

export interface UnderwritingThresholds {
  do_tin_cay_thap: number;
  chenh_lech_thu_nhap: number;
  chenh_lech_thu_nhap_nghiem_trong: number;
  chenh_lech_no: number;
  dti_canh_bao: number;
  dsr_canh_bao: number;
  he_so_dem_so_du_thap: number;
  bien_dong_thu_nhap_cao: number;
}

export const DEFAULT_THRESHOLDS: UnderwritingThresholds = {
  do_tin_cay_thap: 0.75,
  chenh_lech_thu_nhap: 0.15,
  chenh_lech_thu_nhap_nghiem_trong: 0.30,
  chenh_lech_no: 0.20,
  dti_canh_bao: 0.40,
  dsr_canh_bao: 0.45,
  he_so_dem_so_du_thap: 1.00,
  bien_dong_thu_nhap_cao: 0.25,
};

export const THRESHOLD_LABELS: Record<keyof UnderwritingThresholds, string> = {
  do_tin_cay_thap: "Độ tin cậy trích xuất tối thiểu",
  chenh_lech_thu_nhap: "Chênh lệch thu nhập cảnh báo",
  chenh_lech_thu_nhap_nghiem_trong: "Chênh lệch thu nhập nghiêm trọng",
  chenh_lech_no: "Chênh lệch nghĩa vụ nợ",
  dti_canh_bao: "Cảnh báo tỷ lệ DTI hiện hữu",
  dsr_canh_bao: "Cảnh báo tỷ lệ DSR dự kiến",
  he_so_dem_so_du_thap: "Hệ số đệm số dư tối thiểu",
  bien_dong_thu_nhap_cao: "Biến động thu nhập cao",
};

export interface RawCaseData {
  ho_ten_khach_hang: string | null;
  don_vi_cong_tac_ke_khai: string | null;
  don_vi_cong_tac_chung_tu: string | null;
  chuc_danh_ke_khai: string | null;
  chuc_danh_chung_tu: string | null;
  ngay_bat_dau_ke_khai: string | null;
  ngay_bat_dau_chung_tu: string | null;
  tham_nien_lam_viec_thang: number | null;
  thu_nhap_ke_khai: number | null;
  luong_thuc_nhan: number | null;
  thu_nhap_qua_sao_ke: number | null;
  so_tien_de_nghi_vay: number | null;
  thoi_han_vay_thang: number | null;
  khoan_tra_du_kien: number | null;
  nghia_vu_no_ke_khai: number | null;
  nghia_vu_no_quan_sat: number | null;
  chi_phi_sinh_hoat: number | null;
  so_du_binh_quan: number | null;
  bien_dong_thu_nhap: number | null;
  muc_dich_vay: string | null;
}

export interface DocumentDescriptor {
  name: string;
  expectedType: "application" | "income" | "statement" | "debt";
  detectedType: string;
  pages: number;
  status: "Đã trích xuất" | "Không đọc được";
  confidence: number;
}

export interface UnderwritingResult {
  ma_ho_so: string;
  ten_ho_so: string;
  du_lieu: RawCaseData;
  documents: DocumentDescriptor[];
  fields: ExtractedFieldItem[];
  chi_so: MetricItem[];
  canh_bao: RiskItem[];
  thong_tin_thieu: string[];
  cau_hoi_xac_minh: string[];
  trang_thai: "REVIEW READY" | "HUMAN REVIEW REQUIRED" | "INSUFFICIENT INFORMATION";
  thu_nhap_dung_de_tinh: number | null;
  nguon_thu_nhap_dung_de_tinh: string;
  thu_nhap_duoc_xac_minh_doc_lap: boolean;
  thoi_diem_xu_ly: string;
  thoi_gian_xu_ly_ms: number;
}

export const NHAN_TRANG_THAI: Record<string, string> = {
  "REVIEW READY": "SẴN SÀNG ĐỂ THẨM ĐỊNH",
  "HUMAN REVIEW REQUIRED": "CẦN CON NGƯỜI XEM XÉT",
  "INSUFFICIENT INFORMATION": "THÔNG TIN CHƯA ĐỦ"
};

export const NHAN_MUC_DO: Record<string, string> = {
  HIGH: "CAO",
  MEDIUM: "TRUNG BÌNH",
  LOW: "THẤP",
  INFO: "THÔNG TIN"
};

export const NHAN_RUI_RO: Record<string, string> = {
  INCOME_MISMATCH: "Thu nhập không nhất quán",
  EMPLOYER_MISMATCH: "Đơn vị công tác không khớp",
  POSSIBLE_UNDECLARED_DEBT: "Có thể có khoản nợ chưa kê khai",
  JOB_TITLE_MISMATCH: "Chức danh không khớp",
  EMPLOYMENT_DATE_MISMATCH: "Thời điểm làm việc không khớp",
  HIGH_DTI_DEMO: "DTI cao theo ngưỡng minh họa",
  HIGH_DSR_DEMO: "DSR cao theo ngưỡng minh họa",
  LOW_BALANCE_BUFFER: "Hệ số đệm số dư thấp",
  HIGH_INCOME_VOLATILITY: "Thu nhập biến động cao",
  LOW_EXTRACTION_CONFIDENCE: "Độ tin cậy trích xuất thấp"
};

export function tien(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return Math.round(value).toLocaleString("vi-VN") + " VND";
}

export function phan_tram(value: number | null | undefined): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return (value * 100).toFixed(1).replace(".", ",") + "%";
}

export function so_thap_phan(value: number | null | undefined, decimals = 2): string {
  if (value === null || value === undefined || !Number.isFinite(value)) return "—";
  return value.toFixed(decimals).replace(".", ",");
}

export function chia_an_toan(tu_so: number | null | undefined, mau_so: number | null | undefined): number | null {
  if (tu_so === null || tu_so === undefined || mau_so === null || mau_so === undefined || mau_so <= 0) {
    return null;
  }
  const res = tu_so / mau_so;
  return Number.isFinite(res) ? res : null;
}

export function chuan_hoa_chuoi(value: string | null | undefined): string {
  if (!value) return "";
  return value
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/\b(cong ty|company|co|ltd|jsc|tnhh|cp)\b/g, "")
    .replace(/[^a-z0-9]/g, "");
}

export function chuan_hoa_ngay(value: string | null | undefined): string | null {
  if (!value) return null;
  const text = value.trim();
  const m1 = text.match(/(\d{4})[-/](\d{2})[-/](\d{2})/);
  if (m1) return `${m1[1]}-${m1[2]}-${m1[3]}`;
  const m2 = text.match(/(\d{2})[-/](\d{2})[-/](\d{4})/);
  if (m2) return `${m2[3]}-${m2[2]}-${m2[1]}`;
  return null;
}

export function chon_thu_nhap_dung_de_tinh(data: RawCaseData): [number | null, string, boolean] {
  const hop_le: [number, string][] = [];
  if (typeof data.luong_thuc_nhan === "number" && data.luong_thuc_nhan > 0) {
    hop_le.push([data.luong_thuc_nhan, "Lương thực nhận"]);
  }
  if (typeof data.thu_nhap_qua_sao_ke === "number" && data.thu_nhap_qua_sao_ke > 0) {
    hop_le.push([data.thu_nhap_qua_sao_ke, "Ghi có bình quân sao kê"]);
  }
  if (hop_le.length > 0) {
    hop_le.sort((a, b) => a[0] - b[0]);
    const chosen = hop_le[0]!;
    const suffix = hop_le.length > 1 ? "giá trị thận trọng hơn" : "nguồn đối chiếu hiện có";
    return [chosen[0], `${chosen[1]} (${suffix})`, true];
  }
  if (typeof data.thu_nhap_ke_khai === "number" && data.thu_nhap_ke_khai > 0) {
    return [data.thu_nhap_ke_khai, "Thu nhập kê khai (chưa xác minh độc lập)", false];
  }
  return [null, "Không đủ dữ liệu", false];
}

export function runUnderwriting(
  caseId: string,
  caseTitle: string,
  data: RawCaseData,
  documents: DocumentDescriptor[],
  thresholds: UnderwritingThresholds = DEFAULT_THRESHOLDS,
  confidenceOverrides: Record<string, number> = {}
): UnderwritingResult {
  const startTime = performance.now();
  const [incomeForCalc, incomeSource, incomeVerified] = chon_thu_nhap_dung_de_tinh(data);
  const debt = data.nghia_vu_no_quan_sat !== null ? data.nghia_vu_no_quan_sat : data.nghia_vu_no_ke_khai;

  const dti = chia_an_toan(debt, incomeForCalc);
  const dsr = chia_an_toan(
    debt !== null && data.khoan_tra_du_kien !== null ? debt + data.khoan_tra_du_kien : null,
    incomeForCalc
  );
  const disposable =
    incomeForCalc !== null && debt !== null && data.chi_phi_sinh_hoat !== null
      ? incomeForCalc - debt - data.chi_phi_sinh_hoat
      : null;
  const balanceBuffer = chia_an_toan(data.so_du_binh_quan, data.khoan_tra_du_kien);

  const incomeCandidates = [data.thu_nhap_ke_khai, data.luong_thuc_nhan, data.thu_nhap_qua_sao_ke].filter(
    (v): v is number => typeof v === "number" && v > 0
  );
  const incomeDifference =
    incomeCandidates.length >= 2
      ? (Math.max(...incomeCandidates) - Math.min(...incomeCandidates)) / Math.max(...incomeCandidates)
      : null;

  function metricStatus(
    val: number | null,
    threshold: number,
    lowerIsBad = false
  ): "Trong ngưỡng minh họa" | "Cần chú ý" | "Chưa đủ dữ liệu" {
    if (val === null) return "Chưa đủ dữ liệu";
    const warn = lowerIsBad ? val < threshold : val > threshold;
    return warn ? "Cần chú ý" : "Trong ngưỡng minh họa";
  }

  const chiSo: MetricItem[] = [
    {
      key: "dti",
      label: "DTI hiện hữu",
      value_display: phan_tram(dti),
      raw_value: dti,
      reference: `Ngưỡng minh họa: ≤ ${phan_tram(thresholds.dti_canh_bao)}`,
      status: metricStatus(dti, thresholds.dti_canh_bao),
      status_tone: dti === null ? "neutral" : dti > thresholds.dti_canh_bao ? "warning" : "success",
      formula: "Nghĩa vụ nợ hiện hữu ÷ Thu nhập dùng để tính",
      note: `Nguồn thu nhập: ${incomeSource}.`,
      source_role: "calculated"
    },
    {
      key: "dsr",
      label: "DSR dự kiến",
      value_display: phan_tram(dsr),
      raw_value: dsr,
      reference: `Ngưỡng minh họa: ≤ ${phan_tram(thresholds.dsr_canh_bao)}`,
      status: metricStatus(dsr, thresholds.dsr_canh_bao),
      status_tone: dsr === null ? "neutral" : dsr > thresholds.dsr_canh_bao ? "danger" : "success",
      formula: "(Nợ hiện hữu + Khoản trả dự kiến) ÷ Thu nhập dùng để tính",
      note: "Khoản trả dự kiến là đầu vào thủ công; hệ thống không tự đặt lãi suất.",
      source_role: "calculated"
    },
    {
      key: "disposable_income",
      label: "Thu nhập còn lại trước khoản vay mới",
      value_display: tien(disposable),
      raw_value: disposable,
      reference: "Đòi hỏi giá trị dương",
      status: disposable === null ? "Chưa đủ dữ liệu" : disposable < 0 ? "Cần chú ý" : "Trong ngưỡng minh họa",
      status_tone: disposable === null ? "neutral" : disposable < 0 ? "danger" : "success",
      formula: "Thu nhập dùng để tính − Nợ hiện hữu − Chi phí sinh hoạt",
      note: "Chưa trừ khoản trả dự kiến của khoản vay mới.",
      source_role: "calculated"
    },
    {
      key: "balance_buffer",
      label: "Hệ số đệm số dư",
      value_display: balanceBuffer === null ? "—" : `${so_thap_phan(balanceBuffer)}×`,
      raw_value: balanceBuffer,
      reference: `Ngưỡng minh họa: ≥ ${so_thap_phan(thresholds.he_so_dem_so_du_thap)}×`,
      status: metricStatus(balanceBuffer, thresholds.he_so_dem_so_du_thap, true),
      status_tone:
        balanceBuffer === null ? "neutral" : balanceBuffer < thresholds.he_so_dem_so_du_thap ? "warning" : "success",
      formula: "Số dư bình quân ÷ Khoản trả dự kiến",
      note: "Chỉ báo thanh khoản dựa trên số dư bình quân.",
      source_role: "calculated"
    },
    {
      key: "income_difference",
      label: "Chênh lệch thu nhập",
      value_display: phan_tram(incomeDifference),
      raw_value: incomeDifference,
      reference: `Ngưỡng minh họa: ≤ ${phan_tram(thresholds.chenh_lech_thu_nhap)}`,
      status: metricStatus(incomeDifference, thresholds.chenh_lech_thu_nhap),
      status_tone:
        incomeDifference === null ? "neutral" : incomeDifference > thresholds.chenh_lech_thu_nhap ? "warning" : "success",
      formula: "(Nguồn cao nhất − Nguồn thấp nhất) ÷ Nguồn cao nhất",
      note: "So sánh đơn vay, chứng từ thu nhập và sao kê.",
      source_role: "calculated"
    },
    {
      key: "income_volatility",
      label: "Biến động thu nhập",
      value_display: phan_tram(data.bien_dong_thu_nhap),
      raw_value: data.bien_dong_thu_nhap,
      reference: `Ngưỡng minh họa: ≤ ${phan_tram(thresholds.bien_dong_thu_nhap_cao)}`,
      status: metricStatus(data.bien_dong_thu_nhap, thresholds.bien_dong_thu_nhap_cao),
      status_tone:
        data.bien_dong_thu_nhap === null
          ? "neutral"
          : data.bien_dong_thu_nhap > thresholds.bien_dong_thu_nhap_cao
          ? "warning"
          : "success",
      formula: "Độ lệch chuẩn dòng tiền vào tháng ÷ Dòng tiền vào bình quân",
      note: "Hệ số biến thiên khi sao kê có đủ dữ liệu theo tháng.",
      source_role: "calculated"
    }
  ];

  // Document extraction mapping
  const fieldDefinitions: {
    key: keyof RawCaseData;
    label: string;
    sourceDoc: string;
    page: number;
    role: SourceRole;
  }[] = [
    { key: "ho_ten_khach_hang", label: "Họ và tên khách hàng", sourceDoc: "don_de_nghi_vay.pdf", page: 1, role: "declared" },
    { key: "thu_nhap_ke_khai", label: "Thu nhập hàng tháng kê khai", sourceDoc: "don_de_nghi_vay.pdf", page: 1, role: "declared" },
    { key: "luong_thuc_nhan", label: "Lương thực nhận", sourceDoc: "chung_tu_thu_nhap.pdf", page: 1, role: "observed" },
    { key: "thu_nhap_qua_sao_ke", label: "Ghi có bình quân hàng tháng", sourceDoc: "sao_ke_ngan_hang_6_thang.pdf", page: 4, role: "observed" },
    { key: "don_vi_cong_tac_ke_khai", label: "Đơn vị công tác trên đơn vay", sourceDoc: "don_de_nghi_vay.pdf", page: 1, role: "declared" },
    { key: "don_vi_cong_tac_chung_tu", label: "Đơn vị công tác trên chứng từ thu nhập", sourceDoc: "chung_tu_thu_nhap.pdf", page: 1, role: "observed" },
    { key: "chuc_danh_ke_khai", label: "Chức danh trên đơn vay", sourceDoc: "don_de_nghi_vay.pdf", page: 1, role: "declared" },
    { key: "chuc_danh_chung_tu", label: "Chức danh trên chứng từ thu nhập", sourceDoc: "chung_tu_thu_nhap.pdf", page: 1, role: "observed" },
    { key: "ngay_bat_dau_ke_khai", label: "Ngày bắt đầu làm việc trên đơn vay", sourceDoc: "don_de_nghi_vay.pdf", page: 1, role: "declared" },
    { key: "ngay_bat_dau_chung_tu", label: "Ngày bắt đầu làm việc trên chứng từ thu nhập", sourceDoc: "chung_tu_thu_nhap.pdf", page: 1, role: "observed" },
    { key: "tham_nien_lam_viec_thang", label: "Thâm niên làm việc", sourceDoc: "chung_tu_thu_nhap.pdf", page: 1, role: "observed" },
    { key: "so_tien_de_nghi_vay", label: "Số tiền đề nghị vay", sourceDoc: "don_de_nghi_vay.pdf", page: 2, role: "declared" },
    { key: "thoi_han_vay_thang", label: "Thời hạn vay", sourceDoc: "don_de_nghi_vay.pdf", page: 2, role: "declared" },
    { key: "khoan_tra_du_kien", label: "Khoản trả nợ dự kiến hàng tháng", sourceDoc: "don_de_nghi_vay.pdf", page: 2, role: "declared" },
    { key: "nghia_vu_no_ke_khai", label: "Khoản trả nợ kê khai hàng tháng", sourceDoc: "don_de_nghi_vay.pdf", page: 2, role: "declared" },
    { key: "nghia_vu_no_quan_sat", label: "Khoản trả nợ quan sát hàng tháng", sourceDoc: "sao_ke_ngan_hang_6_thang.pdf", page: 5, role: "observed" },
    { key: "chi_phi_sinh_hoat", label: "Chi phí sinh hoạt", sourceDoc: "don_de_nghi_vay.pdf", page: 2, role: "declared" },
    { key: "so_du_binh_quan", label: "Số dư tài khoản bình quân", sourceDoc: "sao_ke_ngan_hang_6_thang.pdf", page: 6, role: "observed" },
    { key: "bien_dong_thu_nhap", label: "Mức biến động thu nhập", sourceDoc: "sao_ke_ngan_hang_6_thang.pdf", page: 6, role: "observed" },
    { key: "muc_dich_vay", label: "Mục đích vay", sourceDoc: "don_de_nghi_vay.pdf", page: 2, role: "declared" }
  ];

  const extractedFields: ExtractedFieldItem[] = fieldDefinitions.map((def) => {
    const rawVal = data[def.key];
    let displayVal = "Không tìm thấy";
    if (rawVal !== null && rawVal !== undefined) {
      if (typeof rawVal === "number") {
        if (def.key === "bien_dong_thu_nhap") displayVal = phan_tram(rawVal);
        else if (def.key === "tham_nien_lam_viec_thang" || def.key === "thoi_han_vay_thang")
          displayVal = `${rawVal} tháng`;
        else displayVal = tien(rawVal);
      } else {
        displayVal = String(rawVal);
      }
    }

    const conf =
      rawVal === null || rawVal === undefined
        ? 0.0
        : confidenceOverrides[def.key] ?? 0.96;

    let confTone: StatusTone = "success";
    let confLabel = "Tin cậy cao";
    if (rawVal === null || rawVal === undefined) {
      confTone = "neutral";
      confLabel = "Thiếu dữ liệu";
    } else if (conf < thresholds.do_tin_cay_thap) {
      confTone = "danger";
      confLabel = "Cần xác minh";
    } else if (conf < 0.9) {
      confTone = "warning";
      confLabel = "Cần đối chiếu";
    }

    const evidence: EvidenceReference | null =
      rawVal !== null && rawVal !== undefined
        ? {
            document: def.sourceDoc,
            page: def.page,
            field: def.label,
            value: displayVal,
            excerpt: `${def.label}: ${displayVal}`
          }
        : null;

    return {
      key: def.key,
      label: def.label,
      value_display: displayVal,
      raw_value: rawVal,
      source: rawVal === null ? "Không tìm thấy" : def.sourceDoc,
      source_role: def.role,
      page: rawVal === null ? null : def.page,
      confidence: conf,
      confidence_display: `${Math.round(conf * 100)}%`,
      confidence_label: confLabel,
      confidence_tone: confTone,
      status: rawVal === null ? "Thiếu dữ liệu" : conf < thresholds.do_tin_cay_thap ? "Cần con người kiểm tra" : "Đã trích xuất",
      evidence
    };
  });

  function getEvidence(fieldKey: keyof RawCaseData): EvidenceReference[] {
    const f = extractedFields.find((item) => item.key === fieldKey);
    return f && f.evidence ? [f.evidence] : [];
  }

  // Risk warning detection
  const risks: RiskItem[] = [];

  if (incomeDifference !== null && incomeDifference > thresholds.chenh_lech_thu_nhap) {
    const isSevere = incomeDifference > thresholds.chenh_lech_thu_nhap_nghiem_trong;
    risks.push({
      code: `R-${String(risks.length + 1).padStart(3, "0")}`,
      name: "Thu nhập không nhất quán",
      severity: isSevere ? "HIGH" : "MEDIUM",
      severity_label: isSevere ? "CẢNH BÁO CAO" : "CẢNH BÁO TRUNG BÌNH",
      severity_tone: isSevere ? "danger" : "warning",
      description: `Các nguồn thu nhập chênh ${phan_tram(incomeDifference)}, vượt ngưỡng minh họa ${phan_tram(thresholds.chenh_lech_thu_nhap)}. Cần xác minh nguồn thu và kỳ ghi nhận.`,
      difference: phan_tram(incomeDifference),
      evidence: [
        ...getEvidence("thu_nhap_ke_khai"),
        ...getEvidence("luong_thuc_nhan"),
        ...getEvidence("thu_nhap_qua_sao_ke")
      ]
    });
  }

  if (
    data.don_vi_cong_tac_ke_khai &&
    data.don_vi_cong_tac_chung_tu &&
    chuan_hoa_chuoi(data.don_vi_cong_tac_ke_khai) !== chuan_hoa_chuoi(data.don_vi_cong_tac_chung_tu)
  ) {
    risks.push({
      code: `R-${String(risks.length + 1).padStart(3, "0")}`,
      name: "Đơn vị công tác không khớp",
      severity: "HIGH",
      severity_label: "CẢNH BÁO CAO",
      severity_tone: "danger",
      description: "Tên đơn vị công tác trên đơn vay và chứng từ thu nhập không khớp sau chuẩn hóa.",
      difference: null,
      evidence: [...getEvidence("don_vi_cong_tac_ke_khai"), ...getEvidence("don_vi_cong_tac_chung_tu")]
    });
  }

  let debtInputInvalid = false;
  if (data.nghia_vu_no_ke_khai !== null && data.nghia_vu_no_quan_sat !== null) {
    const declaredDebt = data.nghia_vu_no_ke_khai;
    const observedDebt = data.nghia_vu_no_quan_sat;
    debtInputInvalid = !Number.isFinite(declaredDebt) || !Number.isFinite(observedDebt) || declaredDebt < 0 || observedDebt < 0;
    const debtEv = [...getEvidence("nghia_vu_no_ke_khai"), ...getEvidence("nghia_vu_no_quan_sat")];
    if (!debtInputInvalid && declaredDebt === 0 && observedDebt > 0) {
      risks.push({
        code: `R-${String(risks.length + 1).padStart(3, "0")}`,
        name: "Có thể có khoản nợ chưa kê khai",
        severity: "HIGH",
        severity_label: "CẢNH BÁO CAO",
        severity_tone: "danger",
        description: `Nghĩa vụ nợ kê khai là 0 VND nhưng quan sát thấy ${tien(observedDebt)}. Không tính tỷ lệ vì mẫu số bằng 0.`,
        difference: tien(observedDebt),
        evidence: debtEv
      });
    } else if (!debtInputInvalid && declaredDebt > 0) {
      const debtDiff = Math.abs(observedDebt - declaredDebt) / declaredDebt;
      if (debtDiff > thresholds.chenh_lech_no) {
        risks.push({
          code: `R-${String(risks.length + 1).padStart(3, "0")}`,
          name: "Có thể có khoản nợ chưa kê khai",
          severity: observedDebt > declaredDebt ? "HIGH" : "MEDIUM",
          severity_label: observedDebt > declaredDebt ? "CẢNH BÁO CAO" : "CẢNH BÁO TRUNG BÌNH",
          severity_tone: observedDebt > declaredDebt ? "danger" : "warning",
          description: `Khoản trả nợ quan sát khác ${phan_tram(debtDiff)} so với kê khai, vượt ngưỡng minh họa ${phan_tram(thresholds.chenh_lech_no)}.`,
          difference: phan_tram(debtDiff),
          evidence: debtEv
        });
      }
    }
  }

  if (
    data.chuc_danh_ke_khai &&
    data.chuc_danh_chung_tu &&
    chuan_hoa_chuoi(data.chuc_danh_ke_khai) !== chuan_hoa_chuoi(data.chuc_danh_chung_tu)
  ) {
    risks.push({
      code: `R-${String(risks.length + 1).padStart(3, "0")}`,
      name: "Chức danh không khớp",
      severity: "MEDIUM",
      severity_label: "CẢNH BÁO TRUNG BÌNH",
      severity_tone: "warning",
      description: "Chức danh công việc khác nhau giữa đơn vay và chứng từ thu nhập.",
      difference: null,
      evidence: [...getEvidence("chuc_danh_ke_khai"), ...getEvidence("chuc_danh_chung_tu")]
    });
  }

  let employmentDateUnparseable = false;
  if (data.ngay_bat_dau_ke_khai && data.ngay_bat_dau_chung_tu) {
    const d1 = chuan_hoa_ngay(data.ngay_bat_dau_ke_khai);
    const d2 = chuan_hoa_ngay(data.ngay_bat_dau_chung_tu);
    employmentDateUnparseable = d1 === null || d2 === null;
    if (!employmentDateUnparseable && d1 !== d2) {
      risks.push({
        code: `R-${String(risks.length + 1).padStart(3, "0")}`,
        name: "Thời điểm làm việc không khớp",
        severity: "MEDIUM",
        severity_label: "CẢNH BÁO TRUNG BÌNH",
        severity_tone: "warning",
        description: "Ngày bắt đầu làm việc không nhất quán giữa các chứng từ sau khi chuẩn hóa định dạng.",
        difference: null,
        evidence: [...getEvidence("ngay_bat_dau_ke_khai"), ...getEvidence("ngay_bat_dau_chung_tu")]
      });
    }
  }

  if (dti !== null && dti > thresholds.dti_canh_bao) {
    risks.push({
      code: `R-${String(risks.length + 1).padStart(3, "0")}`,
      name: "DTI cao theo ngưỡng minh họa",
      severity: "HIGH",
      severity_label: "CẢNH BÁO CAO",
      severity_tone: "danger",
      description: `DTI ${phan_tram(dti)} vượt ngưỡng cảnh báo minh họa ${phan_tram(thresholds.dti_canh_bao)}. Đây không phải chính sách cấp tín dụng của ngân hàng.`,
      difference: phan_tram(dti),
      evidence: [...getEvidence("nghia_vu_no_quan_sat"), ...getEvidence("luong_thuc_nhan")]
    });
  }

  if (dsr !== null && dsr > thresholds.dsr_canh_bao) {
    risks.push({
      code: `R-${String(risks.length + 1).padStart(3, "0")}`,
      name: "DSR cao theo ngưỡng minh họa",
      severity: "HIGH",
      severity_label: "CẢNH BÁO CAO",
      severity_tone: "danger",
      description: `DSR dự kiến ${phan_tram(dsr)} vượt ngưỡng cảnh báo minh họa ${phan_tram(thresholds.dsr_canh_bao)}.`,
      difference: phan_tram(dsr),
      evidence: [
        ...getEvidence("nghia_vu_no_quan_sat"),
        ...getEvidence("khoan_tra_du_kien"),
        ...getEvidence("thu_nhap_qua_sao_ke")
      ]
    });
  }

  if (balanceBuffer !== null && balanceBuffer < thresholds.he_so_dem_so_du_thap) {
    risks.push({
      code: `R-${String(risks.length + 1).padStart(3, "0")}`,
      name: "Hệ số đệm số dư thấp",
      severity: "MEDIUM",
      severity_label: "CẢNH BÁO TRUNG BÌNH",
      severity_tone: "warning",
      description: `Hệ số đệm số dư ${so_thap_phan(balanceBuffer)}× thấp hơn ngưỡng minh họa ${so_thap_phan(thresholds.he_so_dem_so_du_thap)}×.`,
      difference: `${so_thap_phan(balanceBuffer)}×`,
      evidence: [...getEvidence("so_du_binh_quan"), ...getEvidence("khoan_tra_du_kien")]
    });
  }

  if (data.bien_dong_thu_nhap !== null && data.bien_dong_thu_nhap > thresholds.bien_dong_thu_nhap_cao) {
    risks.push({
      code: `R-${String(risks.length + 1).padStart(3, "0")}`,
      name: "Thu nhập biến động cao",
      severity: "MEDIUM",
      severity_label: "CẢNH BÁO TRUNG BÌNH",
      severity_tone: "warning",
      description: `Biến động dòng tiền vào ${phan_tram(data.bien_dong_thu_nhap)} vượt ngưỡng minh họa ${phan_tram(thresholds.bien_dong_thu_nhap_cao)}.`,
      difference: phan_tram(data.bien_dong_thu_nhap),
      evidence: getEvidence("bien_dong_thu_nhap")
    });
  }

  const lowConfidence = extractedFields.filter((f) => f.raw_value !== null && f.confidence < thresholds.do_tin_cay_thap);
  if (lowConfidence.length > 0) {
    risks.push({
      code: `R-${String(risks.length + 1).padStart(3, "0")}`,
      name: "Độ tin cậy trích xuất thấp",
      severity: "MEDIUM",
      severity_label: "CẢNH BÁO TRUNG BÌNH",
      severity_tone: "warning",
      description: `${lowConfidence.length} trường có độ tin cậy dưới ${phan_tram(thresholds.do_tin_cay_thap)} và cần con người kiểm tra.`,
      difference: `${lowConfidence.length} trường`,
      evidence: lowConfidence.map((f) => f.evidence!).filter(Boolean)
    });
  }

  // Missing items
  const missing: string[] = [];
  const docLabels: Record<string, string> = {
    application: "Đơn đề nghị vay vốn",
    income: "Chứng từ thu nhập",
    statement: "Sao kê ngân hàng"
  };
  for (const [key, label] of Object.entries(docLabels)) {
    const d = documents.find((doc) => doc.expectedType === key);
    if (!d || d.status === "Không đọc được") {
      missing.push(label);
    }
  }
  if (!data.ho_ten_khach_hang) missing.push("Họ và tên khách hàng");
  if (data.so_tien_de_nghi_vay === null) missing.push("Số tiền đề nghị vay");
  if (incomeForCalc === null) missing.push("Thu nhập dùng để tính");
  if (data.thoi_han_vay_thang === null) missing.push("Thời hạn vay");

  // Verification questions
  const questions: string[] = [];
  const riskTypes = new Set(risks.map((r) => r.name));
  if (riskTypes.has("Thu nhập không nhất quán")) {
    questions.push("Nguồn thu nhập nào là thường xuyên, có thể xác minh và thuộc đúng kỳ sao kê?");
  }
  if (riskTypes.has("Đơn vị công tác không khớp")) {
    questions.push("Khách hàng có thay đổi đơn vị công tác hay chứng từ nào đã lỗi thời?");
  }
  if (riskTypes.has("Có thể có khoản nợ chưa kê khai")) {
    questions.push("Các khoản ghi nợ định kỳ nào là nghĩa vụ tín dụng hiện hữu của khách hàng?");
  }
  if (!incomeVerified && incomeForCalc !== null) {
    questions.push("Thu nhập dùng để tính hiện chỉ dựa trên kê khai; vui lòng bổ sung chứng từ hoặc sao kê để xác minh độc lập.");
  }
  if (employmentDateUnparseable) {
    questions.push("Một hoặc cả hai ngày bắt đầu làm việc không ở định dạng được hỗ trợ; vui lòng chuẩn hóa và đối chiếu lại.");
  }
  if (debtInputInvalid) {
    questions.push("Nghĩa vụ nợ có giá trị âm hoặc không hợp lệ; vui lòng xác nhận dữ liệu trước khi tính chênh lệch.");
  }
  if (data.khoan_tra_du_kien === null) {
    questions.push("Khoản trả nợ dự kiến hàng tháng theo phương án vay là bao nhiêu?");
  }
  if (missing.length > 0) {
    questions.push(`Vui lòng bổ sung hoặc xác nhận: ${missing.join(", ")}.`);
  }
  if (questions.length === 0) {
    questions.push("Cán bộ tín dụng vui lòng xác nhận lại dữ kiện và bằng chứng trước khi đưa ra quyết định cuối cùng.");
  }

  // Final review status
  const criticalMissing = ["Đơn đề nghị vay vốn", "Chứng từ thu nhập", "Sao kê ngân hàng", "Số tiền đề nghị vay", "Thu nhập dùng để tính"];
  let finalStatus: UnderwritingResult["trang_thai"] = "REVIEW READY";
  if (missing.some((m) => criticalMissing.includes(m))) {
    finalStatus = "INSUFFICIENT INFORMATION";
  } else if (risks.length > 0 || !incomeVerified || employmentDateUnparseable || debtInputInvalid) {
    finalStatus = "HUMAN REVIEW REQUIRED";
  }

  const durationMs = Math.max(1, Math.round(performance.now() - startTime));

  return {
    ma_ho_so: caseId,
    ten_ho_so: caseTitle,
    du_lieu: data,
    documents,
    fields: extractedFields,
    chi_so: chiSo,
    canh_bao: risks,
    thong_tin_thieu: missing,
    cau_hoi_xac_minh: questions,
    trang_thai: finalStatus,
    thu_nhap_dung_de_tinh: incomeForCalc,
    nguon_thu_nhap_dung_de_tinh: incomeSource,
    thu_nhap_duoc_xac_minh_doc_lap: incomeVerified,
    thoi_diem_xu_ly: new Date().toISOString(),
    thoi_gian_xu_ly_ms: durationMs
  };
}

export function buildCorePageViewModel(
  page: "extraction" | "analysis" | "risk",
  result: UnderwritingResult | null,
  thresholds: UnderwritingThresholds = DEFAULT_THRESHOLDS,
  theme: ThemeMode = "system"
): V2CorePageViewModel {
  if (!result) {
    return {
      theme,
      page,
      title: page === "extraction" ? "Trích xuất tài liệu" : page === "analysis" ? "Phân tích tín dụng" : "Cảnh báo rủi ro",
      subtitle: "Chưa có hồ sơ đang mở. Hãy mở hồ sơ minh họa từ Tổng quan.",
      state: "empty",
      state_message: "Chưa có dữ liệu để hiển thị.",
      documents: [],
      fields: [],
      comparisons: [],
      metrics: [],
      thresholds: [],
      risks: [],
      case_status: null
    };
  }

  const documents: DocumentItem[] = result.documents.map((d) => {
    const mismatch = d.detectedType !== "unknown" && d.detectedType !== d.expectedType;
    let tone: StatusTone = "success";
    let label = "Tin cậy cao";
    if (d.status === "Không đọc được") {
      tone = "danger";
      label = "Không đọc được";
    } else if (mismatch) {
      tone = "warning";
      label = "Sai lệch loại";
    } else if (d.confidence < thresholds.do_tin_cay_thap) {
      tone = "warning";
      label = "Cần đối chiếu";
    }

    return {
      name: d.name,
      expected_type: d.expectedType,
      detected_type: d.detectedType,
      pages: d.pages,
      status: d.status,
      confidence: d.confidence,
      confidence_display: `${Math.round(d.confidence * 100)}%`,
      confidence_label: label,
      confidence_tone: tone,
      type_mismatch: mismatch
    };
  });

  const comparisons: CrossDocumentComparison[] = [];
  const d = result.du_lieu;

  // Comparison 1: Income
  const incomeVals = [
    { role: "declared" as const, label: "Đơn vay", value_display: tien(d.thu_nhap_ke_khai), source: "don_de_nghi_vay.pdf" },
    { role: "observed" as const, label: "Chứng từ thu nhập", value_display: tien(d.luong_thuc_nhan), source: "chung_tu_thu_nhap.pdf" },
    { role: "observed" as const, label: "Sao kê ngân hàng", value_display: tien(d.thu_nhap_qua_sao_ke), source: "sao_ke_ngan_hang_6_thang.pdf" }
  ];
  const diffIncome = result.chi_so.find((m) => m.key === "income_difference");
  comparisons.push({
    title: "Đối chiếu thu nhập qua 3 nguồn",
    values: incomeVals,
    difference_display: diffIncome?.value_display ?? "—",
    status: diffIncome?.status ?? "Đầy đủ",
    status_tone: diffIncome?.status_tone ?? "success"
  });

  // Comparison 2: Employer
  comparisons.push({
    title: "Đối chiếu đơn vị công tác",
    values: [
      { role: "declared" as const, label: "Đơn vay", value_display: d.don_vi_cong_tac_ke_khai ?? "—", source: "don_de_nghi_vay.pdf" },
      { role: "observed" as const, label: "Chứng từ", value_display: d.don_vi_cong_tac_chung_tu ?? "—", source: "chung_tu_thu_nhap.pdf" }
    ],
    difference_display:
      d.don_vi_cong_tac_ke_khai && d.don_vi_cong_tac_chung_tu && chuan_hoa_chuoi(d.don_vi_cong_tac_ke_khai) !== chuan_hoa_chuoi(d.don_vi_cong_tac_chung_tu)
        ? "Không khớp"
        : "Khớp",
    status:
      d.don_vi_cong_tac_ke_khai && d.don_vi_cong_tac_chung_tu && chuan_hoa_chuoi(d.don_vi_cong_tac_ke_khai) !== chuan_hoa_chuoi(d.don_vi_cong_tac_chung_tu)
        ? "Cần xem xét"
        : "Nhất quán",
    status_tone:
      d.don_vi_cong_tac_ke_khai && d.don_vi_cong_tac_chung_tu && chuan_hoa_chuoi(d.don_vi_cong_tac_ke_khai) !== chuan_hoa_chuoi(d.don_vi_cong_tac_chung_tu)
        ? "danger"
        : "success"
  });

  // Comparison 3: Monthly Debt
  const debtDiffPercent =
    d.nghia_vu_no_ke_khai !== null && d.nghia_vu_no_quan_sat !== null && d.nghia_vu_no_ke_khai > 0
      ? Math.abs(d.nghia_vu_no_quan_sat - d.nghia_vu_no_ke_khai) / d.nghia_vu_no_ke_khai
      : null;
  comparisons.push({
    title: "Đối chiếu nghĩa vụ nợ hàng tháng",
    values: [
      { role: "declared" as const, label: "Kê khai", value_display: tien(d.nghia_vu_no_ke_khai), source: "don_de_nghi_vay.pdf" },
      { role: "observed" as const, label: "Quan sát sao kê", value_display: tien(d.nghia_vu_no_quan_sat), source: "sao_ke_ngan_hang_6_thang.pdf" }
    ],
    difference_display: debtDiffPercent !== null ? phan_tram(debtDiffPercent) : "—",
    status: debtDiffPercent !== null && debtDiffPercent > thresholds.chenh_lech_no ? "Cần chú ý" : "Phù hợp",
    status_tone: debtDiffPercent !== null && debtDiffPercent > thresholds.chenh_lech_no ? "warning" : "success"
  });

  const thresholdRefs: ThresholdReference[] = [
    { key: "dti", label: "Cảnh báo DTI", value: thresholds.dti_canh_bao, value_display: phan_tram(thresholds.dti_canh_bao), relation: "above" },
    { key: "dsr", label: "Cảnh báo DSR", value: thresholds.dsr_canh_bao, value_display: phan_tram(thresholds.dsr_canh_bao), relation: "above" },
    { key: "buffer", label: "Đệm số dư tối thiểu", value: thresholds.he_so_dem_so_du_thap, value_display: `${so_thap_phan(thresholds.he_so_dem_so_du_thap)}×`, relation: "below" },
    { key: "income_diff", label: "Chênh lệch thu nhập", value: thresholds.chenh_lech_thu_nhap, value_display: phan_tram(thresholds.chenh_lech_thu_nhap), relation: "above" },
    { key: "volatility", label: "Biến động thu nhập cao", value: thresholds.bien_dong_thu_nhap_cao, value_display: phan_tram(thresholds.bien_dong_thu_nhap_cao), relation: "above" }
  ];

  const pageTitles: Record<string, { title: string; subtitle: string }> = {
    extraction: {
      title: "Trích xuất và kiểm chứng thực tế",
      subtitle: "Dữ kiện được trích xuất từ 3-4 tài liệu PDF gốc kèm trích đoạn bằng chứng và mức tin cậy."
    },
    analysis: {
      title: "Phân tích chỉ số tín dụng",
      subtitle: "Công thức xác định tính toán DTI, DSR, thu nhập còn lại và hệ số đệm thanh khoản."
    },
    risk: {
      title: "Cảnh báo rủi ro và bằng chứng",
      subtitle: "Quy tắc kiểm tra chéo đa tài liệu phát hiện mâu thuẫn và gán nhãn mức độ ưu tiên xem xét."
    }
  };

  const isPartial = result.trang_thai === "INSUFFICIENT INFORMATION" || result.thong_tin_thieu.length > 0;

  return {
    theme,
    page,
    title: pageTitles[page]?.title ?? "Thẩm định tín dụng",
    subtitle: pageTitles[page]?.subtitle ?? "",
    state: isPartial ? "partial" : "success",
    state_message: isPartial
      ? "Thông tin chưa đủ; chuyên viên cần bổ sung tài liệu trước khi phê duyệt."
      : "Dữ liệu xác định đã sẵn sàng để chuyên viên xem xét.",
    documents,
    fields: result.fields,
    comparisons,
    metrics: result.chi_so,
    thresholds: thresholdRefs,
    risks: result.canh_bao,
    case_status: NHAN_TRANG_THAI[result.trang_thai] ?? result.trang_thai
  };
}

export function buildSummaryPageViewModel(
  result: UnderwritingResult | null,
  aiExplanation: string | null = null,
  theme: ThemeMode = "system"
): V2SummaryPageViewModel {
  if (!result) {
    return {
      theme,
      state: "empty",
      state_message: "Chưa có hồ sơ để tạo tóm tắt. Hãy tải PDF hoặc mở hồ sơ minh họa.",
      case_id: null,
      applicant: "Chưa có dữ liệu",
      employer: "Chưa có dữ liệu",
      loan_amount: "—",
      loan_term: "—",
      loan_purpose: "Chưa có dữ liệu",
      review_status: "CHƯA CÓ HỒ SƠ",
      review_status_tone: "neutral",
      highest_alert: "Chưa có cảnh báo",
      highest_alert_tone: "neutral",
      metrics: [],
      top_risks: [],
      total_risk_count: 0,
      findings: [],
      evidence: [],
      document_count: 0,
      extracted_field_count: 0,
      ai_explanation: null
    };
  }

  const d = result.du_lieu;
  const isPartial = result.trang_thai === "INSUFFICIENT INFORMATION" || result.thong_tin_thieu.length > 0;

  const highestRisk = result.canh_bao.find((r) => r.severity === "HIGH")
    ? { text: "HIGH · CAO", tone: "danger" as const }
    : result.canh_bao.find((r) => r.severity === "MEDIUM")
    ? { text: "MEDIUM · TRUNG BÌNH", tone: "warning" as const }
    : result.canh_bao.length > 0
    ? { text: "LOW · THẤP", tone: "info" as const }
    : { text: "Không có cảnh báo", tone: "neutral" as const };

  const reviewStatusTone: StatusTone =
    result.trang_thai === "REVIEW READY"
      ? "success"
      : result.trang_thai === "HUMAN REVIEW REQUIRED"
      ? "warning"
      : "neutral";

  const findings: FindingItem[] = [
    {
      category: "finding",
      title: "Thu nhập dùng để tính",
      detail: `${tien(result.thu_nhap_dung_de_tinh)} · ${result.nguon_thu_nhap_dung_de_tinh}`,
      tone: "info"
    },
    {
      category: "finding",
      title: "Trạng thái nguồn thu nhập",
      detail: result.thu_nhap_duoc_xac_minh_doc_lap
        ? "Đã có nguồn đối chiếu độc lập (lương hoặc sao kê)"
        : "Chỉ kê khai hoặc chưa đủ dữ liệu",
      tone: result.thu_nhap_duoc_xac_minh_doc_lap ? "success" : "warning"
    }
  ];

  for (const item of result.thong_tin_thieu) {
    findings.push({
      category: "missing",
      title: "Thông tin còn thiếu",
      detail: item,
      tone: "warning"
    });
  }

  for (const item of result.cau_hoi_xac_minh) {
    findings.push({
      category: "verification",
      title: "Cần chuyên viên xác minh",
      detail: item,
      tone: "warning"
    });
  }

  if (result.thong_tin_thieu.length === 0) {
    findings.push({
      category: "finding",
      title: "Hạng mục bắt buộc",
      detail: "Không phát hiện hạng mục bắt buộc còn thiếu.",
      tone: "success"
    });
  }

  const allEvidence = result.canh_bao.flatMap((r) => r.evidence);

  return {
    theme,
    state: isPartial ? "partial" : "success",
    state_message: isPartial
      ? "Thông tin chưa đủ; chuyên viên cần bổ sung và xác minh trước khi xem xét."
      : "Kết quả xác định đã sẵn sàng để chuyên viên xem xét.",
    case_id: result.ma_ho_so,
    applicant: d.ho_ten_khach_hang ?? "Thông tin chưa đủ",
    employer: d.don_vi_cong_tac_ke_khai ?? "Thông tin chưa đủ",
    loan_amount: tien(d.so_tien_de_nghi_vay),
    loan_term: d.thoi_han_vay_thang !== null ? `${d.thoi_han_vay_thang} tháng` : "Thông tin chưa đủ",
    loan_purpose: d.muc_dich_vay ?? "Thông tin chưa đủ",
    review_status: NHAN_TRANG_THAI[result.trang_thai] ?? result.trang_thai,
    review_status_tone: reviewStatusTone,
    highest_alert: highestRisk.text,
    highest_alert_tone: highestRisk.tone,
    metrics: result.chi_so,
    top_risks: result.canh_bao.slice(0, 3),
    total_risk_count: result.canh_bao.length,
    findings,
    evidence: allEvidence,
    document_count: result.documents.length,
    extracted_field_count: result.fields.length,
    ai_explanation: aiExplanation
  };
}

export function buildMethodologyViewModel(theme: ThemeMode = "system"): V2MethodologyPageViewModel {
  return {
    theme,
    layers: [
      {
        key: "facts",
        label: "1. DỮ KIỆN",
        description:
          "Kiểm tra PDF, đọc lớp văn bản theo trang, phân loại tài liệu, tìm nhãn/bí danh và chuẩn hóa bằng schema. Không suy diễn dữ liệu không tìm thấy."
      },
      {
        key: "deterministic",
        label: "2. PHÂN TÍCH XÁC ĐỊNH",
        description:
          "Thuật toán tính DTI, DSR, thu nhập còn lại, hệ số đệm số dư, chênh lệch và biến động thu nhập. Mẫu số bằng 0 hoặc thiếu dữ liệu trả về Chưa đủ dữ liệu."
      },
      {
        key: "ai",
        label: "3. DIỄN GIẢI AI",
        description:
          "LLM chỉ nhận facts, calculations, rules và evidence khi người dùng yêu cầu. Nếu API lỗi, báo cáo xác định vẫn hoạt động 100% độc lập."
      }
    ],
    formulas: [
      {
        key: "dti",
        name: "DTI hiện hữu",
        formula: "Nghĩa vụ nợ hiện hữu ÷ Thu nhập dùng để tính",
        meaning: "Tỷ trọng nghĩa vụ nợ hiện hữu trên nguồn thu nhập được chọn bởi pipeline.",
        limitation: "Nợ quan sát được ưu tiên hơn nợ kê khai; dữ liệu thiếu trả về Chưa đủ dữ liệu."
      },
      {
        key: "dsr",
        name: "DSR dự kiến",
        formula: "(Nợ hiện hữu + Khoản trả dự kiến) ÷ Thu nhập dùng để tính",
        meaning: "Minh họa sức chịu khoản trả hiện hữu và khoản trả dự kiến của khoản vay mới.",
        limitation: "Khoản trả dự kiến là đầu vào; hệ thống không đặt lãi suất hoặc chính sách tín dụng."
      },
      {
        key: "disposable_income",
        name: "Thu nhập còn lại trước khoản vay mới",
        formula: "Thu nhập dùng để tính − Nợ hiện hữu − Chi phí sinh hoạt",
        meaning: "Phần thu nhập còn lại trước khi trừ khoản trả dự kiến của khoản vay mới.",
        limitation: "Không bao gồm khoản trả dự kiến của khoản vay mới."
      },
      {
        key: "income_consistency",
        name: "Chênh lệch thu nhập",
        formula: "(Nguồn cao nhất − Nguồn thấp nhất) ÷ Nguồn cao nhất",
        meaning: "So sánh thu nhập kê khai, chứng từ và sao kê hiện có.",
        limitation: "Chỉ phản ánh các nguồn đã trích xuất; không suy diễn nguồn còn thiếu."
      },
      {
        key: "balance_buffer",
        name: "Hệ số đệm số dư",
        formula: "Số dư bình quân ÷ Khoản trả dự kiến",
        meaning: "Đo lường năng lực bù đắp thanh khoản ngắn hạn trong trường hợp gián đoạn dòng tiền.",
        limitation: "Số dư biến thiên theo tháng; cần đối chiếu lịch sử giao dịch chi tiết."
      },
      {
        key: "income_volatility",
        name: "Biến động thu nhập",
        formula: "Độ lệch chuẩn dòng tiền vào tháng ÷ Dòng tiền vào bình quân",
        meaning: "Đánh giá mức độ ổn định dòng tiền của người đi vay qua thời gian.",
        limitation: "Đòi hỏi tối thiểu 3-6 tháng sao kê liên tục để có ý nghĩa thống kê."
      }
    ],
    capabilities: [
      {
        document_type: "PDF số / Có lớp văn bản",
        support_level: "Hỗ trợ đầy đủ",
        limitation: "Tốt nhất khi nhãn và giá trị có thứ tự đọc chuẩn và rõ ràng."
      },
      {
        document_type: "PDF có bảng biểu",
        support_level: "Hỗ trợ một phần",
        limitation: "Bảng nhiều cột và ô gộp phức tạp có thể mất liên kết hàng."
      },
      {
        document_type: "PDF quét ảnh (Scanned)",
        support_level: "Cần OCR",
        limitation: "Cần tích hợp module OCR và bắt buộc con người xác minh."
      },
      {
        document_type: "PDF hỗn hợp văn bản & ảnh",
        support_level: "Hỗ trợ một phần",
        limitation: "Dữ kiện chỉ nằm trong ảnh con có thể bị bỏ sót."
      },
      {
        document_type: "PDF có mật khẩu / Mã hóa",
        support_level: "Không hỗ trợ",
        limitation: "Phải gỡ mật khẩu trước khi tải lên hệ thống."
      }
    ],
    limitations: [
      {
        title: "Giới hạn phạm vi hệ thống",
        items: [
          "CreditLens là công cụ hỗ trợ thẩm định, không phải hệ thống phê duyệt tự động.",
          "Hệ thống không tích hợp thông tin điểm tín dụng CIC hoặc danh sách đen tín dụng.",
          "Các ngưỡng cảnh báo chỉ mang tính minh họa, không thay thế quy định quản trị rủi ro ngân hàng."
        ]
      },
      {
        title: "Trách nhiệm của chuyên viên",
        items: [
          "Bắt buộc kiểm tra trích đoạn bằng chứng đối với các trường có điểm confidence thấp.",
          "Chịu trách nhiệm trực tiếp về quyết định cấp hoặc từ chối hạn mức tín dụng.",
          "Xác minh nguồn gốc hợp pháp của chứng từ thu nhập khi có chênh lệch lớn."
        ]
      }
    ],
    self_test_definition:
      "Tự kiểm tra các hàm toán học, logic rẽ nhánh và không chia cho 0 bên trong codebase.",
    evaluation_definition:
      "Đánh giá độc lập trên tập 12 gold cases với nhãn đối chiếu và các chỉ số đo lường Precision / Recall / F1."
  };
}

