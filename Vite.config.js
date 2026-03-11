import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      // Proxy all /api/* requests to FastAPI during development
      "/analysis": { target: "http://localhost:8000", changeOrigin: true },
      "/models":   { target: "http://localhost:8000", changeOrigin: true },
      "/collect":  { target: "http://localhost:8000", changeOrigin: true },
      "/sentiment":{ target: "http://localhost:8000", changeOrigin: true },
    },
  },
  build: {
    outDir: "../static",    // FastAPI serves the built dashboard from /static
    emptyOutDir: true,
  },
});