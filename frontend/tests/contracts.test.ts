import { describe, expect, it } from "vitest";

import {
  createStatusCardEvent,
  parseStatusCardViewModel,
  type V2StatusCardViewModel
} from "../src/contracts";

const SAFE_VIEW_MODEL: V2StatusCardViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "v2_status_card",
  theme: "system",
  status: "info",
  title: "Bản thử nghiệm UI v2",
  message: "View model an toàn.",
  details: ["Python là nguồn sự thật."],
  action_label: "Xác nhận cầu nối",
  loading: false,
  error: null
};

describe("component contracts", () => {
  it("accepts the allowlisted view model", () => {
    expect(parseStatusCardViewModel(SAFE_VIEW_MODEL)).toEqual(SAFE_VIEW_MODEL);
  });

  it("rejects prohibited secret-shaped fields", () => {
    expect(() => parseStatusCardViewModel({ ...SAFE_VIEW_MODEL, api_key: "never-send" })).toThrow(
      /prohibited/i
    );
  });

  it("creates the exact typed domain event", () => {
    expect(createStatusCardEvent(() => "evt_12345678")).toEqual({
      schema_version: "1.0",
      component_version: "0.5.0",
      component: "v2_status_card",
      type: "status_card.action",
      action: "acknowledge",
      event_id: "evt_12345678"
    });
  });
});
