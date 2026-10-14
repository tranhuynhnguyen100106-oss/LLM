import { useEffect } from "react";

export interface ToastItem {
  id: string;
  title: string;
  description?: string;
  type?: "info" | "success" | "warning";
  timestamp: number;
}

interface ToastContainerProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

export function ToastContainer({ toasts, onDismiss }: ToastContainerProps) {
  if (toasts.length === 0) return null;

  return (
    <div
      className="cl-toast-container"
      role="region"
      aria-label="Thông báo hệ thống"
      aria-live="polite"
    >
      {toasts.map((toast) => (
        <ToastCard key={toast.id} toast={toast} onDismiss={() => onDismiss(toast.id)} />
      ))}
    </div>
  );
}

function ToastCard({ toast, onDismiss }: { toast: ToastItem; onDismiss: () => void }) {
  useEffect(() => {
    const timer = setTimeout(() => {
      onDismiss();
    }, 3600);
    return () => clearTimeout(timer);
  }, [onDismiss]);

  const icons = {
    info: "ℹ",
    success: "✓",
    warning: "!"
  };

  return (
    <div className={`cl-toast-card cl-toast-card--${toast.type ?? "info"}`}>
      <span className="cl-toast-card__icon" aria-hidden="true">
        {icons[toast.type ?? "info"]}
      </span>
      <div className="cl-toast-card__content">
        <strong className="cl-toast-card__title">{toast.title}</strong>
        {toast.description ? (
          <p className="cl-toast-card__desc">{toast.description}</p>
        ) : null}
      </div>
      <button
        type="button"
        className="cl-toast-card__close"
        aria-label="Đóng thông báo"
        onClick={onDismiss}
      >
        ×
      </button>
    </div>
  );
}
