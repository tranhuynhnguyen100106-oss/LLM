import { cleanup, fireEvent, render, screen } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { V2StatusCard } from "../src/V2StatusCard";
import type { V2StatusCardViewModel } from "../src/contracts";

const VIEW_MODEL: V2StatusCardViewModel = {
  schema_version: "1.0",
  component_version: "0.5.0",
  component: "v2_status_card",
  theme: "light",
  status: "info",
  title: "Bản thử nghiệm UI v2",
  message: "Không thay thế trang hiện hành.",
  details: ["Chi tiết chỉ mở ở frontend."],
  action_label: "Xác nhận cầu nối",
  loading: false,
  error: null
};

afterEach(cleanup);

describe("V2StatusCard", () => {
  it("renders and keeps disclosure interaction local", () => {
    const onDomainEvent = vi.fn();
    render(<V2StatusCard viewModel={VIEW_MODEL} onDomainEvent={onDomainEvent} />);

    expect(screen.getByRole("heading", { name: VIEW_MODEL.title })).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Xem chi tiết kỹ thuật" }));
    expect(screen.getByText("Chi tiết chỉ mở ở frontend.")).toBeTruthy();
    expect(onDomainEvent).not.toHaveBeenCalled();
  });

  it("emits one typed event only for the domain action", () => {
    const onDomainEvent = vi.fn();
    render(<V2StatusCard viewModel={VIEW_MODEL} onDomainEvent={onDomainEvent} />);

    fireEvent.click(screen.getByRole("button", { name: "Xác nhận cầu nối" }));
    expect(onDomainEvent).toHaveBeenCalledTimes(1);
    expect(onDomainEvent.mock.calls[0]?.[0]).toMatchObject({
      schema_version: "1.0",
      component: "v2_status_card",
      type: "status_card.action",
      action: "acknowledge"
    });
  });

  it("renders loading and error contracts without emitting an event", () => {
    const onDomainEvent = vi.fn();
    const { rerender } = render(
      <V2StatusCard viewModel={{ ...VIEW_MODEL, loading: true }} onDomainEvent={onDomainEvent} />
    );

    expect(screen.getByRole("status").textContent).toContain("Đang chuẩn bị component");
    expect((screen.getByRole("button", { name: "Xác nhận cầu nối" }) as HTMLButtonElement).disabled).toBe(true);

    rerender(
      <V2StatusCard
        viewModel={{ ...VIEW_MODEL, loading: false, error: "Component chưa sẵn sàng." }}
        onDomainEvent={onDomainEvent}
      />
    );
    expect(screen.getByRole("alert").textContent).toContain("Component chưa sẵn sàng");
    expect((screen.getByRole("button", { name: "Xác nhận cầu nối" }) as HTMLButtonElement).disabled).toBe(true);
    expect(onDomainEvent).not.toHaveBeenCalled();
  });
});
