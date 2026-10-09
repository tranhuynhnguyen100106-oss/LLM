import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { CoreBusinessPage } from "../src/CoreBusinessPage";
import { parseCorePageViewModel, type V2CorePageViewModel } from "../src/contracts";

const BASE: V2CorePageViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "core_business_page",
  theme: "light",
  page: "extraction",
  title: "Trích xuất tài liệu",
  subtitle: "Dữ liệu do Python cung cấp.",
  state: "success",
  state_message: "Dữ liệu đã sẵn sàng để chuyên viên xem xét.",
  documents: [],
  fields: [],
  comparisons: [],
  metrics: [],
  thresholds: [],
  risks: [],
  case_status: "CẦN CON NGƯỜI XEM XÉT"
};

const EXTRACTION: V2CorePageViewModel = {
  ...BASE,
  documents: [
    {
      name: "chung_tu_thu_nhap.pdf",
      expected_type: "Chứng từ thu nhập",
      detected_type: "Chứng từ thu nhập",
      pages: 2,
      status: "Đã trích xuất",
      confidence: 0.99,
      confidence_display: "99,0%",
      confidence_label: "Tin cậy cao",
      confidence_tone: "success",
      type_mismatch: false
    }
  ],
  fields: [
    {
      key: "luong_thuc_nhan",
      label: "Lương thực nhận",
      value_display: "18.000.000 ₫",
      raw_value: 18000000,
      source: "chung_tu_thu_nhap.pdf",
      source_role: "observed",
      page: 1,
      confidence: 0.58,
      confidence_display: "58,0%",
      confidence_label: "Cần xác minh",
      confidence_tone: "danger",
      status: "Cần xác minh",
      evidence: {
        document: "chung_tu_thu_nhap.pdf",
        page: 1,
        field: "Lương thực nhận",
        value: "18.000.000 ₫",
        excerpt: "Lương thực nhận: 18.000.000 ₫"
      }
    },
    {
      key: "thu_nhap_ke_khai",
      label: "Thu nhập kê khai",
      value_display: "25.000.000 ₫",
      raw_value: 25000000,
      source: "don_de_nghi_vay.pdf",
      source_role: "declared",
      page: 1,
      confidence: 0.96,
      confidence_display: "96,0%",
      confidence_label: "Tin cậy cao",
      confidence_tone: "success",
      status: "Tin cậy cao",
      evidence: null
    }
  ]
};

const ANALYSIS: V2CorePageViewModel = {
  ...BASE,
  page: "analysis",
  title: "Phân tích tín dụng bằng Python",
  comparisons: [
    {
      title: "Đối chiếu thu nhập giữa các nguồn",
      values: [
        { role: "declared", label: "Thu nhập kê khai", value_display: "25.000.000 ₫", source: "Đơn đề nghị vay vốn" },
        { role: "observed", label: "Thu nhập sao kê", value_display: "14.000.000 ₫", source: "Sao kê ngân hàng" },
        { role: "calculated", label: "Thu nhập dùng để tính", value_display: "14.000.000 ₫", source: "Sao kê ngân hàng" }
      ],
      difference_display: "44,0%",
      status: "Cần chú ý",
      status_tone: "warning"
    }
  ],
  metrics: ["dti", "dsr", "thu_nhap_kha_dung", "he_so_dem_so_du", "chenh_lech_thu_nhap", "bien_dong_thu_nhap"].map(
    (key, index) => ({
      key,
      label: ["DTI hiện hữu", "DSR dự kiến", "Thu nhập còn lại", "Hệ số đệm số dư", "Chênh lệch thu nhập", "Biến động thu nhập"][index] as string,
      value_display: index < 2 ? "37,5%" : "1,2×",
      raw_value: 0.375,
      reference: "Cần chú ý khi > 40,0%",
      status: "Trong ngưỡng minh họa",
      status_tone: "success" as const,
      formula: "Giá trị do Python tính",
      note: "Không tính lại trong React.",
      source_role: "calculated" as const
    })
  ),
  thresholds: [
    { key: "dti_canh_bao", label: "DTI", value: 0.4, value_display: "40,0%", relation: "above" }
  ]
};

const RISK: V2CorePageViewModel = {
  ...BASE,
  page: "risk",
  title: "Cảnh báo rủi ro và bằng chứng",
  risks: [
    {
      code: "R-001",
      name: "Thu nhập không nhất quán",
      severity: "HIGH",
      severity_label: "CAO",
      severity_tone: "danger",
      description: "Các nguồn thu nhập chênh lệch.",
      difference: "44,0%",
      evidence: [
        { document: "don_de_nghi_vay.pdf", page: 1, field: "Thu nhập kê khai", value: "25.000.000 ₫", excerpt: null }
      ]
    },
    {
      code: "R-002",
      name: "Biến động thu nhập cao",
      severity: "MEDIUM",
      severity_label: "TRUNG BÌNH",
      severity_tone: "warning",
      description: "Biến động vượt ngưỡng hiện hành.",
      difference: "34,0%",
      evidence: []
    }
  ]
};

afterEach(cleanup);

describe("Cluster 4 core business pages", () => {
  it("renders extracted value, source, page, confidence and evidence without recomputing", () => {
    render(<CoreBusinessPage viewModel={EXTRACTION} />);
    expect(screen.getByRole("heading", { name: "Trích xuất tài liệu", level: 1 })).toBeTruthy();
    expect(screen.getAllByText("18.000.000 ₫").length).toBeGreaterThan(0);
    expect(screen.getByText(/58,0% · Cần xác minh/)).toBeTruthy();
    expect(screen.getAllByText("Quan sát từ chứng từ").length).toBeGreaterThan(0);
    expect(screen.getAllByText("Trang 1").length).toBeGreaterThan(0);
    fireEvent.click(screen.getByText("Xem bằng chứng nguồn"));
    expect(screen.getByText("Lương thực nhận: 18.000.000 ₫")).toBeTruthy();
  });

  it("keeps local extraction filters in React and presents explicit source roles", () => {
    render(<CoreBusinessPage viewModel={EXTRACTION} />);
    fireEvent.change(screen.getByLabelText("Nguồn dữ liệu"), { target: { value: "declared" } });
    expect(screen.getByText("25.000.000 ₫")).toBeTruthy();
    expect(screen.queryByText("18.000.000 ₫")).toBeNull();
    expect(screen.getByText("1/2 trường")).toBeTruthy();
  });

  it("renders six backend metrics, comparison values and unchanged threshold references", () => {
    render(<CoreBusinessPage viewModel={ANALYSIS} />);
    expect(screen.getAllByText("Python tính toán").length).toBeGreaterThanOrEqual(6);
    expect(screen.getByRole("heading", { name: "DTI hiện hữu" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "DSR dự kiến" })).toBeTruthy();
    expect(screen.getByText("Chênh lệch từ Python")).toBeTruthy();
    expect(screen.getByText("> 40,0%")).toBeTruthy();
  });

  it("groups risks by the existing severity and exposes text labels plus evidence counts", () => {
    render(<CoreBusinessPage viewModel={RISK} />);
    expect(screen.getByText("Mức độ CAO")).toBeTruthy();
    expect(screen.getByText("Mức độ TRUNG BÌNH")).toBeTruthy();
    expect(screen.getByText("HIGH · CAO")).toBeTruthy();
    expect(screen.getByText("Bằng chứng (1)")).toBeTruthy();
    expect(screen.getByText("Bằng chứng (0)")).toBeTruthy();
  });

  it("renders semantic empty, loading, partial and error states", () => {
    const { rerender } = render(<CoreBusinessPage viewModel={{ ...BASE, state: "empty" }} />);
    expect(screen.getByRole("status").textContent).toContain("Chưa có dữ liệu");
    rerender(<CoreBusinessPage viewModel={{ ...BASE, state: "loading" }} />);
    expect(screen.getByRole("status").textContent).toContain("Đang xử lý");
    rerender(<CoreBusinessPage viewModel={{ ...BASE, state: "partial" }} />);
    expect(screen.getByRole("status").textContent).toContain("Dữ liệu chưa đầy đủ");
    rerender(<CoreBusinessPage viewModel={{ ...BASE, state: "error" }} />);
    expect(screen.getByRole("alert").textContent).toContain("Không thể hiển thị");
  });

  it("strictly parses the presentation contract and rejects secret-shaped fields", () => {
    expect(parseCorePageViewModel(EXTRACTION)).toEqual(EXTRACTION);
    expect(() => parseCorePageViewModel({ ...EXTRACTION, authorization: "never-send" })).toThrow(/prohibited/i);
  });
});
