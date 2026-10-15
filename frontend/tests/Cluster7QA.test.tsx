import { readFileSync } from "node:fs";
import { resolve } from "node:path";

import { cleanup, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it } from "vitest";

import { CoreBusinessPage } from "../src/CoreBusinessPage";
import type { V2CorePageViewModel } from "../src/contracts";

const HOSTILE_TEXT = '<img src=x onerror="window.__creditlens_xss=1">';

const EXTRACTION: V2CorePageViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "core_business_page",
  theme: "dark",
  page: "extraction",
  title: "Trích xuất tài liệu",
  subtitle: "Kiểm tra nội dung dài và dữ liệu không tin cậy.",
  state: "success",
  state_message: "Dữ liệu đã sẵn sàng.",
  documents: [],
  fields: [{
    key: "hostile-field",
    label: "Nội dung không tin cậy",
    value_display: HOSTILE_TEXT,
    raw_value: HOSTILE_TEXT,
    source: "ten-tai-lieu-rat-dai-khong-co-dau-ngat-lien-tuc-1234567890.pdf",
    source_role: "observed",
    page: 1,
    confidence: 0.75,
    confidence_display: "75,0%",
    confidence_label: "Cần xác minh",
    confidence_tone: "warning",
    status: "Cần xác minh",
    evidence: null
  }],
  comparisons: [],
  metrics: [],
  thresholds: [],
  risks: [],
  case_status: "CẦN CON NGƯỜI XEM XÉT"
};

afterEach(cleanup);

describe("Cluster 7 accessibility, responsive and security gates", () => {
  it("renders untrusted text as text rather than executable HTML", () => {
    const { container } = render(<CoreBusinessPage viewModel={EXTRACTION} />);
    expect(screen.getByText(HOSTILE_TEXT)).toBeTruthy();
    expect(container.querySelector("img")).toBeNull();
    expect(container.querySelector("script")).toBeNull();
  });

  it("keeps the production CSS responsive and reduced-motion aware", () => {
    const css = readFileSync(resolve(process.cwd(), "src/styles.css"), "utf8");
    expect(css).toContain("@media (prefers-reduced-motion: reduce)");
    expect(css).toContain("overflow-wrap: anywhere");
    expect(css).toContain("@media (max-width: 767px)");
  });
});
