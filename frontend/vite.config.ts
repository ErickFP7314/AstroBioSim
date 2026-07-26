import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// El backend FastAPI corre en :8000. Proxyeamos /api (HTTP y WebSocket) para que
// el frontend use rutas relativas y no haya problemas de CORS/origen en dev.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Si el sistema tiene pocos "file watchers" (ENOSPC), correr con
    // `VITE_POLLING=1 npm run dev` usa polling en vez de inotify (sin sudo).
    watch: process.env.VITE_POLLING ? { usePolling: true, interval: 120 } : undefined,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        ws: true,
      },
    },
  },
});
