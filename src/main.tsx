import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { CreditLensProvider } from "./context/CreditLensContext";
import App from "./App";
import "./styles.css";

const rootElement = document.getElementById("root");
if (!rootElement) {
  throw new Error("Không tìm thấy root element");
}

createRoot(rootElement).render(
  <StrictMode>
    <CreditLensProvider>
      <App />
    </CreditLensProvider>
  </StrictMode>
);
