import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "@/lib/auth/require-auth";
import { SignUpRoute } from "@/routes/sign-up";
import { SignInRoute } from "@/routes/sign-in";
import { DashboardRoute } from "@/routes/dashboard";
import { SpokespersonDetailRoute } from "@/routes/spokespeople/$id";
import { CreateSpokespersonRoute } from "@/routes/spokespeople/new";
import { TalkRoute } from "@/routes/spokespeople/talk";
import { SpokespersonWelcomeRoute } from "@/routes/spokespeople/welcome";
import { SpokespersonIdentityRoute } from "@/routes/spokespeople/identity";
import { VideoStatusRoute } from "@/routes/videos/$id";
import { WorkspaceKnowledgeRoute } from "@/routes/workspace/knowledge";
import { KnowledgeDocumentDetailRoute } from "@/routes/workspace/knowledge.$id";
import { WorkspaceAssetsRoute } from "@/routes/workspace/assets";
import { WorkspaceAssetDetailRoute } from "@/routes/workspace/assets.$id";
import { WorkspaceTranscriptsRoute } from "@/routes/workspace/transcripts";
import { WorkspaceTranscriptDetailRoute } from "@/routes/workspace/transcripts.$id";
import { WorkspaceCampaignsRoute } from "@/routes/workspace/campaigns";
import { CampaignNewRoute } from "@/routes/workspace/campaigns.new";
import { CampaignDetailRoute } from "@/routes/workspace/campaigns.$id";
import { WorkspaceVideosRoute } from "@/routes/workspace/videos";
import { WorkspaceBundlesRoute } from "@/routes/workspace/bundles";
import { BundleNewRoute } from "@/routes/workspace/bundles.new";
import { BundleDetailRoute } from "@/routes/workspace/bundles.$id";
import { WorkspaceScriptsRoute } from "@/routes/workspace/scripts";
import { ScriptNewRoute } from "@/routes/workspace/scripts.new";
import { ScriptDetailRoute } from "@/routes/workspace/scripts.$id";
import { WorkspaceToolsRoute } from "@/routes/workspace/tools";
import { RecipeGalleryRoute } from "@/routes/recipes";
import { RecipeFormRoute } from "@/routes/recipes/$kind";
import { ImagesRoute } from "@/routes/images";
import { CompositionStatusRoute } from "@/routes/compositions/$id";
import { ConversationChatRoute } from "@/routes/conversations/$id";
import { SignatureRoute } from "@/routes/signature";
import { AboutRoute } from "@/routes/about";
import { BrandV3PreviewRoute } from "@/routes/_dev/brand-v3-preview";
import { ProviderStatusRoute } from "@/routes/settings/provider-status";
import { EngineConnectionsRoute } from "@/routes/settings/engine-connections";
import { BootstrapReviewRoute } from "@/routes/settings/bootstrap-review";
import { BootstrapReviewRunRoute } from "@/routes/settings/bootstrap-review/run";
import { BootstrapReviewFixtureRoute } from "@/routes/settings/bootstrap-review/fixture";
import { BootstrapReviewSlotRoute } from "@/routes/settings/bootstrap-review/slot";
import { Layout } from "@/routes/_layout";

export function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<Navigate to="/dashboard" replace />} />
          <Route path="/sign-up" element={<SignUpRoute />} />
          <Route path="/sign-in" element={<SignInRoute />} />
          <Route
            path="/dashboard"
            element={
              <RequireAuth>
                <DashboardRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/spokespeople/new"
            element={
              <RequireAuth>
                <CreateSpokespersonRoute />
              </RequireAuth>
            }
          />
          {/* Static sub-routes register before the dynamic catch-all
              so React Router doesn't swallow them as ids. */}
          <Route
            path="/spokespeople/:id/talk"
            element={
              <RequireAuth>
                <TalkRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/spokespeople/:id/welcome"
            element={
              <RequireAuth>
                <SpokespersonWelcomeRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/spokespeople/:id/identity"
            element={
              <RequireAuth>
                <SpokespersonIdentityRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/spokespeople/:id"
            element={
              <RequireAuth>
                <SpokespersonDetailRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/videos/:id"
            element={
              <RequireAuth>
                <VideoStatusRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/knowledge"
            element={
              <RequireAuth>
                <WorkspaceKnowledgeRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/knowledge/:id"
            element={
              <RequireAuth>
                <KnowledgeDocumentDetailRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/assets"
            element={
              <RequireAuth>
                <WorkspaceAssetsRoute />
              </RequireAuth>
            }
          />
          {/* A6 — per-asset detail; registers before the list so
              React Router never interprets the id as a list param. */}
          <Route
            path="/workspace/assets/:id"
            element={
              <RequireAuth>
                <WorkspaceAssetDetailRoute />
              </RequireAuth>
            }
          />
          {/* B1.5 — Transcript Miner list + detail; detail registers
              before the list route per the /assets pattern above. */}
          <Route
            path="/workspace/transcripts"
            element={
              <RequireAuth>
                <WorkspaceTranscriptsRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/transcripts/:id"
            element={
              <RequireAuth>
                <WorkspaceTranscriptDetailRoute />
              </RequireAuth>
            }
          />
          {/* B3.7 — Personalized-video campaigns. /new registers before
              the dynamic :id catch-all per the /spokespeople pattern. */}
          <Route
            path="/workspace/campaigns"
            element={
              <RequireAuth>
                <WorkspaceCampaignsRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/campaigns/new"
            element={
              <RequireAuth>
                <CampaignNewRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/campaigns/:id"
            element={
              <RequireAuth>
                <CampaignDetailRoute />
              </RequireAuth>
            }
          />
          {/* SESSION 209 — Videos library (paginated composition
              list). Detail still lives at /compositions/:id. */}
          <Route
            path="/workspace/videos"
            element={
              <RequireAuth>
                <WorkspaceVideosRoute />
              </RequireAuth>
            }
          />
          {/* B14.4 — Publish Bundles. /new registers before
              the dynamic :id catch-all per the /campaigns pattern. */}
          <Route
            path="/workspace/bundles"
            element={
              <RequireAuth>
                <WorkspaceBundlesRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/bundles/new"
            element={
              <RequireAuth>
                <BundleNewRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/bundles/:id"
            element={
              <RequireAuth>
                <BundleDetailRoute />
              </RequireAuth>
            }
          />
          {/* B2.5 — Auto-scripts. /new registers before the dynamic
              :id catch-all per the /bundles + /campaigns pattern. */}
          <Route
            path="/workspace/scripts"
            element={
              <RequireAuth>
                <WorkspaceScriptsRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/scripts/new"
            element={
              <RequireAuth>
                <ScriptNewRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/workspace/scripts/:id"
            element={
              <RequireAuth>
                <ScriptDetailRoute />
              </RequireAuth>
            }
          />
          {/* C5.1 — Non-realtime bridge invocation UI. See
              docs/design/BRIDGE_TOOLS_UI_V1.md. */}
          <Route
            path="/workspace/tools"
            element={
              <RequireAuth>
                <WorkspaceToolsRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/recipes"
            element={
              <RequireAuth>
                <RecipeGalleryRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/recipes/:kind"
            element={
              <RequireAuth>
                <RecipeFormRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/images"
            element={
              <RequireAuth>
                <ImagesRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/compositions/:id"
            element={
              <RequireAuth>
                <CompositionStatusRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/conversations/:id"
            element={
              <RequireAuth>
                <ConversationChatRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/signature"
            element={
              <RequireAuth>
                <SignatureRoute />
              </RequireAuth>
            }
          />
          {/* P1 2.3 (SESSION 220) — operator-only provider-status
              surface. Reads /api/health/providers/. Not a customer
              configuration panel. */}
          <Route
            path="/settings/provider-status"
            element={
              <RequireAuth>
                <ProviderStatusRoute />
              </RequireAuth>
            }
          />
          {/* EB.4 (S2887 side-step) — per-workspace EngineConnection
              settings panel. Wraps the DRF surface shipped in
              SESSION 217 (EB.3). Pro+ tier gated at the resolver +
              viewset + this component. Env-var fallback preserved
              in the resolver. */}
          <Route
            path="/settings/engine-connections"
            element={
              <RequireAuth>
                <EngineConnectionsRoute />
              </RequireAuth>
            }
          />
          {/* §19 Step 9.b.1 (SESSION 249) — read-only bootstrap
              human-review browser. Backend enforces operator admission
              via IsOperator (staff/superuser) on every endpoint;
              RequireAuth here is the outer session gate. Nested route
              hierarchy: runs → run → fixture → slot. No decision
              controls anywhere — that's 9.b.2+. */}
          <Route
            path="/settings/bootstrap-review"
            element={
              <RequireAuth>
                <BootstrapReviewRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/settings/bootstrap-review/:runId"
            element={
              <RequireAuth>
                <BootstrapReviewRunRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/settings/bootstrap-review/:runId/:fixtureId"
            element={
              <RequireAuth>
                <BootstrapReviewFixtureRoute />
              </RequireAuth>
            }
          />
          <Route
            path="/settings/bootstrap-review/:runId/:fixtureId/:kind/:purpose"
            element={
              <RequireAuth>
                <BootstrapReviewSlotRoute />
              </RequireAuth>
            }
          />
          {/* /about is public — no auth gate. The parent-company
              identity surface is reachable from the ParentBrandChip
              in the header on every authenticated page AND from
              sign-in / sign-up. */}
          <Route path="/about" element={<AboutRoute />} />
          {/* V3.2 (SESSION 209) — editorial primitives showcase.
              Dev-only reference page; no auth gate; no real data. */}
          <Route path="/dev/brand-v3" element={<BrandV3PreviewRoute />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
