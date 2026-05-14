import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "@/lib/auth/require-auth";
import { SignUpRoute } from "@/routes/sign-up";
import { SignInRoute } from "@/routes/sign-in";
import { DashboardRoute } from "@/routes/dashboard";
import { SpokespersonDetailRoute } from "@/routes/spokespeople/$id";
import { CreateSpokespersonRoute } from "@/routes/spokespeople/new";
import { MakeVideoRoute } from "@/routes/spokespeople/render";
import { VideoStatusRoute } from "@/routes/videos/$id";
import { WorkspaceKnowledgeRoute } from "@/routes/workspace/knowledge";
import { KnowledgeDocumentDetailRoute } from "@/routes/workspace/knowledge.$id";
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
            path="/spokespeople/:id/render"
            element={
              <RequireAuth>
                <MakeVideoRoute />
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
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
