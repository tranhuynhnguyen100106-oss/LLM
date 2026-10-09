import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { EvaluationPage, MethodologyPage, SummaryPage } from "../src/Cluster5Pages";
import {
  parseEvaluationPageViewModel,
  parseMethodologyPageViewModel,
  parseSummaryPageViewModel,
  type V2EvaluationPageViewModel,
  type V2MethodologyPageViewModel,
  type V2SummaryPageViewModel
} from "../src/contracts";

const SUMMARY: V2SummaryPageViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "summary_page",
  theme: "light",
  state: "success",
  state_message: "Kết quả xác định đã sẵn sàng để chuyên viên xem xét.",
  case_id: "CASE-03",
  applicant: "Nguyễn Minh Anh",
  employer: "Công ty Ánh Dương",
  loan_amount: "500.000.000 ₫",
  loan_term: "60 tháng",
  loan_purpose: "Mua nhà",
  review_status: "CẦN CON NGƯỜI XEM XÉT",
  review_status_tone: "warning",
  highest_alert: "HIGH · CAO",
  highest_alert_tone: "danger",
  metrics: [{
    key: "dti", label: "DTI hiện hữu", value_display: "37,5%", raw_value: 0.375,
    reference: "Cần chú ý khi > 40,0%", status: "Trong ngưỡng minh họa", status_tone: "success",
    formula: "Nợ hiện hữu ÷ Thu nhập dùng để tính", note: "Do Python tính.", source_role: "calculated"
  }],
  top_risks: [{
    code: "R-001", name: "Thu nhập không nhất quán", severity: "HIGH", severity_label: "CAO",
    severity_tone: "danger", description: "Các nguồn thu nhập chênh lệch.", difference: "44,0%",
    evidence: [{ document: "sao_ke.pdf", page: 4, field: "Thu nhập sao kê", value: "14.000.000 ₫", excerpt: null }]
  }],
  total_risk_count: 1,
  findings: [
    { category: "finding", title: "Thu nhập dùng để tính", detail: "14.000.000 ₫ · Sao kê", tone: "info" },
    { category: "verification", title: "Cần chuyên viên xác minh", detail: "Đối chiếu thu nhập", tone: "warning" }
  ],
  evidence: [{ document: "sao_ke.pdf", page: 4, field: "Thu nhập sao kê", value: "14.000.000 ₫", excerpt: null }],
  document_count: 4,
  extracted_field_count: 20,
  ai_explanation: "Đây là phần diễn giải đã có trong phiên."
};

const METHODOLOGY: V2MethodologyPageViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "methodology_page",
  theme: "light",
  layers: ["DỮ KIỆN", "PHÂN TÍCH XÁC ĐỊNH", "DIỄN GIẢI AI"].map((label, index) => ({ key: `layer-${index}`, label, description: `Mô tả lớp ${index + 1}` })),
  formulas: ["DTI", "DSR", "Thu nhập còn lại", "Chênh lệch thu nhập", "Biến động thu nhập", "Hệ số đệm số dư"].map((name, index) => ({ key: `formula-${index}`, name, formula: "Công thức hiện hành", meaning: "Ý nghĩa hiện hành", limitation: "Giới hạn hiện hành" })),
  capabilities: ["PDF số", "PDF bảng", "PDF quét", "PDF hỗn hợp", "PDF mật khẩu"].map((document_type) => ({ document_type, support_level: "Một phần", limitation: "Cần đối chiếu" })),
  limitations: [{ title: "LIMITATIONS & HUMAN REVIEW", items: ["Quyết định cuối cùng thuộc về con người."] }],
  self_test_definition: "Kiểm tra phần mềm có chạy đúng không.",
  evaluation_definition: "Đo hệ thống hoạt động tốt đến mức nào."
};

const EVALUATION: V2EvaluationPageViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "evaluation_page",
  theme: "light",
  state: "success",
  state_message: "Báo cáo đã lưu trong phiên.",
  run_id: "eval-12345678",
  metadata: [{ label: "Run ID", value: "eval-12345678" }],
  dataset: [{ label: "Test cases", value: "36" }],
  scorecards: [{ key: "extraction", label: "Extraction Accuracy", raw_value: 0.9833, value_display: "98.3%" }],
  field_metrics: [{ name: "thu_nhap_ke_khai", correct: 35, total: 36, accuracy: "97.2%", detail: "numeric tolerance" }],
  risk_metrics: [{ name: "INCOME_MISMATCH", tp: 8, fp: 1, fn: 1, tn: 26, precision: "88.9%", recall: "88.9%", f1: "88.9%", detail: null }],
  status_metrics: [{ name: "REVIEW READY", tp: 12, fp: 0, fn: 1, tn: null, precision: "100.0%", recall: "92.3%", f1: "96.0%", detail: null }],
  confusion_labels: ["REVIEW READY", "HUMAN REVIEW REQUIRED", "INSUFFICIENT INFORMATION"],
  confusion_rows: [
    { actual: "REVIEW READY", predicted: [12, 1, 0] },
    { actual: "HUMAN REVIEW REQUIRED", predicted: [0, 11, 0] },
    { actual: "INSUFFICIENT INFORMATION", predicted: [0, 0, 12] }
  ],
  grounding: [{ variant: "Structured + evidence", evidence_coverage: "96.9%", unsupported_claim_rate: "0.9%", factual_consistency: "94.4%" }],
  baselines: [{ baseline: "Cross-document comparison", variant: "CURRENT SYSTEM", values: [{ label: "Risk F1", value: "91.2%" }] }],
  processing: [{ label: "Evaluation runtime", value: "25 ms" }],
  failure_cases: [
    { case_id: "FAIL-01", scenario: "PDF quét", expected: "OCR hoặc human review", actual: "N/A", failure_type: "Scanned PDF / no text", probable_cause: "Không có lớp text", mitigation: "Thêm OCR", status: "KNOWN LIMITATION" },
    { case_id: "FAIL-05", scenario: "Nợ kê khai bằng 0", expected: "Không chia cho 0", actual: "Đã kiểm thử", failure_type: "Zero declared debt", probable_cause: "Mẫu số 0", mitigation: "Nhánh tuyệt đối", status: "MITIGATED" }
  ],
  limitations: ["Synthetic/anonymized dataset."],
  llm_api_calls: 0
};

afterEach(cleanup);

describe("Cluster 5 support pages", () => {
  it("renders deterministic Summary hierarchy, Human Review, evidence and labelled AI output", () => {
    render(<SummaryPage viewModel={SUMMARY} />);
    expect(screen.getByRole("heading", { name: "Tóm tắt thẩm định tín dụng", level: 1 })).toBeTruthy();
    expect(screen.getByText("Nguyễn Minh Anh")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "DTI hiện hữu" })).toBeTruthy();
    expect(screen.getAllByText("HIGH · CAO").length).toBeGreaterThanOrEqual(2);
    expect(screen.getByRole("heading", { name: "System assessment" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Human Review" })).toBeTruthy();
    expect(screen.getByText("AI-generated explanation")).toBeTruthy();
    expect(screen.getByText(/Word, Excel, PDF, Markdown và JSON/)).toBeTruthy();
  });

  it("renders methodology as formula cards and separates Self-test from Evaluation", () => {
    render(<MethodologyPage viewModel={METHODOLOGY} />);
    expect(screen.getByRole("heading", { name: "Phương pháp và giới hạn", level: 1 })).toBeTruthy();
    expect(screen.getAllByText("Công thức hiện hành", { selector: "code" }).length).toBe(6);
    expect(screen.getByRole("heading", { name: "SELF-TEST" })).toBeTruthy();
    expect(screen.getByRole("heading", { name: "EVALUATION" })).toBeTruthy();
    expect(screen.getByRole("table", { name: "Bảng khả năng đọc PDF" })).toBeTruthy();
  });

  it("renders real Evaluation scorecards, accessible confusion matrix and local failure filters", () => {
    render(<EvaluationPage viewModel={EVALUATION} onDomainEvent={() => undefined} />);
    expect(screen.getByText("98.3%")).toBeTruthy();
    expect(screen.getByText("LLM API calls: 0")).toBeTruthy();
    expect(screen.getByRole("table", { name: "Confusion matrix trạng thái" })).toBeTruthy();
    fireEvent.change(screen.getByLabelText("Failure type"), { target: { value: "Zero declared debt" } });
    expect(screen.getByText("1/2 cases")).toBeTruthy();
    expect(screen.queryByRole("heading", { name: "Scanned PDF / no text" })).toBeNull();
    expect(screen.getByRole("heading", { name: "Zero declared debt" })).toBeTruthy();
  });

  it("emits exactly one typed Evaluation run event after duplicate clicks", () => {
    const handler = vi.fn();
    render(<EvaluationPage viewModel={{ ...EVALUATION, state: "idle" }} onDomainEvent={handler} />);
    const button = screen.getByRole("button", { name: "Run Evaluation" });
    fireEvent.click(button);
    fireEvent.click(button);
    expect(handler).toHaveBeenCalledTimes(1);
    expect(handler.mock.calls[0]?.[0]).toMatchObject({ component: "evaluation_page", type: "evaluation.run", action: "run" });
  });

  it("strictly parses all Cluster 5 contracts and rejects secret-shaped fields", () => {
    expect(parseSummaryPageViewModel(SUMMARY)).toEqual(SUMMARY);
    expect(parseMethodologyPageViewModel(METHODOLOGY)).toEqual(METHODOLOGY);
    expect(parseEvaluationPageViewModel(EVALUATION)).toEqual(EVALUATION);
    expect(() => parseEvaluationPageViewModel({ ...EVALUATION, api_key: "never-send" })).toThrow(/prohibited/i);
  });
});
