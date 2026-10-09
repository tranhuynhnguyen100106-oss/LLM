import { useEffect, useId, useRef, useState, type MouseEvent as ReactMouseEvent } from "react";

import {
  createNavigationEvent,
  type V2AppShellViewModel,
  type V2NavigationEvent,
  type WorkflowState
} from "./contracts";

interface AppShellProps {
  viewModel: V2AppShellViewModel;
  onDomainEvent: (event: V2NavigationEvent) => void;
}

const GROUPS: V2AppShellViewModel["navigation"][number]["group"][] = ["Hồ sơ", "Kiểm chứng", "Hệ thống"];

const STEP_ICONS: Record<WorkflowState, string> = {
  upcoming: "·",
  current: "→",
  complete: "✓",
  warning: "!",
  error: "×"
};

const PAGE_STATE_LABELS: Record<V2AppShellViewModel["page_state"], string> = {
  empty: "Chưa có hồ sơ",
  ready: "Sẵn sàng bắt đầu",
  processing: "Đang xử lý",
  success: "Hồ sơ đã sẵn sàng",
  warning: "Cần xem xét",
  error: "Cần xử lý lỗi",
  disabled: "Chưa thể bắt đầu"
};

export function AppShell({ viewModel, onDomainEvent }: AppShellProps) {
  const [navigationOpen, setNavigationOpen] = useState(false);
  const navigationId = useId();
  const legalId = useId();
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const activeNavigationRef = useRef<HTMLButtonElement>(null);
  const mainContentRef = useRef<HTMLElement>(null);

  useEffect(() => {
    if (!navigationOpen) return;
    activeNavigationRef.current?.focus();
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key !== "Escape") return;
      event.preventDefault();
      setNavigationOpen(false);
      menuButtonRef.current?.focus();
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [navigationOpen]);

  const closeNavigation = () => {
    setNavigationOpen(false);
    menuButtonRef.current?.focus();
  };

  const selectPage = (page: string) => {
    setNavigationOpen(false);
    onDomainEvent(createNavigationEvent(page));
  };

  const skipToMainContent = (event: ReactMouseEvent<HTMLAnchorElement>) => {
    event.preventDefault();
    mainContentRef.current?.focus();
    mainContentRef.current?.scrollIntoView?.({ block: "start" });
  };

  return (
    <div className="cl-shell" data-theme={viewModel.theme} aria-busy={viewModel.page_state === "processing"}>
      <a className="cl-shell__skip" href="#cl-v2-main" onClick={skipToMainContent}>
        Chuyển đến nội dung chính
      </a>

      <header className="cl-shell__header">
        <button
          type="button"
          ref={menuButtonRef}
          className="cl-shell__menu"
          aria-label={navigationOpen ? "Đóng điều hướng" : "Mở điều hướng"}
          aria-expanded={navigationOpen}
          aria-controls={navigationId}
          onClick={() => setNavigationOpen((current) => !current)}
        >
          <span aria-hidden="true">{navigationOpen ? "×" : "☰"}</span>
        </button>
        <div className="cl-shell__brand" aria-label="HUB và CreditLens">
          <img src={viewModel.logo_data_uri} alt="" className="cl-shell__logo" />
          <div className="cl-shell__brand-name">
            <strong>HUB × CreditLens</strong>
            <span>Thẩm định có thể kiểm chứng</span>
          </div>
        </div>
        <div className="cl-shell__header-status">
          <span aria-hidden="true" className="cl-shell__header-dot" />
          Quy trình xác định · Không tự động phê duyệt
        </div>
      </header>

      {navigationOpen ? (
        <button
          type="button"
          className="cl-shell__scrim"
          aria-label="Đóng điều hướng"
          onClick={closeNavigation}
        />
      ) : null}

      <aside
        id={navigationId}
        className={`cl-shell__sidebar${navigationOpen ? " is-open" : ""}`}
        aria-label="Điều hướng ứng dụng"
      >
        <nav aria-label="Điều hướng chính">
          {GROUPS.map((group) => (
            <section className="cl-shell__nav-group" aria-labelledby={`${navigationId}-${group}`} key={group}>
              <h2 id={`${navigationId}-${group}`}>{group}</h2>
              {viewModel.navigation
                .filter((item) => item.group === group)
                .map((item) => {
                  const active = item.page === viewModel.active_page;
                  return (
                    <button
                      type="button"
                      ref={active ? activeNavigationRef : undefined}
                      className={`cl-shell__nav-item${active ? " is-active" : ""}`}
                      aria-current={active ? "page" : undefined}
                      aria-label={item.label}
                      title={item.label}
                      onClick={() => selectPage(item.page)}
                      key={item.page}
                    >
                      <span className="cl-shell__nav-index" aria-hidden="true">
                        {item.ordinal}
                      </span>
                      <span className="cl-shell__nav-label">{item.label}</span>
                    </button>
                  );
                })}
            </section>
          ))}
        </nav>
        <p className="cl-shell__sidebar-note">
          Ngưỡng minh họa · Không phải chính sách ngân hàng · Bắt buộc con người xem xét
        </p>
      </aside>

      <main ref={mainContentRef} id="cl-v2-main" className="cl-shell__main" tabIndex={-1}>
        <section className={`cl-case-context cl-tone--${viewModel.case_context.status_tone}`} aria-live="polite">
          <div>
            <span className="cl-case-context__label">Hồ sơ hiện tại</span>
            <strong>{viewModel.case_context.case_id ?? "Chưa có hồ sơ đang mở"}</strong>
          </div>
          <div className="cl-case-context__meta">
            {viewModel.case_context.source ? <span>{viewModel.case_context.source}</span> : null}
            <span>{viewModel.case_context.status_label}</span>
            <span>{viewModel.case_context.summary}</span>
          </div>
        </section>

        {viewModel.overview ? (
          <>
            <section className="cl-page-header">
              <div>
                <p className="cl-page-header__eyebrow">CreditLens workspace</p>
                <h1>Tổng quan và hồ sơ</h1>
                <p>Bắt đầu từ bộ tài liệu hoặc mở một hồ sơ minh họa xác định.</p>
              </div>
              <span className="cl-page-header__badge">Không dùng LLM để mở trang</span>
            </section>

            <section className="cl-legal-alert" aria-labelledby={legalId}>
              <div aria-hidden="true" className="cl-legal-alert__icon">i</div>
              <div>
                <strong id={legalId}>Dữ liệu chỉ được dùng trong phiên hiện tại</strong>
                <p>CreditLens hỗ trợ thẩm định; quyết định cuối cùng thuộc cán bộ tín dụng.</p>
                <details>
                  <summary>Xem nguyên tắc sử dụng</summary>
                  <p>
                    Không tải dữ liệu ngân hàng thật hoặc thông tin mật vào bản minh họa công khai. Hệ thống không tự
                    phê duyệt hoặc từ chối khoản vay.
                  </p>
                </details>
              </div>
            </section>

            <section className={`cl-page-state cl-page-state--${viewModel.page_state}`} role={viewModel.page_state === "error" ? "alert" : "status"}>
              <strong>{PAGE_STATE_LABELS[viewModel.page_state]}</strong>
              <span>{viewModel.state_message}</span>
            </section>

            <section className="cl-workflow" aria-labelledby="cl-workflow-title">
              <div className="cl-section-heading">
                <div>
                  <p className="cl-page-header__eyebrow">Luồng xử lý</p>
                  <h2 id="cl-workflow-title">Quy trình thẩm định</h2>
                </div>
                <span>Python cung cấp trạng thái</span>
              </div>
              <ol>
                {viewModel.workflow.map((step, index) => (
                  <li className={`cl-workflow__step cl-workflow__step--${step.state}`} key={step.key}>
                    <span className="cl-workflow__marker" aria-hidden="true">
                      {step.state === "upcoming" ? index + 1 : STEP_ICONS[step.state]}
                    </span>
                    <div>
                      <strong>{step.label}</strong>
                      <p>{step.description}</p>
                      <span className="cl-workflow__status" aria-current={step.state === "current" ? "step" : undefined}>
                        {step.status_label}
                      </span>
                    </div>
                  </li>
                ))}
              </ol>
            </section>

            <section className="cl-process" aria-labelledby="cl-process-title">
              <div className="cl-section-heading">
                <h2 id="cl-process-title">Các chặng xử lý</h2>
              </div>
              <div className="cl-process__grid">
                {viewModel.process_cards.map((card, index) => (
                  <article className={`cl-process-card cl-process-card--${card.state}`} key={card.key}>
                    <div className="cl-process-card__topline">
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <span>{card.state === "complete" ? "Hoàn tất" : card.state === "current" ? "Hiện tại" : card.state === "warning" ? "Cần xem xét" : card.state === "error" ? "Có lỗi" : "Sắp tới"}</span>
                    </div>
                    <h3>{card.label}</h3>
                    <p>{card.description}</p>
                  </article>
                ))}
              </div>
            </section>
          </>
        ) : null}
      </main>
    </div>
  );
}
