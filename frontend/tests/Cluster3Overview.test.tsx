import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { AppShell } from "../src/AppShell";
import { DemoCasePanel } from "../src/DemoCasePanel";
import type {
  V2AppShellViewModel,
  V2DemoPanelViewModel,
  WorkflowStep
} from "../src/contracts";

const WORKFLOW: WorkflowStep[] = [
  { key: "intake", label: "Tiếp nhận", description: "Tiếp nhận tài liệu", state: "current", status_label: "Hiện tại" },
  { key: "compute", label: "Tính toán", description: "Tính bằng Python", state: "upcoming", status_label: "Chưa thực hiện" },
  { key: "crosscheck", label: "Đối chiếu", description: "Đối chiếu bằng chứng", state: "upcoming", status_label: "Chưa thực hiện" },
  { key: "human", label: "Con người xem xét", description: "Chuyên viên quyết định", state: "upcoming", status_label: "Chưa thực hiện" }
];

const CASE_CONTEXT = {
  case_id: null,
  source: null,
  status_label: "Chưa có hồ sơ đang mở",
  status_tone: "neutral" as const,
  summary: "Tải tài liệu hoặc mở hồ sơ minh họa."
};

const SHELL: V2AppShellViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "app_shell",
  theme: "light",
  active_page: "1_overview",
  navigation: Array.from({ length: 8 }, (_, index) => ({
    page: `${index + 1}_${index === 0 ? "overview" : `page_${index + 1}`}`,
    label: index === 0 ? "Tổng quan" : `Trang ${index + 1}`,
    group: index < 5 ? "Hồ sơ" : index < 7 ? "Kiểm chứng" : "Hệ thống",
    ordinal: index + 1
  })),
  workflow: WORKFLOW,
  process_cards: WORKFLOW.map(({ key, label, description, state }) => ({ key, label, description, state })),
  case_context: CASE_CONTEXT,
  logo_data_uri: "data:image/png;base64,AA==",
  overview: true,
  page_state: "empty",
  state_message: "Chưa có hồ sơ đang mở."
};

const DEMO: V2DemoPanelViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "demo_panel",
  theme: "light",
  cases: Array.from({ length: 10 }, (_, index) => ({
    case_name: `CASE-${String(index + 1).padStart(2, "0")} — Tình huống ${index + 1}`,
    case_code: `CASE-${String(index + 1).padStart(2, "0")}`,
    title: `Tình huống ${index + 1}`,
    description: "Dữ liệu tổng hợp xác định; không gọi mô hình."
  })),
  selected_case: "CASE-03 — Tình huống 3",
  case_context: CASE_CONTEXT,
  loading: false,
  error: null
};

afterEach(cleanup);

describe("Cluster 3 App Shell and Overview", () => {
  it("renders eight-page navigation, four-step workflow, disclosure, and case state", () => {
    render(<AppShell viewModel={SHELL} onDomainEvent={vi.fn()} />);

    expect(screen.getAllByRole("button", { name: /Tổng quan|Trang/ })).toHaveLength(8);
    expect(screen.getByRole("heading", { name: "Tổng quan và hồ sơ" })).toBeTruthy();
    expect(screen.getByText("Không dùng LLM để mở trang")).toBeTruthy();
    expect(screen.getByRole("status").textContent).toContain("Chưa có hồ sơ");
    expect(screen.getByRole("list").querySelectorAll("li")).toHaveLength(4);
    expect(screen.getByRole("button", { name: "Tổng quan" }).getAttribute("aria-current")).toBe("page");
  });

  it("emits one typed navigation event from the selected page", () => {
    const onDomainEvent = vi.fn();
    render(<AppShell viewModel={SHELL} onDomainEvent={onDomainEvent} />);

    fireEvent.click(screen.getByRole("button", { name: "Trang 2" }));
    expect(onDomainEvent).toHaveBeenCalledTimes(1);
    expect(onDomainEvent.mock.calls[0]?.[0]).toMatchObject({
      component_version: "0.5.0",
      component: "app_shell",
      type: "navigation.select",
      action: "select",
      page: "2_page_2"
    });
  });

  it("opens and closes the compact navigation with keyboard focus recovery", () => {
    render(<AppShell viewModel={SHELL} onDomainEvent={vi.fn()} />);
    const menu = screen.getByRole("button", { name: "Mở điều hướng" });
    fireEvent.click(menu);
    expect(screen.getByRole("button", { name: "Tổng quan" })).toBe(document.activeElement);
    fireEvent.keyDown(document, { key: "Escape" });
    expect(screen.getByRole("button", { name: "Mở điều hướng" })).toBe(document.activeElement);
  });

  it("moves keyboard focus to the main content when the skip link is activated", () => {
    render(<AppShell viewModel={SHELL} onDomainEvent={vi.fn()} />);
    const main = document.querySelector<HTMLElement>("#cl-v2-main");
    expect(main).toBeTruthy();
    fireEvent.click(screen.getByRole("link", { name: "Chuyển đến nội dung chính" }));
    expect(main).toBe(document.activeElement);
  });

  it("keeps demo selection and open actions typed and disables double action while processing", () => {
    const onDomainEvent = vi.fn();
    const { rerender } = render(<DemoCasePanel viewModel={DEMO} onDomainEvent={onDomainEvent} />);

    fireEvent.change(screen.getByLabelText("Chọn hồ sơ"), { target: { value: DEMO.cases[3]?.case_name } });
    fireEvent.click(screen.getByRole("button", { name: "Mở hồ sơ minh họa" }));
    fireEvent.click(screen.getByRole("button", { name: "Mở hồ sơ minh họa" }));
    expect(onDomainEvent.mock.calls[0]?.[0]).toMatchObject({ type: "demo.select", action: "select" });
    expect(onDomainEvent.mock.calls[1]?.[0]).toMatchObject({
      type: "demo.open",
      action: "open",
      case_name: DEMO.selected_case
    });
    expect(onDomainEvent).toHaveBeenCalledTimes(2);

    rerender(<DemoCasePanel viewModel={{ ...DEMO, loading: true }} onDomainEvent={onDomainEvent} />);
    expect((screen.getByRole("button", { name: "Mở hồ sơ minh họa" }) as HTMLButtonElement).disabled).toBe(true);
    expect(screen.getByRole("status").textContent).toContain("Đang xử lý");
  });
});
