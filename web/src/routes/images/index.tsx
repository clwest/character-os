/**
 * Images route — W11.6.3 (generate sub-view).
 *
 * Sibling of /recipes in the workspace fabric nav. Two
 * sub-views surfaced via tabs:
 *   - Generate: the W11.6.3 form (model, ratio, purpose,
 *     style preset, subject).
 *   - Library: simple recent-images list. W11.6.4 expands
 *     this with filters + regenerate + delete; for v1 of
 *     this slice we render a minimal grid so operators
 *     can confirm their newly-generated image landed.
 *
 * Workspace resolution mirrors the rest of the SPA — fall
 * back to ``useMe().data.default_workspace`` until the
 * Agency-tier workspace switcher lands.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Image as ImageIcon, Loader2 } from "lucide-react";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { ImageGenerationForm } from "@/components/image-generation-form";
import { useImages } from "@/lib/api/images";
import { useMe } from "@/lib/api/workspaces";

type SubView = "generate" | "library";

export function ImagesRoute() {
  const me = useMe();
  const [tab, setTab] = useState<SubView>("generate");
  const workspaceId = me.data?.default_workspace?.id;

  return (
    <div
      className="flex flex-col gap-8 py-10"
      data-testid="images-route"
    >
      <Header />
      {!workspaceId && me.isLoading && <LoadingState />}
      {!workspaceId && !me.isLoading && <NoWorkspaceState />}
      {workspaceId && (
        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as SubView)}
          className="flex flex-col gap-6"
        >
          <TabsList className="w-fit">
            <TabsTrigger value="generate" data-testid="images-tab-generate">
              Generate
            </TabsTrigger>
            <TabsTrigger value="library" data-testid="images-tab-library">
              Library
            </TabsTrigger>
          </TabsList>
          <TabsContent value="generate" className="flex flex-col gap-6">
            <ImageGenerationForm
              workspace={workspaceId}
              onGenerated={() => setTab("library")}
            />
          </TabsContent>
          <TabsContent value="library" className="flex flex-col gap-6">
            <LibraryPreview workspace={workspaceId} />
          </TabsContent>
        </Tabs>
      )}
    </div>
  );
}

function Header() {
  return (
    <header className="flex flex-col gap-3">
      <Link
        to="/dashboard"
        className="inline-flex w-fit items-center gap-1 font-mono text-[11px] uppercase tracking-[0.22em] text-muted-foreground transition-colors hover:text-foreground"
      >
        <ArrowLeft className="h-3 w-3" />
        Back to dashboard
      </Link>
      <div className="flex flex-col gap-2">
        <span className="text-[11px] uppercase tracking-[0.22em] text-muted-foreground">
          Workspace images
        </span>
        <h1 className="font-display text-4xl leading-tight tracking-tight">
          Generate hero shots, b-roll, products, and ad visuals.
        </h1>
        <p className="max-w-2xl text-muted-foreground">
          Powered by Stability AI. Pick a purpose, describe the subject,
          choose a style — the system composes the rest. Spokespeople
          still bake through the wizard.
        </p>
      </div>
    </header>
  );
}

function LoadingState() {
  return (
    <div className="flex items-center gap-2 text-sm text-muted-foreground">
      <Loader2 className="h-4 w-4 animate-spin" />
      Loading your workspace…
    </div>
  );
}

function NoWorkspaceState() {
  return (
    <div className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive">
      We couldn't resolve your default workspace. Try refreshing or
      sign in again.
    </div>
  );
}

function LibraryPreview({ workspace }: { workspace: string }) {
  const images = useImages({ workspace });

  if (images.isLoading) {
    return (
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Loader2 className="h-4 w-4 animate-spin" />
        Loading library…
      </div>
    );
  }

  if (images.isError) {
    return (
      <div
        data-testid="images-library-error"
        className="rounded-md border border-destructive/40 bg-destructive/5 p-4 text-sm text-destructive"
      >
        Couldn't load your image library. Try again in a moment.
      </div>
    );
  }

  const data = images.data ?? [];
  if (!data.length) {
    return (
      <div
        data-testid="images-library-empty"
        className="flex flex-col items-start gap-2 rounded-md border border-dashed border-border p-6 text-sm text-muted-foreground"
      >
        <ImageIcon className="h-5 w-5" />
        <p>
          No images in this workspace yet. Switch to the Generate tab to
          create your first one.
        </p>
      </div>
    );
  }

  return (
    <div
      data-testid="images-library-grid"
      className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3"
    >
      {data.map((asset) => (
        <article
          key={asset.id}
          data-testid={`image-card-${asset.id}`}
          className="flex flex-col gap-2 rounded-md border border-border bg-card p-3"
        >
          <img
            src={asset.file_path}
            alt={asset.prompt.slice(0, 120)}
            className="w-full rounded-sm border border-border"
          />
          <div className="flex flex-wrap items-baseline justify-between gap-2 text-[11px] uppercase tracking-[0.18em] text-muted-foreground">
            <span>{asset.purpose}</span>
            <span>
              {asset.model} · {asset.aspect_ratio}
            </span>
          </div>
          {asset.style_preset && (
            <span className="text-xs text-muted-foreground">
              Style: {asset.style_preset}
            </span>
          )}
        </article>
      ))}
    </div>
  );
}
