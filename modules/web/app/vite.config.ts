import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const proxy = process.env.VITE_API_PROXY;

export default defineConfig({
  plugins: [react()],
  server: proxy ? { proxy: { "/api": proxy } } : undefined,
  build: { outDir: "dist", sourcemap: false },
});