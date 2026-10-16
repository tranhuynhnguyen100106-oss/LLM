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

  it("bảng xác nhận phân loại: selectbox phát upload_assign, tiếp tục bị khóa khi trùng loại", () => {
    const base = parseV3Payload(fixtures.locked);
    const plan = {
      mode: "directory",
      rows: [
        { id: "f1", path: "HOSO/don_de_nghi_vay.pdf", size_label: "2 KB", type: "application", detected_label: "Đơn đề nghị vay vốn", confidence: 0.92, basis: "Tên tệp + nội dung", changed: false, note: "" },
        { id: "f2", path: "HOSO/sub/a.pdf", size_label: "2 KB", type: "application", detected_label: "Đơn đề nghị vay vốn", confidence: 0.74, basis: "Nội dung PDF", changed: false, note: "" }
      ],
      skipped: [{ path: "HOSO/ghi_chu.txt", reason: "Không phải PDF — bỏ qua." }],
      options: [
        { value: "application", label: "Đơn đề nghị vay vốn" },
        { value: "income", label: "Chứng từ thu nhập" },
        { value: "statement", label: "Sao kê ngân hàng" },
        { value: "debt", label: "Thông tin nghĩa vụ nợ" },
        { value: "skip", label: "Bỏ qua (không dùng)" }
      ],
      issues: [{ level: "error" as const, text: "Có 2 tệp cùng loại Đơn đề nghị vay vốn." }],
      can_continue: false
    };
    const { emit } = mount({ ...base, privacy: { ...base.privacy, upload_plan: plan } });
    expect(screen.getByText("Xác nhận phân loại tài liệu")).toBeTruthy();
    expect(screen.getByText("HOSO/sub/a.pdf")).toBeTruthy();
    expect(screen.getByText(/Có 2 tệp cùng loại/)).toBeTruthy();
    const next = screen.getByRole("button", { name: "Tiếp tục trích xuất" });
    expect(next.hasAttribute("disabled")).toBe(true);
    fireEvent.change(screen.getByLabelText("Loại tài liệu của HOSO/sub/a.pdf"), { target: { value: "income" } });
    expect(emit.mock.calls.at(-1)![0]).toMatchObject({ type: "upload_assign", id: "f2", doc_type: "income" });
  });

  it("nút Chọn thư mục dùng input webkitdirectory", () => {
    mount(parseV3Payload(fixtures.locked));
    expect(screen.getAllByRole("button", { name: /Chọn thư mục/ }).length).toBeGreaterThan(0);
    expect(document.querySelector('[data-testid="cl-folder-input"]')!.hasAttribute("webkitdirectory")).toBe(true);
  });

  it("lỗi 5xx: nút Thử lại / Thử bằng model khác, mỗi lần bấm 1 event, bấm lặp không phát thêm", () => {
    const base = parseV3Payload(fixtures.summary);
    const notice = {
      role: "assistant" as const,
      content: "**Không nhận được phản hồi từ Gemini 3.8 Flash.** Model gemini-3.8-flash đang quá tải phía Google (không phải lỗi API Key). (mã GEM-503)",
      modelUsed: "Hệ thống",
      timestamp: 2,
      retry: { id: "r123", label: "Gemini 3.8 Flash", alt_label: "Gemini 3.1 Flash Lite" }
    };
    const withRetry = { ...base, chat: { ...base.chat, messages: [{ role: "user" as const, content: "hello", timestamp: 1 }, notice] } };
    const { emit, view } = mount(withRetry);
    fireEvent.click(screen.getAllByRole("button", { name: "Mở Trợ lý Thẩm định Gemini" })[0]!);
    fireEvent.click(screen.getByRole("button", { name: "Thử bằng Gemini 3.1 Flash Lite" }));
    const retries = () => emit.mock.calls.filter(([e]) => e.type === "chat_retry");
    expect(retries()).toHaveLength(1);
    expect(retries()[0]![0]).toMatchObject({ retry_id: "r123", alt: true });
    expect(screen.queryByRole("button", { name: /Thử lại/ })).toBeNull(); // đang chờ: thông báo cũ ẩn
    view.unmount();
    const noAlt = { ...withRetry, chat: { ...withRetry.chat, messages: [withRetry.chat.messages[0]!, { ...notice, retry: { ...notice.retry, alt_label: null } }] } };
    const second = mount(noAlt);
    fireEvent.click(screen.getAllByRole("button", { name: "Mở Trợ lý Thẩm định Gemini" })[0]!);
    expect(screen.queryByRole("button", { name: /Thử bằng/ })).toBeNull();
    const again = screen.getByRole("button", { name: "↻ Thử lại" });
    fireEvent.click(again);
    fireEvent.click(again);
    const sent = second.emit.mock.calls.filter(([e]) => e.type === "chat_retry");
    expect(sent).toHaveLength(1);
    expect(sent[0]![0]).toMatchObject({ retry_id: "r123", alt: false });
  });

  it("từ chối payload chứa khóa bị cấm", () => {
    expect(() => parseV3Payload({ ...fixtures.summary, api_key: "x" })).toThrow();
    expect(() => parseV3Payload({ ...fixtures.summary, chat: { ...fixtures.summary.chat, token: "x" } })).toThrow();
  });
});
