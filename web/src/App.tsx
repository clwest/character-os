import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { RequireAuth } from "@/lib/auth/require-auth";
import { SignUpRoute } from "@/routes/sign-up";
import { SignInRoute } from "@/routes/sign-in";
import { DashboardRoute } from "@/routes/dashboard";
import { SpokespersonDetailRoute } from "@/routes/spokespeople/$id";
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
            path="/spokespeople/:id"
            element={
              <RequireAuth>
                <SpokespersonDetailRoute />
              </RequireAuth>
            }
          />
        </Route>
      </Routes>
    </BrowserRouter>
  );
}
