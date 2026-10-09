import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { SettingsPage } from "../src/Cluster6SettingsPage";
import { parseSettingsPageViewModel, type V2SettingsPageViewModel } from "../src/contracts";

const SETTINGS: V2SettingsPageViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "settings_page",
  theme: "dark",
  connection_state: "connected",
  connection_status_label: "CONNECTED",
  active_provider_label: "OpenAI · GPT",
  active_model: "gpt-test",
  providers: [
    { provider: "openai", label: "OpenAI · GPT", description: "GPT models", connected: true, active: true, model: "gpt-test", model_count: 2, status_label: "ĐANG DÙNG", status_tone: "success" },
    { provider: "gemini", label: "Google · Gemini", description: "Gemini models", connected: false, active: false, model: null, model_count: 0, status_label: "CHƯA KẾT NỐI", status_tone: "neutral" },
    { provider: "anthropic", label: "Anthropic · Claude", description: "Claude models", connected: false, active: false, model: null, model_count: 0, status_label: "CHƯA KẾT NỐI", status_tone: "neutral" },
    { provider: "deepseek", label: "DeepSeek", description: "DeepSeek models", connected: false, active: false, model: null, model_count: 0, status_label: "CHƯA KẾT NỐI", status_tone: "neutral" }
  ],
  thresholds: [
    ["do_tin_cay_thap", "Độ tin cậy tối thiểu", 0.75, "75,0%"],
    ["chenh_lech_thu_nhap", "Chênh lệch thu nhập", 0.15, "15,0%"],
    ["chenh_lech_thu_nhap_nghiem_trong", "Chênh lệch thu nhập nghiêm trọng", 0.3, "30,0%"],
    ["chenh_lech_no", "Chênh lệch nợ", 0.2, "20,0%"],
    ["dti_canh_bao", "Cảnh báo DTI", 0.4, "40,0%"],
    ["dsr_canh_bao", "Cảnh báo DSR", 0.45, "45,0%"],
    ["he_so_dem_so_du_thap", "Hệ số đệm số dư tối thiểu", 1, "1,00×"],
    ["bien_dong_thu_nhap_cao", "Biến động thu nhập cao", 0.25, "25,0%"]
  ].map(([key, label, value, value_display]) => ({
    key: key as string,
    label: label as string,
    value: value as number,
    value_display: value_display as string
  })),
  chat_state: "ready",
  chat_message_count: 4,
  current_case: "CASE-03",
  has_result: true,
  evaluation_ready: true,
  error_message: null
};

afterEach(cleanup);

describe("Cluster 6 Settings page", () => {
  it("renders safe connection, provider/model, threshold and chat-session metadata", () => {
    render(<SettingsPage viewModel={SETTINGS} />);
    expect(screen.getByRole("heading", { name: "Cài đặt và trợ lý AI", level: 1 })).toBeTruthy();
    expect(screen.getAllByText("CONNECTED").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("OpenAI · GPT").length).toBeGreaterThanOrEqual(1);
    expect(screen.getAllByText("gpt-test").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("4")).toBeTruthy();
    expect(screen.getByText("75,0%")).toBeTruthy();
    expect(screen.getByRole("heading", { name: "Secure native controls ngay bên dưới" })).toBeTruthy();
  });

  it("renders a textual error state without relying on color", () => {
    render(
      <SettingsPage
        viewModel={{
          ...SETTINGS,
          connection_state: "error",
          connection_status_label: "ERROR",
          error_message: "Không thể xác minh kết nối.",
          chat_state: "error"
        }}
      />
    );
    expect(screen.getByRole("alert")).toBeTruthy();
    expect(screen.getAllByText("ERROR").length).toBeGreaterThanOrEqual(1);
    expect(screen.getByText("Không thể xác minh kết nối.")).toBeTruthy();
  });

  it("strictly rejects credential-shaped fields at any depth", () => {
    expect(parseSettingsPageViewModel(SETTINGS)).toEqual(SETTINGS);
    expect(() => parseSettingsPageViewModel({ ...SETTINGS, api_key: "never-send" })).toThrow(/prohibited/i);
    expect(() => parseSettingsPageViewModel({ ...SETTINGS, providers: [{ ...SETTINGS.providers[0], credentials: "never-send" }] })).toThrow(/prohibited/i);
  });
});
