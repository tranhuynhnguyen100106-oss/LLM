import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

const here = (p: string) => fileURLToPath(new URL(p, import.meta.url));
const nm = here("./node_modules/");

/**
 * UI v3 = giao diện "Đánh giá tín dụng vay" (../src/components, ../src/styles.css) dùng lại nguyên vẹn,
 * đóng gói thành một Streamlit Component v2. Hai module được thay khi build cho Streamlit:
 *  - context/CreditLensContext → StreamlitContext (dữ liệu do Python cấp, không chạy engine.ts ở runtime);
 *  - lib/gemini → geminiStub (không gọi Gemini từ trình duyệt, không lưu khóa vào localStorage).
 */
export default defineConfig({
  base: "./",
  define: { "process.env.NODE_ENV": JSON.stringify("production") },
  plugins: [react()],
  resolve: {
    alias: [
      { find: /^.*\/context\/CreditLensContext$/, replacement: here("./src/StreamlitContext.tsx") },
      { find: /^.*\/lib\/gemini$/, replacement: here("./src/geminiStub.ts") },
      { find: "@original-context", replacement: here("../src/context/CreditLensContext.tsx") },
      { find: /^react-dom(\/.*)?$/, replacement: `${nm}react-dom$1` },
      { find: /^react(\/.*)?$/, replacement: `${nm}react$1` }
    ]
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
    minify: "oxc",
    sourcemap: false,
    lib: {
      entry: here("./src/streamlit_entry.tsx"),
      formats: ["es"],
      fileName: "creditlens-v3",
      cssFileName: "creditlens-v3"
    }
  },
  test: { environment: "jsdom", clearMocks: true, setupFiles: ["./tests/setup.ts"] }
});
