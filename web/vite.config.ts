import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Same-origin in production (Django serves dist/); Vite proxies the
// Django-shaped paths in dev so the SPA at :5174 talks to Django at
// :8010 transparently. Documented in
// docs/design/SPA_ARCHITECTURE.md — "Dev workflow".
//
// Port note: Django binds :8010 in dev by convention so Character OS
// can run alongside other local services that may claim :8000. The
// consult_engine realtime tool reaches an external engine at whatever
// URL is set in the UDB_PA_API_URL env var — see
// `shell/apps/realtime/tools/consult_engine.py` for the contract.
//
// To start Django on :8010 explicitly:
//   python manage.py runserver 0.0.0.0:8010
const DJANGO_TARGET =
  process.env.CHARACTER_OS_DJANGO_TARGET || "http://localhost:8010";
const MEDIA_ENGINE_TARGET =
  process.env.MEDIA_ENGINE_TARGET || "http://localhost:8001";

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    // Port :5174 by convention so it coexists with other local Vite
    // servers (default 5173). Override with `--port` if needed.
    port: 5174,
    strictPort: true,
    proxy: {
      // `cookieDomainRewrite: ""` strips the domain attribute from
      // Set-Cookie headers Django sends back, so the browser stores
      // them on the SPA's origin (localhost:5174) rather than the
      // upstream (localhost:8010). Without this, `document.cookie`
      // doesn't see Django's csrftoken cookie and every POST gets
      // a 403. Same-origin in production sidesteps the whole
      // problem.
      "/api": {
        target: DJANGO_TARGET,
        changeOrigin: true,
        cookieDomainRewrite: "",
      },
      "/_allauth": {
        target: DJANGO_TARGET,
        changeOrigin: true,
        cookieDomainRewrite: "",
      },
      "/accounts": {
        target: DJANGO_TARGET,
        changeOrigin: true,
        cookieDomainRewrite: "",
      },
      "/admin": {
        target: DJANGO_TARGET,
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
        target: MEDIA_ENGINE_TARGET,
        changeOrigin: true,
      },
    },
  },
});
