import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Same-origin in production (Django serves dist/); Vite proxies the
// Django-shaped paths in dev so the SPA at :5173 talks to Django at
// :8000 transparently. Documented in
// docs/design/SPA_ARCHITECTURE.md — "Dev workflow".
export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Port shifted to 5174 to dodge the runway-hackathon Vite dev
    // server which the operator keeps running on the default 5173.
    // Same pattern as Redis :6381 dodging session1115/unified-redis.
    port: 5174,
    strictPort: true,
    proxy: {
      // `cookieDomainRewrite: ""` strips the domain attribute from
      // Set-Cookie headers Django sends back, so the browser stores
      // them on the SPA's origin (localhost:5174) rather than the
      // upstream (localhost:8000). Without this, `document.cookie`
      // doesn't see Django's csrftoken cookie and every POST gets
      // a 403. Same-origin in production sidesteps the whole
      // problem.
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
        cookieDomainRewrite: "",
      },
      "/_allauth": {
        target: "http://localhost:8000",
        changeOrigin: true,
        cookieDomainRewrite: "",
      },
      "/accounts": {
        target: "http://localhost:8000",
        changeOrigin: true,
        cookieDomainRewrite: "",
      },
      "/admin": {
        target: "http://localhost:8000",
        changeOrigin: true,
        cookieDomainRewrite: "",
      },
      // Media-engine artifacts (long_form_ad concats, composite
      // videos, audio mixes, etc.) — Asset.file_path is a
      // `/data/_internal/...` disk path on media-engine. The
      // FastAPI app mounts StaticFiles at `/data` in main.py;
      // this proxy makes those files reachable from the SPA's
      // origin so `<video src="/data/_internal/concats/x.mp4">`
      // resolves without same-origin CORS / cookie ceremony.
      "/data": {
        target: "http://localhost:8001",
        changeOrigin: true,
      },
    },
  },
});
