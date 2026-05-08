import react from "@vitejs/plugin-react";
import { defineConfig } from "vitest/config";

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      "/api-gateway": {
        target: "http://localhost:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api-gateway/, ""),
      },
      "/news-service": {
        target: "http://localhost:8004",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/news-service/, ""),
      },
    },
  },
  test: {
    environment: "jsdom",
    setupFiles: ["src/test/setup.ts"],
  },
});
