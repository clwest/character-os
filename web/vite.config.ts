import path from "node:path";
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Same-origin in production (Django serves dist/); Vite proxies the
// Django-shaped paths in dev so the SPA at :5174 talks to Django at
// :8010 transparently. Documented in
// docs/design/SPA_ARCHITECTURE.md — "Dev workflow".
//
// Port note: shifted from :8000 to :8010 (Session 1117 follow-up) so
// Character OS can run concurrently with unified-donkey-betz, which
// owns :8000 by Procfile / Makefile convention. Both apps need to be
// up at once for the consult_engine engine-bridge realtime tool to
// reach u-d-b's PA at http://localhost:8000/api/pa/chat/. See
// /Users/donkeyking/development/infra/README.md for the fleet
// host-port convention.
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
    // Port shifted to 5174 to dodge the runway-hackathon Vite dev
    // server which the operator keeps running on the default 5173.
    // Same pattern as Redis :6381 dodging session1115/unified-redis.
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
