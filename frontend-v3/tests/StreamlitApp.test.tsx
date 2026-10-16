import { act, cleanup, fireEvent, render, screen } from "@testing-library/react";
import { readFileSync } from "node:fs";
import { resolve } from "node:path";
import { afterEach, describe, expect, it, vi } from "vitest";

import { StreamlitApp } from "../src/StreamlitApp";
import { parseV3Payload, StreamlitCreditLensProvider, type V3AppPayload, type V3Event } from "../src/StreamlitContext";

// View model thật do Python (creditlens_ui_v3.build_v3_payload) sinh ra cho CASE-03.
const fixtures = JSON.parse(readFileSync(resolve(__dirname, "fixtures.json"), "utf-8")) as {
  locked: V3AppPayload;
  summary: V3AppPayload;
};

function mount(payload: V3AppPayload) {
  const emit = vi.fn<(event: V3Event) => void>();
  const view = render(
    <StreamlitCreditLensProvider payload={payload} emit={emit}>
      <StreamlitApp payload={payload} />
    </StreamlitCreditLensProvider>
  );
  return { emit, view };
}

afterEach(() => {
  cleanup();
  document.body.innerHTML = "";
});

describe("UI v3 trên Streamlit", () => {
  it("khóa trang 2–5 trước Bước 0 và không phát event điều hướng cho trang bị khóa", () => {
    const { emit } = mount(parseV3Payload(fixtures.locked));
    const locked = screen.getAllByRole("button").find((b) => b.getAttribute("data-page") === "2_extraction")!;
    expect(locked.hasAttribute("disabled")).toBe(true);
    fireEvent.click(locked);
    expect(emit).not.toHaveBeenCalled();
    expect(screen.getAllByText("Bước 0 · Bảo mật hồ sơ").length).toBeGreaterThan(0);
    expect(screen.getByText("KH_01")).toBeTruthy();
    const methodology = screen.getAllByRole("button").find((b) => b.getAttribute("data-page") === "6_methodology")!;
    fireEvent.click(methodology);
    expect(emit).toHaveBeenCalledTimes(1);
    expect(emit.mock.calls[0]![0]).toMatchObject({ type: "navigate", page: "6_methodology" });
  });

  it("trang Tóm tắt dùng view model Python đã giả danh hóa và huy hiệu trên App Shell", () => {
    mount(parseV3Payload(fixtures.summary));
    expect(screen.getAllByText(/Đã giả danh hóa · \d+ trường/).length).toBeGreaterThan(0);
    expect(screen.getAllByText("KH_01").length).toBeGreaterThan(0);
    expect(document.body.textContent).not.toContain("Nguyễn Minh Anh");
  });

  it("một lần Send phát đúng một event; submit rỗng và rerender không phát event", () => {
    const payload = parseV3Payload(fixtures.summary);
    const { emit, view } = mount(payload);
    fireEvent.click(screen.getAllByRole("button", { name: "Mở Trợ lý Thẩm định Gemini" })[0]!);
    const textarea = document.querySelector<HTMLTextAreaElement>(".cl-chat-drawer-container textarea")!;
    fireEvent.keyDown(textarea, { key: "Enter" });
    expect(emit).not.toHaveBeenCalled();
    fireEvent.change(textarea, { target: { value: "DTI của hồ sơ này?" } });
    fireEvent.keyDown(textarea, { key: "Enter" });
    fireEvent.keyDown(textarea, { key: "Enter" });
    const sends = emit.mock.calls.filter(([event]) => event.type === "chat_send");
    expect(sends).toHaveLength(1);
    expect(sends[0]![0]).toMatchObject({ text: "DTI của hồ sơ này?" });
    act(() => {
      view.rerender(
        <StreamlitCreditLensProvider payload={{ ...payload, revision: payload.revision + 1 }} emit={emit}>
          <StreamlitApp payload={payload} />
        </StreamlitCreditLensProvider>
      );
    });
    expect(emit.mock.calls.filter(([event]) => event.type === "chat_send")).toHaveLength(1);
  });

  it("chatbot không có ô nhập khóa trong trình duyệt và không ghi khóa vào localStorage", () => {
    const setItem = vi.spyOn(Storage.prototype, "setItem");
    mount(parseV3Payload(fixtures.summary));
    fireEvent.click(screen.getAllByRole("button", { name: "Mở Trợ lý Thẩm định Gemini" })[0]!);
    expect(document.querySelector('input[type="password"]')).toBeNull();
    expect(screen.getAllByText(/Chưa kết nối AI/).length).toBeGreaterThan(0);
    expect(setItem.mock.calls.some(([key]) => String(key).includes("gemini"))).toBe(false);
  });

  it("nút tải xuống của React gọi st.download_button gốc do Python tạo", () => {
    const native = document.createElement("div");
    native.className = "st-key-v3_dl_markdown";
    const button = document.createElement("button");
    const click = vi.fn();
    button.addEventListener("click", click);
    native.appendChild(button);
    document.body.appendChild(native);
    mount(parseV3Payload(fixtures.summary));
    fireEvent.click(screen.getByRole("button", { name: /Tải báo cáo Markdown/ }));
    expect(click).toHaveBeenCalledTimes(1);
  });

  it("từ chối payload chứa khóa bị cấm", () => {
    expect(() => parseV3Payload({ ...fixtures.summary, api_key: "x" })).toThrow();
    expect(() => parseV3Payload({ ...fixtures.summary, chat: { ...fixtures.summary.chat, token: "x" } })).toThrow();
  });
});
