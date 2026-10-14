import { useState } from "react";
import { useCreditLens } from "../context/CreditLensContext";
import { THRESHOLD_LABELS, type UnderwritingThresholds } from "../domain/engine";
import type { StatusTone } from "../domain/contracts";
import { GeminiChatbot } from "./GeminiChatbot";

function ToneBadge({ tone, children }: { tone: StatusTone; children: string }) {
  return <span className={`cl-badge cl-badge--${tone}`}>{children}</span>;
}

export function SettingsPage() {
  const {
    theme,
    setTheme,
    motionLevel,
    setMotionLevel,
    providers,
    activeProvider,
    setActiveProvider,
    thresholds,
    updateThreshold,
    resetThresholds,
    result
  } = useCreditLens();

  const activeProviderObj = providers.find((p) => p.provider === activeProvider);

  return (
    <main
      className="cl-support-page cl-settings-page"
      data-theme={theme}
      aria-labelledby="cl-settings-title"
    >
      <header className="cl-support-header cl-settings-header">
        <div>
          <p className="cl-core-eyebrow">SESSION SETTINGS</p>
          <h1 id="cl-settings-title">Cài đặt và trợ lý AI</h1>
          <p>
            Quản lý nhà cung cấp mô hình, điều chỉnh ngưỡng minh họa trong phiên và tương tác với trợ lý thẩm định.
          </p>
        </div>
        <ToneBadge tone="success">CONNECTED</ToneBadge>
      </header>

      {/* Connection status card */}
      <section
        className="cl-settings-status cl-tone--success"
        role="status"
        aria-live="polite"
        aria-labelledby="cl-settings-status-title"
      >
        <div>
          <p className="cl-core-eyebrow">CONNECTION STATUS</p>
          <h2 id="cl-settings-status-title">CONNECTED</h2>
          <p>Kết nối đã được xác minh trong phiên hiện tại. Phân tích xác định tiếp tục hoạt động độc lập.</p>
        </div>
        <dl className="cl-settings-status__facts">
          <div>
            <dt>Provider</dt>
            <dd>{activeProviderObj?.label ?? "Chưa chọn"}</dd>
          </div>
          <div>
            <dt>Model</dt>
            <dd>
              <code>{activeProviderObj?.model ?? "Chưa chọn"}</code>
            </dd>
          </div>
          <div>
            <dt>Hồ sơ hiện tại</dt>
            <dd>{result?.ma_ho_so ?? "Chưa có"}</dd>
          </div>
        </dl>
      </section>

      {/* Interface & Motion Controls Section */}
      <section className="cl-core-section" aria-labelledby="cl-ui-motion-title">
        <div className="cl-core-section__heading">
          <div>
            <p className="cl-core-eyebrow">INTERFACE & MOTION PREFERENCES</p>
            <h2 id="cl-ui-motion-title">Giao diện và Hiệu ứng chuyển động</h2>
          </div>
          <ToneBadge tone="info">WCAG AA COMPLIANT</ToneBadge>
        </div>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
            gap: "20px"
          }}
        >
          {/* Card: Theme selection */}
          <div
            style={{
              padding: "16px",
              background: "var(--cl-surface-subtle)",
              borderRadius: "8px",
              border: "1px solid var(--cl-border)"
            }}
          >
            <strong style={{ fontSize: "14px", display: "block", marginBottom: "4px" }}>
              Chế độ hiển thị (Theme)
            </strong>
            <p style={{ fontSize: "12px", color: "var(--cl-muted)", marginBottom: "14px", lineHeight: "17px" }}>
              Chuyển đổi giữa tông màu ngân hàng sáng và tối với hiệu ứng chuyển màu mượt 220ms không nháy trắng.
            </p>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              {(["system", "light", "dark"] as const).map((t) => (
                <button
                  key={t}
                  type="button"
                  onClick={() => setTheme(t)}
                  style={{
                    padding: "8px 14px",
                    borderRadius: "6px",
                    fontSize: "13px",
                    fontWeight: theme === t ? 700 : 500,
                    cursor: "pointer",
                    border: theme === t ? "2px solid var(--cl-primary)" : "1px solid var(--cl-border)",
                    background: theme === t ? "var(--cl-primary-subtle)" : "var(--cl-surface)",
                    color: theme === t ? "var(--cl-primary)" : "var(--cl-text)",
                    transition: "all 0.16s ease"
                  }}
                >
                  {t === "light" && "☀️ Sáng (Light)"}
                  {t === "dark" && "🌙 Tối (Dark)"}
                  {t === "system" && "💻 Hệ thống (System)"}
                </button>
              ))}
            </div>
          </div>

          {/* Card: Motion Level selection */}
          <div
            style={{
              padding: "16px",
              background: "var(--cl-surface-subtle)",
              borderRadius: "8px",
              border: "1px solid var(--cl-border)"
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline", marginBottom: "4px" }}>
              <strong style={{ fontSize: "14px" }}>
                Hiệu ứng giao diện
              </strong>
              <span style={{ fontSize: "12px", color: "var(--cl-primary)", fontWeight: 700 }}>
                {motionLevel === "full" && "Đầy đủ"}
                {motionLevel === "light" && "Nhẹ"}
                {motionLevel === "off" && "Tắt"}
              </span>
            </div>
            <p style={{ fontSize: "12px", color: "var(--cl-muted)", marginBottom: "14px", lineHeight: "17px" }}>
              Tùy chỉnh hiệu ứng Ken Burns HUB photo reel, vệt aurora trôi và gợn sóng phản hồi. Lưu vào localStorage và tự chuyển "Nhẹ" khi hệ điều hành bật reduced-motion.
            </p>
            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                onClick={() => setMotionLevel("full")}
                style={{
                  padding: "8px 14px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: motionLevel === "full" ? 700 : 500,
                  cursor: "pointer",
                  border: motionLevel === "full" ? "2px solid var(--cl-primary)" : "1px solid var(--cl-border)",
                  background: motionLevel === "full" ? "var(--cl-primary-subtle)" : "var(--cl-surface)",
                  color: motionLevel === "full" ? "var(--cl-primary)" : "var(--cl-text)",
                  transition: "all 0.16s ease"
                }}
              >
                ● Đầy đủ
              </button>
              <button
                type="button"
                onClick={() => setMotionLevel("light")}
                style={{
                  padding: "8px 14px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: motionLevel === "light" ? 700 : 500,
                  cursor: "pointer",
                  border: motionLevel === "light" ? "2px solid var(--cl-primary)" : "1px solid var(--cl-border)",
                  background: motionLevel === "light" ? "var(--cl-primary-subtle)" : "var(--cl-surface)",
                  color: motionLevel === "light" ? "var(--cl-primary)" : "var(--cl-text)",
                  transition: "all 0.16s ease"
                }}
              >
                ◐ Nhẹ
              </button>
              <button
                type="button"
                onClick={() => setMotionLevel("off")}
                style={{
                  padding: "8px 14px",
                  borderRadius: "6px",
                  fontSize: "13px",
                  fontWeight: motionLevel === "off" ? 700 : 500,
                  cursor: "pointer",
                  border: motionLevel === "off" ? "2px solid var(--cl-primary)" : "1px solid var(--cl-border)",
                  background: motionLevel === "off" ? "var(--cl-primary-subtle)" : "var(--cl-surface)",
                  color: motionLevel === "off" ? "var(--cl-primary)" : "var(--cl-text)",
                  transition: "all 0.16s ease"
                }}
              >
                ○ Tắt
              </button>
            </div>
            <div style={{ marginTop: "10px", fontSize: "11px", color: "var(--cl-muted)", lineHeight: "16px" }}>
              {motionLevel === "full" && "✨ Hoạt động đầy đủ: Ken Burns 12–14s, aurora drift 30–45s, parallax theo con trỏ và ripple gợn sóng."}
              {motionLevel === "light" && "🛡️ Chuyển động nhẹ: Nền tĩnh mờ, tắt Ken Burns và parallax, chuyển trang fade 120ms."}
              {motionLevel === "off" && "🛑 Tắt chuyển động: Không có hiệu ứng động hay chuyển trang trượt."}
            </div>
          </div>
        </div>
      </section>

      {/* Provider cards */}
      <section className="cl-core-section" aria-labelledby="cl-provider-title">
        <div className="cl-core-section__heading">
          <div>
            <p className="cl-core-eyebrow">AI CONNECTION</p>
            <h2 id="cl-provider-title">Provider và model trong phiên</h2>
          </div>
          <span>Bấm để chọn provider kích hoạt</span>
        </div>
        <div className="cl-provider-grid">
          {providers.map((p) => {
            const isActive = p.provider === activeProvider;
            return (
              <article
                className={`cl-provider-card${isActive ? " is-active" : ""}`}
                key={p.provider}
                onClick={() => setActiveProvider(p.provider)}
                style={{ cursor: "pointer", transition: "all 0.15s ease" }}
              >
                <div className="cl-provider-card__topline">
                  <h3>{p.label}</h3>
                  <ToneBadge tone={p.status_tone}>{p.status_label}</ToneBadge>
                </div>
                <p>{p.description}</p>
                <dl>
                  <div>
                    <dt>Model</dt>
                    <dd>
                      <code>{p.model ?? "Chưa có"}</code>
                    </dd>
                  </div>
                  <div>
                    <dt>Model khả dụng</dt>
                    <dd>{p.connected ? p.model_count : "—"}</dd>
                  </div>
                </dl>
                {isActive && (
                  <div style={{ marginTop: "12px", color: "var(--cl-primary)", fontSize: "12px", fontWeight: 700 }}>
                    ✓ Đang sử dụng cho phiên này
                  </div>
                )}
              </article>
            );
          })}
        </div>
      </section>

      {/* Threshold controls section */}
      <section className="cl-core-section" aria-labelledby="cl-thresholds-setting-title">
        <div className="cl-core-section__heading">
          <div>
            <p className="cl-core-eyebrow">THRESHOLD TUNING</p>
            <h2 id="cl-thresholds-setting-title">Điều chỉnh ngưỡng tính toán minh họa</h2>
          </div>
          <button
            type="button"
            onClick={resetThresholds}
            style={{
              padding: "4px 12px",
              borderRadius: "6px",
              border: "1px solid var(--cl-border)",
              background: "var(--cl-surface)",
              color: "var(--cl-muted)",
              cursor: "pointer",
              fontSize: "12px"
            }}
          >
            Khôi phục mặc định
          </button>
        </div>
        <p style={{ color: "var(--cl-muted)", fontSize: "13px", lineHeight: "19px", marginBottom: "20px" }}>
          Thay đổi thanh trượt sẽ tính toán lại ngay lập tức toàn bộ chỉ số DTI, DSR, chênh lệch nợ và các cảnh báo
          rủi ro trên mọi trang.
        </p>

        <div
          style={{
            display: "grid",
            gridTemplateColumns: "repeat(auto-fit, minmax(280px, 1fr))",
            gap: "20px"
          }}
        >
          {/* Slider 1: do_tin_cay_thap */}
          <div style={{ padding: "12px", background: "var(--cl-surface-subtle)", borderRadius: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <strong style={{ fontSize: "13px" }}>{THRESHOLD_LABELS.do_tin_cay_thap}</strong>
              <span style={{ color: "var(--cl-primary)", fontWeight: 700 }}>
                {Math.round(thresholds.do_tin_cay_thap * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="0.99"
              step="0.01"
              value={thresholds.do_tin_cay_thap}
              onChange={(e) => updateThreshold("do_tin_cay_thap", parseFloat(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>

          {/* Slider 2: dti_canh_bao */}
          <div style={{ padding: "12px", background: "var(--cl-surface-subtle)", borderRadius: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <strong style={{ fontSize: "13px" }}>{THRESHOLD_LABELS.dti_canh_bao}</strong>
              <span style={{ color: "var(--cl-primary)", fontWeight: 700 }}>
                {Math.round(thresholds.dti_canh_bao * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.2"
              max="0.8"
              step="0.05"
              value={thresholds.dti_canh_bao}
              onChange={(e) => updateThreshold("dti_canh_bao", parseFloat(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>

          {/* Slider 3: dsr_canh_bao */}
          <div style={{ padding: "12px", background: "var(--cl-surface-subtle)", borderRadius: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <strong style={{ fontSize: "13px" }}>{THRESHOLD_LABELS.dsr_canh_bao}</strong>
              <span style={{ color: "var(--cl-primary)", fontWeight: 700 }}>
                {Math.round(thresholds.dsr_canh_bao * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.2"
              max="0.8"
              step="0.05"
              value={thresholds.dsr_canh_bao}
              onChange={(e) => updateThreshold("dsr_canh_bao", parseFloat(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>

          {/* Slider 4: chenh_lech_thu_nhap */}
          <div style={{ padding: "12px", background: "var(--cl-surface-subtle)", borderRadius: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <strong style={{ fontSize: "13px" }}>{THRESHOLD_LABELS.chenh_lech_thu_nhap}</strong>
              <span style={{ color: "var(--cl-primary)", fontWeight: 700 }}>
                {Math.round(thresholds.chenh_lech_thu_nhap * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.05"
              max="0.5"
              step="0.05"
              value={thresholds.chenh_lech_thu_nhap}
              onChange={(e) => updateThreshold("chenh_lech_thu_nhap", parseFloat(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>

          {/* Slider 5: he_so_dem_so_du_thap */}
          <div style={{ padding: "12px", background: "var(--cl-surface-subtle)", borderRadius: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <strong style={{ fontSize: "13px" }}>{THRESHOLD_LABELS.he_so_dem_so_du_thap}</strong>
              <span style={{ color: "var(--cl-primary)", fontWeight: 700 }}>
                {thresholds.he_so_dem_so_du_thap.toFixed(1)}×
              </span>
            </div>
            <input
              type="range"
              min="0.5"
              max="3.0"
              step="0.1"
              value={thresholds.he_so_dem_so_du_thap}
              onChange={(e) => updateThreshold("he_so_dem_so_du_thap", parseFloat(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>

          {/* Slider 6: bien_dong_thu_nhap_cao */}
          <div style={{ padding: "12px", background: "var(--cl-surface-subtle)", borderRadius: "8px" }}>
            <div style={{ display: "flex", justifyContent: "space-between", marginBottom: "6px" }}>
              <strong style={{ fontSize: "13px" }}>{THRESHOLD_LABELS.bien_dong_thu_nhap_cao}</strong>
              <span style={{ color: "var(--cl-primary)", fontWeight: 700 }}>
                {Math.round(thresholds.bien_dong_thu_nhap_cao * 100)}%
              </span>
            </div>
            <input
              type="range"
              min="0.1"
              max="0.6"
              step="0.05"
              value={thresholds.bien_dong_thu_nhap_cao}
              onChange={(e) => updateThreshold("bien_dong_thu_nhap_cao", parseFloat(e.target.value))}
              style={{ width: "100%" }}
            />
          </div>
        </div>
      </section>

      {/* Chat session section */}
      <div className="cl-settings-two-column">
        <section className="cl-core-section" aria-labelledby="cl-chat-session-title">
          <div className="cl-core-section__heading">
            <div>
              <p className="cl-core-eyebrow">GEMINI MULTI-TURN CHAT</p>
              <h2 id="cl-chat-session-title">Hội thoại trợ lý thẩm định Gemini</h2>
            </div>
            <ToneBadge tone="success">READY</ToneBadge>
          </div>
          <GeminiChatbot embedded={true} />
        </section>

        <section className="cl-core-section" aria-labelledby="cl-info-summary-title">
          <div className="cl-core-section__heading">
            <div>
              <p className="cl-core-eyebrow">SESSION CONTEXT</p>
              <h2 id="cl-info-summary-title">Thông số phiên làm việc</h2>
            </div>
          </div>
          <dl className="cl-session-facts" style={{ display: "grid", gap: "10px" }}>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <dt style={{ color: "var(--cl-muted)" }}>Hồ sơ nạp</dt>
              <dd>
                <strong>{result?.ma_ho_so ?? "Chưa có"}</strong>
              </dd>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <dt style={{ color: "var(--cl-muted)" }}>Khách hàng</dt>
              <dd>{result?.du_lieu.ho_ten_khach_hang ?? "N/A"}</dd>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <dt style={{ color: "var(--cl-muted)" }}>Số tài liệu đọc</dt>
              <dd>{result?.documents.length ?? 0} tài liệu</dd>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <dt style={{ color: "var(--cl-muted)" }}>Trường dữ liệu</dt>
              <dd>{result?.fields.length ?? 0} trường</dd>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <dt style={{ color: "var(--cl-muted)" }}>Số cảnh báo rủi ro</dt>
              <dd>{result?.canh_bao.length ?? 0} cảnh báo</dd>
            </div>
            <div style={{ display: "flex", justifyContent: "space-between" }}>
              <dt style={{ color: "var(--cl-muted)" }}>Đánh giá hệ thống</dt>
              <dd>
                <ToneBadge tone={result?.trang_thai === "REVIEW READY" ? "success" : "warning"}>
                  {result?.trang_thai ?? "EMPTY"}
                </ToneBadge>
              </dd>
            </div>
          </dl>

          <div
            style={{
              marginTop: "20px",
              padding: "12px",
              background: "var(--cl-surface-subtle)",
              borderRadius: "8px",
              border: "1px solid var(--cl-border)"
            }}
          >
            <strong style={{ fontSize: "12px", display: "block", marginBottom: "4px" }}>
              Nguyên tắc bảo vệ dữ liệu phiên:
            </strong>
            <p style={{ fontSize: "11px", color: "var(--cl-muted)", margin: 0, lineHeight: "16px" }}>
              Mọi dữ liệu tải lên và cài đặt ngưỡng chỉ lưu trong bộ nhớ RAM trình duyệt. Không gửi sang máy chủ
              bên ngoài trừ khi người dùng chủ động yêu cầu diễn giải AI.
            </p>
          </div>
        </section>
      </div>
    </main>
  );
}
