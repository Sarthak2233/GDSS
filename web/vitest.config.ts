/// <reference types="vitest/config" />
import { defineConfig } from "vitest/config";
import path from "node:path";

// vitest uses esbuild to transpile TSX (jsx: automatic), so no extra react
// plugin dependency is required for plain component tests under jsdom.
export default defineConfig({
  esbuild: {
    jsx: "automatic",
  },
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./tests/setup.ts"],
    css: false,
  },
});
