import react from "@vitejs/plugin-react";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vitest/config";

export default defineConfig({
  base: "./",
  define: {
    "process.env.NODE_ENV": JSON.stringify("production")
  },
  plugins: [react()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
    minify: "oxc",
    sourcemap: false,
    lib: {
      entry: fileURLToPath(new URL("./src/index.tsx", import.meta.url)),
      formats: ["es"],
      fileName: "creditlens-v2",
      cssFileName: "creditlens-v2"
    }
  },
  test: {
    environment: "jsdom",
    clearMocks: true
  }
});
