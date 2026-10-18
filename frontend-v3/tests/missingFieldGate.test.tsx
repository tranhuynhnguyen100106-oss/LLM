import { cleanup, fireEvent, render, screen, waitFor } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StreamlitApp } from "../src/StreamlitApp";
import { parseV3Payload, StreamlitCreditLensProvider, type V3AppPayload, type V3Event } from "../src/StreamlitContext";

const fixtures = JSON.parse(readFileSync(resolve(__dirname, "fixtures.json"), "utf-8")) as { summary: V3AppPayload };

const GATE = {
  open: true,
  title: "Hồ sơ còn thiếu thông tin",
  explanation:
    "Nếu tiếp tục, hồ sơ sẽ được đánh giá ở trạng thái INSUFFICIENT INFORMATION / HUMAN REVIEW REQUIRED. Các chỉ số phụ thuộc trường thiếu sẽ hiển thị 'Chưa đủ dữ liệu'.",
  groups: [
    {
      doc: "application",
      doc_label: "Đơn đề nghị vay vốn",
      items: [
        { field: "so_tien_de_nghi_vay", label: "Số tiền đề nghị vay", level: "Bắt buộc" as const },
        { field: "chi_phi_sinh_hoat", label: "Chi phí sinh hoạt", level: "Nên có" as const }
      ]
    }
  ],
  required_count: 1,
  can_ai: false,
  can_restore_files: true
};

function mount(gate: typeof GATE | null) {
  const payload = parseV3Payload({ ...fixtures.summary, missing_gate: gate });
  const emit = vi.fn<(event: V3Event) => void>();
  render(
    <StreamlitCreditLensProvider payload={payload} emit={emit}>
      <StreamlitApp payload={payload} />
    </StreamlitCreditLensProvider>
  );
  return emit;
}

afterEach(() => {
  cleanup();
  document.body.innerHTML = "";
});

describe("Hộp thoại Hồ sơ còn thiếu thông tin", () => {
  it("không hiện khi hồ sơ đủ", () => {
    mount(null);
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("liệt kê trường theo tài liệu, có mức độ, focus vào nút an toàn", async () => {
    mount(GATE);
    const dialog = screen.getByRole("alertdialog");
    expect(dialog.getAttribute("aria-modal")).toBe("true");
    expect(dialog.textContent).toContain("Đơn đề nghị vay vốn");
    expect(dialog.textContent).toContain("Số tiền đề nghị vay");
    expect(dialog.textContent).toContain("Bắt buộc");
    expect(dialog.textContent).toContain("Nên có");
    expect(dialog.textContent).toContain("INSUFFICIENT INFORMATION / HUMAN REVIEW REQUIRED");
    await waitFor(() => expect(document.activeElement?.textContent).toBe("Bổ sung tài liệu"));
    expect(screen.queryByRole("button", { name: /Bổ sung bằng AI/ })).toBeNull();
    // Focus bị kéo ra ngoài hộp thoại → quay lại nút an toàn.
    const outside = screen.getAllByRole("button").find((b) => !dialog.contains(b))!;
    outside.focus();
    await waitFor(() => expect(document.activeElement?.textContent).toBe("Bổ sung tài liệu"));
  });

  it("nút AI chỉ hiện khi có trường số/ngày thiếu", () => {
    mount({ ...GATE, can_ai: true });
    expect(screen.getByRole("button", { name: /Bổ sung bằng AI/ })).toBeTruthy();
  });

  it("mỗi nút phát đúng một event; bấm lại khi chưa có payload mới không phát thêm", () => {
    const emit = mount({ ...GATE, can_ai: true });
    fireEvent.click(screen.getByRole("button", { name: /Tiếp tục đánh giá/ }));
    fireEvent.click(screen.getByRole("button", { name: /Hủy hồ sơ/ }));
    expect(emit).toHaveBeenCalledTimes(1);
    expect(emit.mock.calls[0]![0]).toMatchObject({ type: "missing_gate_continue" });
  });

  it.each([
    [/Bổ sung tài liệu/, "missing_gate_supplement"],
    [/Bổ sung bằng AI/, "missing_gate_ai"],
    [/Hủy hồ sơ/, "missing_gate_cancel"]
  ])("nút %s → %s", (name, type) => {
    const emit = mount({ ...GATE, can_ai: true });
    fireEvent.click(screen.getByRole("button", { name }));
    expect(emit.mock.calls[0]![0]).toMatchObject({ type });
  });

  it("Esc = Bổ sung tài liệu (trong hộp thoại hoặc khi focus ở ngoài), chỉ 1 event", () => {
    const emit = mount(GATE);
    fireEvent.keyDown(screen.getByRole("alertdialog"), { key: "Escape" });
    expect(emit).toHaveBeenCalledTimes(1);
    expect(emit.mock.calls[0]![0]).toMatchObject({ type: "missing_gate_supplement" });
    cleanup();
    const emitOutside = mount(GATE);
    fireEvent.keyDown(document.body, { key: "Escape" });
    expect(emitOutside).toHaveBeenCalledTimes(1);
    expect(emitOutside.mock.calls[0]![0]).toMatchObject({ type: "missing_gate_supplement" });
  });
});
