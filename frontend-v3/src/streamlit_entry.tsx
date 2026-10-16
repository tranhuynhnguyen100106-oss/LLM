/**
 * Entry Streamlit Component v2 cho UI v3 "Đánh giá tín dụng vay".
 * Root React được giữ qua các lần rerun (chỉ render lại với view model mới) để không mất trạng thái
 * giao diện như ngăn kéo chat đang mở hay vị trí cuộn.
 */
import type { FrontendRenderer } from "@streamlit/component-v2-lib";
import { createRoot, type Root } from "react-dom/client";

import "../../src/styles.css";
import "./streamlit-host.css";
import { StreamlitApp } from "./StreamlitApp";
import { parseV3Payload, StreamlitCreditLensProvider, type V3Event } from "./StreamlitContext";

const roots = new WeakMap<Element, Root>();

const render: FrontendRenderer = ({ data, parentElement, setTriggerValue }) => {
  const mountPoint = parentElement.querySelector<HTMLElement>("[data-creditlens-v3-root]");
  if (!mountPoint) return;
  let root = roots.get(mountPoint);
  if (!root) {
    root = createRoot(mountPoint);
    roots.set(mountPoint, root);
  }
  try {
    const payload = parseV3Payload(data);
    const emit = (event: V3Event) => setTriggerValue("event", event);
    root.render(
      <StreamlitCreditLensProvider payload={payload} emit={emit}>
        <StreamlitApp payload={payload} />
      </StreamlitCreditLensProvider>
    );
  } catch {
    root.render(
      <section className="cl-render-error" role="alert">
        <h2>Không thể hiển thị UI v3</h2>
        <p>Dữ liệu component không hợp lệ. Ứng dụng sẽ dùng giao diện dự phòng.</p>
      </section>
    );
  }
  // Không unmount giữa các lần rerun: Streamlit giữ nguyên phần tử khi cùng key.
  return () => undefined;
};

export default render;
