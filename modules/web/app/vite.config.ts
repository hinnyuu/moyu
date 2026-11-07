import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const proxy = process.env.VITE_API_PROXY;

export default defineConfig({
  plugins: [react()],
  server: {
    headers: {
      "Cross-Origin-Opener-Policy": "same-origin",
      "Cross-Origin-Embedder-Policy": "require-corp",
    },
    ...(proxy ? { proxy: { "/api": proxy } } : {}),
  },
  optimizeDeps: { exclude: ["@ffmpeg/ffmpeg", "@ffmpeg/util"] },
  build: { outDir: "dist", sourcemap: false },
});