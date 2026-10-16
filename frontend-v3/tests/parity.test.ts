/**
 * Đối chiếu V4: engine.ts (bản AI Studio, chỉ giữ để test) ↔ Python (source of truth).
 * UI v3 luôn hiển thị theo Python; bảng chênh lệch được ghi khi đặt biến PARITY_OUT.
 */
import { readFileSync, writeFileSync } from "node:fs";
import { resolve } from "node:path";
import { describe, expect, it } from "vitest";

import { DEMO_CASES, evaluateDemoCase } from "../../src/domain/demoCases";
import { DEFAULT_THRESHOLDS } from "../../src/domain/engine";

const python = JSON.parse(
  readFileSync(resolve(__dirname, "../../tests/fixtures/v3_parity_python.json"), "utf-8")
) as Record<string, { dti: number | null; dsr: number | null; thu_nhap_dung_de_tinh: number | null; canh_bao_labels: string[]; trang_thai: string }>;

const close = (a: number | null | undefined, b: number | null | undefined) =>
  (a == null && b == null) || (a != null && b != null && Math.abs(a - b) < 1e-9);

describe("V4 parity engine.ts ↔ Python", () => {
  it("so sánh DTI, DSR, thu nhập dùng để tính và danh sách cảnh báo cho 10 demo case", () => {
    const rows = DEMO_CASES.map((definition) => {
      const ts = evaluateDemoCase(definition.case_name, DEFAULT_THRESHOLDS)!;
      const py = python[definition.case_name]!;
      const dti = ts.chi_so.find((m) => m.key === "dti")?.raw_value as number | null;
      const dsr = ts.chi_so.find((m) => m.key === "dsr")?.raw_value as number | null;
      const labels = ts.canh_bao.map((r) => r.name).sort();
      return {
        case_name: definition.case_name,
        dti_ok: close(dti, py.dti),
        dsr_ok: close(dsr, py.dsr),
        income_ok: close(ts.thu_nhap_dung_de_tinh, py.thu_nhap_dung_de_tinh),
        status_ok: ts.trang_thai === py.trang_thai,
        risks_ok: JSON.stringify(labels) === JSON.stringify(py.canh_bao_labels),
        ts: { dti, dsr, income: ts.thu_nhap_dung_de_tinh, status: ts.trang_thai, risks: labels },
        python: { dti: py.dti, dsr: py.dsr, income: py.thu_nhap_dung_de_tinh, status: py.trang_thai, risks: py.canh_bao_labels }
      };
    });
    if (process.env.PARITY_OUT) writeFileSync(process.env.PARITY_OUT, JSON.stringify(rows, null, 1));
    expect(rows).toHaveLength(10);
    // Python là source of truth. Hiện 10/10 case khớp hoàn toàn; nếu sau này lệch, UI vẫn hiển thị
    // theo Python và test này báo đỏ để ghi chênh lệch vào báo cáo.
    for (const row of rows) {
      expect({ case: row.case_name, dti: row.dti_ok, dsr: row.dsr_ok, income: row.income_ok, status: row.status_ok, risks: row.risks_ok }).toEqual({
        case: row.case_name, dti: true, dsr: true, income: true, status: true, risks: true
      });
    }
  });
});
