import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "@/lib/auth/require-auth";
import { SignUpRoute } from "@/routes/sign-up";
import { SignInRoute } from "@/routes/sign-in";
import { DashboardRoute } from "@/routes/dashboard";
import { SpokespersonDetailRoute } from "@/routes/spokespeople/$id";
import { CreateSpokespersonRoute } from "@/routes/spokespeople/new";
import { TalkRoute } from "@/routes/spokespeople/talk";
import { VideoStatusRoute } from "@/routes/videos/$id";
import { WorkspaceKnowledgeRoute } from "@/routes/workspace/knowledge";
import { KnowledgeDocumentDetailRoute } from "@/routes/workspace/knowledge.$id";
import { WorkspaceAssetsRoute } from "@/routes/workspace/assets";
import { WorkspaceAssetDetailRoute } from "@/routes/workspace/assets.$id";
import { RecipeGalleryRoute } from "@/routes/recipes";
import { RecipeFormRoute } from "@/routes/recipes/$kind";
import { ImagesRoute } from "@/routes/images";
import { CompositionStatusRoute } from "@/routes/compositions/$id";
import { ConversationChatRoute } from "@/routes/conversations/$id";
import { SignatureRoute } from "@/routes/signature";
import { AboutRoute } from "@/routes/about";
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
          {/* /about is public — no auth gate. The parent-company
              identity surface is reachable from the ParentBrandChip
              in the header on every authenticated page AND from
              sign-in / sign-up. */}
          <Route path="/about" element={<AboutRoute />} />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
