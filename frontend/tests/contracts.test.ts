import { describe, expect, it } from "vitest";

import {
  createNavigationEvent,
  parseAppShellViewModel,
  type V2AppShellViewModel
} from "../src/contracts";

const SAFE_VIEW_MODEL: V2AppShellViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "app_shell",
  theme: "system",
  active_page: "page-1",
  navigation: Array.from({ length: 8 }, (_, index) => ({
    page: `page-${index + 1}`,
    label: `Trang ${index + 1}`,
    group: index < 5 ? "Hồ sơ" : index < 7 ? "Kiểm chứng" : "Hệ thống",
    ordinal: index + 1
  })),
  workflow: ["intake", "compute", "crosscheck", "human"].map((key, index) => ({
    key,
    label: `Bước ${index + 1}`,
    description: "Mô tả xác định",
    state: index === 0 ? "current" : "upcoming",
    status_label: index === 0 ? "Hiện tại" : "Tiếp theo"
  })),
  process_cards: ["intake", "compute", "crosscheck", "human"].map((key, index) => ({
    key,
    label: `Bước ${index + 1}`,
    description: "Mô tả xác định",
    state: index === 0 ? "current" : "upcoming"
  })),
  case_context: {
    case_id: null,
    source: null,
    status_label: "Chưa có hồ sơ",
    status_tone: "neutral",
    summary: "Tải tài liệu để tiếp tục."
  },
  logo_data_uri: "data:image/png;base64,AA==",
  overview: true,
  page_state: "empty",
  state_message: "Chưa có hồ sơ đang mở."
};

describe("component contracts", () => {
  it("accepts the current allowlisted App Shell view model", () => {
    expect(parseAppShellViewModel(SAFE_VIEW_MODEL)).toEqual(SAFE_VIEW_MODEL);
  });

  it("rejects prohibited secret-shaped fields", () => {
    expect(() => parseAppShellViewModel({ ...SAFE_VIEW_MODEL, api_key: "never-send" })).toThrow(
      /prohibited/i
    );
  });

  it("creates the exact typed navigation event", () => {
    expect(createNavigationEvent("page-2", () => "evt_12345678")).toEqual({
      schema_version: "1.0",
      component_version: "0.5.0",
      component: "app_shell",
      type: "navigation.select",
      action: "select",
      event_id: "evt_12345678",
      page: "page-2"
    });
  });
});
