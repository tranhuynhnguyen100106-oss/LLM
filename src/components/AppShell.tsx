import { useState, useRef, useEffect, useLayoutEffect, type ReactNode } from "react";
import { useCreditLens } from "../context/CreditLensContext";
import { AmbientBackground } from "./AmbientBackground";
import { ToastContainer } from "./Toast";
import { GeminiChatbot } from "./GeminiChatbot";
import type { WorkflowState } from "../domain/contracts";

interface AppShellProps {
  children: ReactNode;
}

const STEP_ICONS: Record<WorkflowState, string> = {
  upcoming: "·",
  current: "→",
  complete: "✓",
  warning: "!",
  error: "×"
};

export function AppShell({ children }: AppShellProps) {
  const {
    theme,
    setTheme,
    motionLevel,
    activePage,
    setActivePage,
    navigationItems,
    caseContext,
    clearCase,
    toasts,
    dismissToast
  } = useCreditLens();

  const [navigationOpen, setNavigationOpen] = useState(false);
  const [chatOpen, setChatOpen] = useState(false);
  const menuButtonRef = useRef<HTMLButtonElement>(null);
  const mainContentRef = useRef<HTMLElement>(null);
  const navContainerRef = useRef<HTMLElement>(null);
  const shellRef = useRef<HTMLDivElement>(null);

  // Active indicator position state
  const [indicatorStyle, setIndicatorStyle] = useState<{
    top: number;
    height: number;
    visible: boolean;
  }>({
    top: 0,
    height: 44,
    visible: false
  });

  // Calculate sliding indicator position whenever activePage changes or sidebar opens
  useLayoutEffect(() => {
    if (!navContainerRef.current) return;
    const activeBtn = navContainerRef.current.querySelector<HTMLButtonElement>(
      `.cl-shell__nav-item[data-page="${activePage}"]`
    );
    if (activeBtn) {
      const containerRect = navContainerRef.current.getBoundingClientRect();
      const btnRect = activeBtn.getBoundingClientRect();
      setIndicatorStyle({
        top: btnRect.top - containerRect.top,
        height: btnRect.height,
        visible: true
      });
    } else {
      setIndicatorStyle((prev) => ({ ...prev, visible: false }));
    }
  }, [activePage, navigationOpen]);

  // Keyboard shortcut: close on Escape
  useEffect(() => {
    const closeOnEscape = (event: KeyboardEvent) => {
      if (event.key === "Escape") {
        if (chatOpen) {
          setChatOpen(false);
          return;
        }
        if (navigationOpen) {
          setNavigationOpen(false);
          menuButtonRef.current?.focus();
        }
      }
    };
    document.addEventListener("keydown", closeOnEscape);
    return () => document.removeEventListener("keydown", closeOnEscape);
  }, [navigationOpen, chatOpen]);

  const lastCanvasRippleRef = useRef<number>(0);

  // Interaction Polish: Button Click Ripple & Empty Canvas Ripple (rate-limited 300ms)
  useEffect(() => {
    const shellEl = shellRef.current;
    if (!shellEl) return;

    const handlePointerDown = (e: MouseEvent) => {
      // Check prefers-reduced-motion or motionLevel !== 'full'
      if (
        motionLevel !== "full" ||
        window.matchMedia("(prefers-reduced-motion: reduce)").matches
      ) {
        return;
      }

      const target = e.target as HTMLElement | null;
      if (!target) return;

      const button = target.closest<HTMLElement>(
        "button, [role='button'], .cl-shell__nav-item, .cl-icon-action"
      );

      if (button && !(button as HTMLButtonElement).disabled) {
        const rect = button.getBoundingClientRect();
        const ripple = document.createElement("span");
        ripple.className = "cl-ripple";

        const diameter = Math.max(rect.width, rect.height) * 2;
        const radius = diameter / 2;
        const x = e.clientX - rect.left - radius;
        const y = e.clientY - rect.top - radius;

        ripple.style.width = `${diameter}px`;
        ripple.style.height = `${diameter}px`;
        ripple.style.left = `${x}px`;
        ripple.style.top = `${y}px`;

        button.appendChild(ripple);

        setTimeout(() => {
          ripple.remove();
        }, 480);
        return;
      }

      // Empty background click check
      const isInteractive = target.closest(
        "button, [role='button'], a, input, select, textarea, .cl-document-card, .cl-field-card, .cl-comparison-card, .cl-metric-card, .cl-risk-card, .cl-core-section, .cl-summary-card, .cl-demo-panel, .cl-session-facts, .cl-chat-messages, .cl-toast-card, .cl-table, tr, td, th"
      );

      if (!isInteractive) {
        const now = Date.now();
        if (now - lastCanvasRippleRef.current >= 300) {
          lastCanvasRippleRef.current = now;
          const bgRipple = document.createElement("div");
          bgRipple.className = "cl-ambient-canvas-ripple";
          bgRipple.style.left = `${e.clientX}px`;
          bgRipple.style.top = `${e.clientY}px`;
          document.body.appendChild(bgRipple);

          setTimeout(() => {
            bgRipple.remove();
          }, 650);
        }
      }
    };

    shellEl.addEventListener("pointerdown", handlePointerDown);
    return () => {
      shellEl.removeEventListener("pointerdown", handlePointerDown);
    };
  }, [motionLevel]);

  // Interaction Polish: Card Spotlight Tracking
  useEffect(() => {
    const shellEl = shellRef.current;
    if (!shellEl || motionLevel !== "full") return;

    // Check prefers-reduced-motion
    if (window.matchMedia("(prefers-reduced-motion: reduce)").matches) return;

    const handlePointerMove = (e: PointerEvent) => {
      const target = e.target as HTMLElement | null;
      if (!target) return;

      const card = target.closest<HTMLElement>(
        ".cl-document-card, .cl-field-card, .cl-comparison-card, .cl-metric-card, .cl-risk-card, .cl-core-section, .cl-summary-card, .cl-process__card, .cl-demo-panel, .cl-formula-card, .cl-provider-card, .cl-limitation-card, .cl-scorecard, .cl-settings-section, .cl-method-layer, .cl-human-review-panel, .cl-ai-explanation"
      );

      if (card) {
        const rect = card.getBoundingClientRect();
        const x = e.clientX - rect.left;
        const y = e.clientY - rect.top;
        card.style.setProperty("--mouse-x", `${x}px`);
        card.style.setProperty("--mouse-y", `${y}px`);
      }
    };

    shellEl.addEventListener("pointermove", handlePointerMove, { passive: true });
    return () => {
      shellEl.removeEventListener("pointermove", handlePointerMove);
    };
  }, [motionLevel]);

  const selectPage = (page: string) => {
    setActivePage(page);
    setNavigationOpen(false);
    window.scrollTo({ top: 0, behavior: "smooth" });
  };

  const groups = ["Hồ sơ", "Kiểm chứng", "Hệ thống"] as const;

  return (
    <div ref={shellRef} className="cl-shell" data-theme={theme} data-motion={motionLevel}>
      {/* YÊU CẦU 1: Layered background behind all application content */}
      <AmbientBackground theme={theme} motionLevel={motionLevel} />

      {/* Global banking-grade status notifications */}
      <ToastContainer toasts={toasts} onDismiss={dismissToast} />

      <a
        className="cl-shell__skip"
        href="#cl-v2-main"
        onClick={(e) => {
          e.preventDefault();
          mainContentRef.current?.focus();
          mainContentRef.current?.scrollIntoView({ block: "start" });
        }}
      >
        Chuyển đến nội dung chính
      </a>

      <header className="cl-shell__header">
        <button
          type="button"
          ref={menuButtonRef}
          className="cl-shell__menu"
          aria-label={navigationOpen ? "Đóng điều hướng" : "Mở điều hướng"}
          aria-expanded={navigationOpen}
          onClick={() => setNavigationOpen((cur) => !cur)}
        >
          <span aria-hidden="true">{navigationOpen ? "×" : "☰"}</span>
        </button>

        <div className="cl-shell__brand" aria-label="HUB và CreditLens">
          <img
            src="/hub-creditlens-lockup.png"
            alt="HUB CreditLens"
            className="cl-shell__logo"
            onError={(e) => {
              (e.target as HTMLImageElement).style.display = "none";
            }}
          />
          <div className="cl-shell__brand-name">
            <strong>HUB × CreditLens</strong>
            <span>Thẩm định có thể kiểm chứng</span>
          </div>
        </div>

        <div className="cl-shell__header-status">
          <span aria-hidden="true" className="cl-shell__header-dot cl-status-pulse" />
          <span>Quy trình xác định · Không tự động phê duyệt</span>
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "8px", justifySelf: "end" }}>
          {/* Theme switch buttons */}
          <div
            className="cl-theme-switcher"
            role="group"
            aria-label="Chọn giao diện"
          >
            <button
              type="button"
              className={`cl-theme-btn${theme === "light" ? " is-active" : ""}`}
              onClick={() => setTheme("light")}
              title="Giao diện Sáng (Light)"
            >
              ☀️ Sáng
            </button>
            <button
              type="button"
              className={`cl-theme-btn${theme === "dark" ? " is-active" : ""}`}
              onClick={() => setTheme("dark")}
              title="Giao diện Tối (Dark)"
            >
              🌙 Tối
            </button>
            <button
              type="button"
              className={`cl-theme-btn${theme === "system" ? " is-active" : ""}`}
              onClick={() => setTheme("system")}
              title="Theo hệ điều hành (System)"
            >
              💻 Hệ thống
            </button>
          </div>

          {/* Gemini AI Copilot header toggle */}
          <button
            type="button"
            className={`cl-theme-btn cl-gemini-header-btn${chatOpen ? " is-active" : ""}`}
            onClick={() => setChatOpen((prev) => !prev)}
            title="Mở Trợ lý Thẩm định Gemini Copilot"
            aria-expanded={chatOpen}
            aria-label="Mở Trợ lý Thẩm định Gemini"
          >
            <span className="cl-gemini-sparkle-icon" aria-hidden="true">✦</span>
            <span>Trợ lý Gemini</span>
          </button>

          {caseContext.case_id ? (
            <button
              type="button"
              className="cl-close-case-btn"
              onClick={clearCase}
              title="Đóng hồ sơ hiện hành"
            >
              Đóng hồ sơ
            </button>
          ) : null}
        </div>
      </header>

      {/* Dismiss mobile sidebar on background click */}
      {navigationOpen ? (
        <button
          type="button"
          className="cl-shell__scrim"
          aria-label="Đóng điều hướng"
          onClick={() => setNavigationOpen(false)}
        />
      ) : null}

      <aside
        className={`cl-shell__sidebar${navigationOpen ? " is-open" : ""}`}
        aria-label="Điều hướng ứng dụng"
      >
        <nav ref={navContainerRef} aria-label="Điều hướng chính" className="cl-shell__nav-container">
          {/* Sliding active indicator */}
          {indicatorStyle.visible && (
            <div
              className="cl-shell__nav-sliding-pill"
              aria-hidden="true"
              style={{
                transform: `translateY(${indicatorStyle.top}px)`,
                height: `${indicatorStyle.height}px`
              }}
            />
          )}

          {groups.map((group) => (
            <section className="cl-shell__nav-group" key={group}>
              <h2>{group}</h2>
              {navigationItems
                .filter((item) => item.group === group)
                .map((item) => {
                  const active = item.page === activePage;
                  return (
                    <button
                      type="button"
                      data-page={item.page}
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
                      <span className="cl-shell__nav-label">
                        {item.label.replace(/^\d+\.\s*/, "")}
                      </span>
                      {active && (
                        <span className="cl-shell__nav-active-glyph" aria-hidden="true">
                          •
                        </span>
                      )}
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
        <section
          className={`cl-case-context cl-tone--${caseContext.status_tone}`}
          aria-live="polite"
        >
          <div>
            <span className="cl-case-context__label">Hồ sơ hiện tại</span>
            <strong>{caseContext.case_id ?? "Chưa có hồ sơ đang mở"}</strong>
          </div>
          <div className="cl-case-context__meta">
            {caseContext.source ? <span>{caseContext.source}</span> : null}
            <span>{caseContext.status_label}</span>
            <span>{caseContext.summary}</span>
          </div>
        </section>

        {children}
      </main>

      {/* Floating Gemini Copilot Trigger (Bottom-Right) */}
      {!chatOpen && (
        <div className="cl-chat-floating-trigger">
          <button
            type="button"
            className="cl-chat-floating-btn"
            onClick={() => setChatOpen(true)}
            aria-label="Mở Trợ lý Thẩm định Gemini"
            title="Trợ lý Thẩm định Tín dụng Gemini Copilot (HUB)"
          >
            <span className="cl-chat-floating-icon" aria-hidden="true">✦</span>
            <span className="cl-chat-floating-label">Trợ lý Gemini</span>
            <span className="cl-chat-floating-pulse" aria-hidden="true" />
          </button>
        </div>
      )}

      {/* Slide-out Gemini Chatbot Drawer */}
      {chatOpen && (
        <div
          className="cl-chat-drawer-backdrop"
          onClick={() => setChatOpen(false)}
          role="presentation"
        >
          <div
            className="cl-chat-drawer-container"
            onClick={(e) => e.stopPropagation()}
            role="dialog"
            aria-modal="true"
            aria-label="Trợ lý Thẩm định Gemini"
          >
            <GeminiChatbot embedded={false} onClose={() => setChatOpen(false)} />
          </div>
        </div>
      )}
    </div>
  );
}
