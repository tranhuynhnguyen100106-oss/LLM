import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../src/AppShell";
import { PrivacyGatewayPage } from "../src/PrivacyGatewayPage";
import {
  parseAppShellViewModel,
  parsePrivacyGatewayViewModel,
  parseViewModel,
  type V2AppShellViewModel,
  type V2PrivacyGatewayViewModel,
  type WorkflowStep
} from "../src/contracts";

const WORKFLOW: WorkflowStep[] = ["intake", "compute", "crosscheck", "human"].map((key) => ({
  key,
  label: key,
  description: "Mô tả",
  state: "upcoming",
  status_label: "Chưa thực hiện"
}));

const LOCK = "Đang khóa: hoàn tất Bước 0 · Bảo mật hồ sơ (xác nhận và giả danh hóa) để mở trang này.";

function shell(locked: boolean): V2AppShellViewModel {
  return {
    schema_version: "1.0",
    component_version: "0.5.0",
    component: "app_shell",
    theme: "light",
    active_page: "page-1",
    navigation: Array.from({ length: 8 }, (_, index) => ({
      page: `page-${index + 1}`,
      label: `Trang ${index + 1}`,
      group: index < 5 ? "Hồ sơ" : index < 7 ? "Kiểm chứng" : "Hệ thống",
      ordinal: index + 1,
      locked: locked && index >= 1 && index <= 4,
      lock_reason: locked && index >= 1 && index <= 4 ? LOCK : ""
    })),
    workflow: WORKFLOW,
    process_cards: WORKFLOW.map(({ key, label, description, state }) => ({ key, label, description, state })),
    case_context: { case_id: null, source: null, status_label: "Chưa có hồ sơ", status_tone: "neutral", summary: "—" },
    logo_data_uri: "data:image/png;base64,AA==",
    overview: true,
    page_state: "empty",
    state_message: "Chưa có hồ sơ đang mở.",
    privacy: locked
      ? { state: "pending", label: "Chưa qua Bước 0", count: 0 }
      : { state: "done", label: "Đã giả danh hóa · 10 trường", count: 10 }
  };
}

const PRIVACY: V2PrivacyGatewayViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "privacy_gateway_page",
  theme: "light",
  state: "review",
  badge_label: "Chờ xác nhận · 2 trường",
  field_count: 2,
  public_warning: "Bản công khai chỉ dành cho dữ liệu tổng hợp hoặc đã ẩn danh. Không tải hồ sơ khách hàng thật.",
  consent_text: "Tôi xác nhận hồ sơ được xử lý theo quy định bảo mật.",
  consent_given: false,
  case_id: "EVAL-001",
  rows: [
    { pii_type: "Họ tên khách hàng", masked_value: "Nguyễn M*** A**", replacement: "KH_01", document: "01_don.pdf", page: 1, source: "Dữ liệu trích xuất", required: true },
    { pii_type: "Số điện thoại", masked_value: "**********", replacement: "[SĐT_ĐÃ_CHE]", document: "01_don.pdf", page: 1, source: "Regex mẫu VN", required: true }
  ],
  counts: [{ label: "Họ tên khách hàng", count: 1 }, { label: "Số điện thoại", count: 1 }],
  audit: []
};

afterEach(cleanup);

describe("Privacy Gateway · Bước 0", () => {
  it("locks later pages with an explanation and never emits navigation for them", () => {
    const onDomainEvent = vi.fn();
    render(<AppShell viewModel={parseAppShellViewModel(shell(true))} onDomainEvent={onDomainEvent} />);
    const locked = screen.getByRole("button", { name: `Trang 2 — ${LOCK}` });
    expect(locked.hasAttribute("disabled")).toBe(true);
    expect(locked.getAttribute("title")).toBe(LOCK);
    fireEvent.click(locked);
    expect(onDomainEvent).not.toHaveBeenCalled();
    fireEvent.click(screen.getByRole("button", { name: "Trang 6" }));
    expect(onDomainEvent).toHaveBeenCalledTimes(1);
    expect(screen.getByLabelText(/Trạng thái bảo mật hồ sơ/).textContent).toContain("Chưa qua Bước 0");
  });

  it("shows the pseudonymized badge on the App Shell once the gateway is complete", () => {
    render(<AppShell viewModel={parseAppShellViewModel(shell(false))} onDomainEvent={vi.fn()} />);
    expect(screen.getByLabelText(/Trạng thái bảo mật hồ sơ/).textContent).toContain("Đã giả danh hóa · 10 trường");
    expect(screen.getByRole("button", { name: "Trang 2" }).hasAttribute("disabled")).toBe(false);
  });

  it("renders the public warning and a masked-only preview table", () => {
    const parsed = parseViewModel(PRIVACY);
    expect(parsed.component).toBe("privacy_gateway_page");
    render(<PrivacyGatewayPage viewModel={parsePrivacyGatewayViewModel(PRIVACY)} />);
    expect(screen.getByRole("heading", { name: "Bước 0 · Bảo mật hồ sơ" })).toBeTruthy();
    expect(screen.getByRole("alert").textContent).toContain("Không tải hồ sơ khách hàng thật");
    expect(screen.getByText("KH_01")).toBeTruthy();
    expect(screen.getByText("Nguyễn M*** A**")).toBeTruthy();
    expect(document.body.textContent).not.toContain("Nguyễn Minh Anh");
  });

  it("rejects payloads carrying prohibited keys such as a raw vault token map", () => {
    expect(() => parsePrivacyGatewayViewModel({ ...PRIVACY, token: { KH_01: "Nguyễn Minh Anh" } })).toThrow();
    expect(() => parsePrivacyGatewayViewModel({ ...PRIVACY, rows: [{ ...PRIVACY.rows[0], required: "yes" }] })).toThrow();
  });
});
