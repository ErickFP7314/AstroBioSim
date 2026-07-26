import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
// El backend FastAPI corre en :8000. Proxyeamos /api (HTTP y WebSocket) para que
// el frontend use rutas relativas y no haya problemas de CORS/origen en dev.
export default defineConfig({
    plugins: [react()],
    server: {
        port: 5173,
        proxy: {
            "/api": {
                target: "http://localhost:8000",
                changeOrigin: true,
                ws: true,
            },
        },
    },
});
