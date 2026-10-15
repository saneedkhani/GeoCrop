import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// `npm run dev` talks to the Docker stack through nginx on :8080.
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": "http://localhost:8080",
      "/tiles": "http://localhost:8080",
    },
  },
});
