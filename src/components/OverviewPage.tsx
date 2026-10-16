import { useState, useId, useRef } from "react";
import { useCreditLens } from "../context/CreditLensContext";
import { collectFromDataTransfer, withRelativePath } from "../lib/folderUpload";
import type { WorkflowState } from "../domain/contracts";

const STEP_ICONS: Record<WorkflowState, string> = {
  upcoming: "·",
  current: "→",
  complete: "✓",
  warning: "!",
  error: "×"
};

export function OverviewPage() {
  const {
    demoCases,
    selectedDemoCase,
    setSelectedDemoCase,
    openDemoCase,
    caseContext,
    workflowSteps,
    processCards,
    handleFileUpload,
    result,
    setActivePage,
    serverMode
  } = useCreditLens();

  const [uploading, setUploading] = useState(false);
  const [dragActive, setDragActive] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);
  const folderInputRef = useRef<HTMLInputElement>(null);
  const selectId = useId();

  const selectedCaseObj = demoCases.find((c) => c.case_name === selectedDemoCase) ?? demoCases[0];

  const onFileChange = async (e: React.ChangeEvent<HTMLInputElement>) => {
    if (!e.target.files || e.target.files.length === 0) return;
    setUploading(true);
    await handleFileUpload(e.target.files);
    setUploading(false);
  };

  const handleDrop = async (e: React.DragEvent) => {
    e.preventDefault();
    setDragActive(false);
    if (serverMode) {
      // Bản Streamlit: hỗ trợ kéo-thả CẢ THƯ MỤC (đọc đệ quy thư mục con); lọc PDF ở StreamlitContext.
      const pending = collectFromDataTransfer(e.dataTransfer);
      setUploading(true);
      const collected = await pending;
      if (collected.length) await handleFileUpload(collected.map(withRelativePath));
      setUploading(false);
      return;
    }
    if (e.dataTransfer.files && e.dataTransfer.files.length > 0) {
      setUploading(true);
      await handleFileUpload(e.dataTransfer.files);
      setUploading(false);
    }
  };

  return (
    <div className="cl-overview-container" style={{ display: "grid", gap: "24px" }}>
      <section className="cl-page-header">
        <div>
          <p className="cl-page-header__eyebrow">Đánh giá tín dụng vay</p>
          <h1>Tổng quan và hồ sơ</h1>
          <p>Bắt đầu từ bộ tài liệu hoặc mở một hồ sơ minh họa xác định.</p>
        </div>
        <span className="cl-page-header__badge">Không dùng LLM để mở trang</span>
      </section>

      <section className="cl-legal-alert" aria-label="Nguyên tắc an toàn">
        <div aria-hidden="true" className="cl-legal-alert__icon">
          i
        </div>
        <div>
          <strong>Dữ liệu chỉ được dùng trong phiên hiện tại</strong>
          <p>Hệ thống hỗ trợ thẩm định; quyết định cuối cùng thuộc cán bộ tín dụng.</p>
          <details>
            <summary>Xem nguyên tắc sử dụng</summary>
            <p>
              Không tải dữ liệu ngân hàng thật hoặc thông tin mật vào bản minh họa công khai. Hệ thống không tự
              phê duyệt hoặc từ chối khoản vay.
            </p>
          </details>
        </div>
      </section>

      <section
        className={`cl-page-state cl-page-state--${result ? "success" : "empty"}`}
        role="status"
      >
        <strong>{result ? "Hồ sơ đã sẵn sàng" : "Chưa có hồ sơ"}</strong>
        <span>
          {result
            ? `Đã nạp hồ sơ ${result.ma_ho_so}: ${result.ten_ho_so}`
            : "Chưa có hồ sơ đang mở. Vui lòng mở hồ sơ minh họa bên dưới hoặc tải lên tệp PDF."}
        </span>
      </section>

      {/* Intake workspace: Upload & Demo cases */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(320px, 1fr))",
          gap: "24px",
          alignItems: "stretch"
        }}
      >
        {/* Upload panel */}
        <section
          className="cl-core-section"
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between"
          }}
        >
          <div>
            <div className="cl-core-section__heading">
              <div>
                <p className="cl-core-eyebrow">TIẾP NHẬN TÀI LIỆU</p>
                <h2>Bộ hồ sơ tài liệu</h2>
              </div>
              <span>Hỗ trợ tải 3-4 tệp PDF</span>
            </div>
            <p style={{ color: "var(--cl-muted)", fontSize: "14px", lineHeight: "20px", marginBottom: "16px" }}>
              Tải lên đơn vay, chứng từ thu nhập, sao kê ngân hàng và nghĩa vụ nợ để pipeline trích xuất tự động.
            </p>

            <div
              onDragOver={(e) => {
                e.preventDefault();
                setDragActive(true);
              }}
              onDragLeave={() => setDragActive(false)}
              onDrop={handleDrop}
              onClick={() => fileInputRef.current?.click()}
              style={{
                border: dragActive ? "2px dashed var(--cl-primary)" : "2px dashed var(--cl-border-strong)",
                borderRadius: "10px",
                padding: "28px 16px",
                textAlign: "center",
                background: dragActive ? "var(--cl-surface-muted)" : "var(--cl-surface-subtle)",
                cursor: "pointer",
                transition: "all 0.2s ease"
              }}
            >
              <input
                ref={fileInputRef}
                type="file"
                multiple
                accept={serverMode ? ".pdf" : ".pdf,.json,.txt"}
                onChange={onFileChange}
                style={{ display: "none" }}
              />
              {serverMode ? (
                <input
                  ref={folderInputRef}
                  type="file"
                  multiple
                  data-testid="cl-folder-input"
                  {...({ webkitdirectory: "", directory: "" } as Record<string, string>)}
                  onChange={onFileChange}
                  onClick={(e) => e.stopPropagation()}
                  style={{ display: "none" }}
                />
              ) : null}
              <div style={{ fontSize: "28px", marginBottom: "8px" }}>📄</div>
              <strong style={{ display: "block", color: "var(--cl-text)", marginBottom: "4px" }}>
                {uploading
                  ? "Đang xử lý tệp..."
                  : serverMode
                  ? "Kéo thả cả thư mục hồ sơ hoặc PDF vào đây"
                  : "Kéo thả PDF vào đây hoặc bấm để chọn tệp"}
              </strong>
              <span style={{ fontSize: "12px", color: "var(--cl-muted)" }}>
                Hỗ trợ tải nhiều tệp hoặc tải thư mục (Đơn vay, Thu nhập, Sao kê)
              </span>
            </div>
          </div>

          <div style={{ marginTop: "16px", display: "flex", gap: "8px", flexWrap: "wrap" }}>
            <button
              type="button"
              className="cl-demo-panel__action"
              style={{ flex: 1, minHeight: "44px" }}
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
            >
              {uploading ? "Đang xử lý..." : "Chọn tệp từ máy tính"}
            </button>
            {serverMode ? (
              <button
                type="button"
                className="cl-demo-panel__action"
                style={{ flex: 1, minHeight: "44px" }}
                onClick={() => folderInputRef.current?.click()}
                disabled={uploading}
              >
                📁 Chọn thư mục
              </button>
            ) : null}
            {result && (
              <button
                type="button"
                style={{
                  minHeight: "44px",
                  padding: "0 16px",
                  border: "1px solid var(--cl-border)",
                  borderRadius: "8px",
                  background: "var(--cl-surface)",
                  color: "var(--cl-primary)",
                  fontWeight: 600,
                  cursor: "pointer"
                }}
                onClick={() => setActivePage("2_extraction")}
              >
                Xem kết quả trích xuất →
              </button>
            )}
          </div>
        </section>

        {/* Demo case panel */}
        <section className="cl-demo-panel" aria-labelledby="cl-demo-title">
          <p className="cl-page-header__eyebrow">Luồng xác định</p>
          <h2 id="cl-demo-title">Hồ sơ minh họa</h2>
          <p className="cl-demo-panel__intro">Xem luồng sản phẩm bằng dữ liệu tổng hợp mà không gọi mô hình.</p>

          <label htmlFor={selectId} style={{ display: "block", marginBottom: "6px", fontWeight: 600, fontSize: "13px" }}>
            Chọn 1 trong 10 tình huống thử nghiệm
          </label>
          <select
            id={selectId}
            value={selectedDemoCase}
            onChange={(e) => setSelectedDemoCase(e.target.value)}
            style={{ width: "100%", marginBottom: "16px" }}
          >
            {demoCases.map((c) => (
              <option value={c.case_name} key={c.case_name}>
                {c.case_name}
              </option>
            ))}
          </select>

          {selectedCaseObj && (
            <article className="cl-demo-card">
              <span>{selectedCaseObj.case_code}</span>
              <h3>{selectedCaseObj.title}</h3>
              <p>{selectedCaseObj.description}</p>
            </article>
          )}

          <button
            type="button"
            className="cl-demo-panel__action"
            onClick={() => {
              openDemoCase(selectedDemoCase);
            }}
          >
            Mở hồ sơ minh họa
          </button>

          <div className={`cl-demo-status cl-tone--${caseContext.status_tone}`}>
            <strong>{caseContext.status_label}</strong>
            <p>{caseContext.summary}</p>
            {caseContext.case_id ? <code>{caseContext.case_id}</code> : null}
          </div>
        </section>
      </div>

      {/* Workflow Stepper */}
      <section className="cl-workflow" aria-labelledby="cl-workflow-title">
        <div className="cl-section-heading">
          <div>
            <p className="cl-page-header__eyebrow">Luồng xử lý</p>
            <h2 id="cl-workflow-title">Quy trình thẩm định</h2>
          </div>
          <span>Động cơ xác định cung cấp trạng thái</span>
        </div>
        <ol>
          {workflowSteps.map((step, index) => (
            <li className={`cl-workflow__step cl-workflow__step--${step.state}`} key={step.key}>
              <span className="cl-workflow__marker" aria-hidden="true">
                {step.state === "upcoming" ? (
                  index + 1
                ) : (
                  <span
                    className={
                      step.state === "complete"
                        ? "cl-step-complete-icon"
                        : step.state === "warning"
                        ? "cl-step-warning-icon"
                        : ""
                    }
                  >
                    {STEP_ICONS[step.state]}
                  </span>
                )}
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

      {/* Process stage cards */}
      <section className="cl-process" aria-labelledby="cl-process-title">
        <div className="cl-section-heading">
          <h2 id="cl-process-title">Các chặng xử lý</h2>
        </div>
        <div className="cl-process__grid">
          {processCards.map((card, index) => (
            <article className={`cl-process-card cl-process-card--${card.state}`} key={card.key}>
              <div className="cl-process-card__topline">
                <span>{String(index + 1).padStart(2, "0")}</span>
                <span>
                  {card.state === "complete"
                    ? "Hoàn tất"
                    : card.state === "current"
                    ? "Hiện tại"
                    : card.state === "warning"
                    ? "Cần xem xét"
                    : card.state === "error"
                    ? "Có lỗi"
                    : "Sắp tới"}
                </span>
              </div>
              <h3>{card.label}</h3>
              <p>{card.description}</p>
            </article>
          ))}
        </div>
      </section>
    </div>
  );
}
