/**
 * Images route — W11.6.3 (generate) + W11.6.4 (library).
 *
 * Sibling of /recipes in the workspace fabric nav. Two
 * sub-views surfaced via tabs:
 *   - Generate: the W11.6.3 form (model, ratio, purpose,
 *     style preset, subject).
 *   - Library: W11.6.4's ImageLibraryGrid + ImageDetailModal.
 *     Filters + regenerate + delete all live here.
 *
 * On successful generate, the route auto-switches to library
 * so the fresh image lands in front of the operator.
 * Auto-switch lives at the route level rather than the form
 * so the modal can also pop the new asset on regenerate.
 *
 * Workspace resolution mirrors the rest of the SPA — fall
 * back to ``useMe().data.default_workspace`` until the
 * Agency-tier workspace switcher lands.
 */
import { useState } from "react";
import { Link } from "react-router-dom";
import { ArrowLeft, Loader2 } from "lucide-react";
import {
  Tabs,
  TabsContent,
  TabsList,
  TabsTrigger,
} from "@/components/ui/tabs";
import { ImageGenerationForm } from "@/components/image-generation-form";
import { ImageLibraryGrid } from "@/components/image-library-grid";
import { ImageDetailModal } from "@/components/image-detail-modal";
import { useImage, type ImageAsset } from "@/lib/api/images";
import { useMe } from "@/lib/api/workspaces";

type SubView = "generate" | "library";

export function ImagesRoute() {
  const me = useMe();
  const [tab, setTab] = useState<SubView>("generate");
  const [selectedAssetId, setSelectedAssetId] = useState<string | undefined>(
    undefined,
  );
  const workspaceId = me.data?.default_workspace?.id;
  // Re-fetch via useImage when an asset is selected so the modal
  // always renders the latest server-side state (the queryCache
  // is also kept warm by useGenerateImage's onSuccess).
  const selectedAsset = useImage(selectedAssetId);

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
            <ImageLibraryGrid
              workspace={workspaceId}
              onSelect={(asset) => setSelectedAssetId(asset.id)}
            />
          </TabsContent>
        </Tabs>
      )}
      {selectedAssetId && selectedAsset.data && (
        <ImageDetailModal
          asset={selectedAsset.data}
          onRegenerated={(newAsset: ImageAsset) => {
            setSelectedAssetId(newAsset.id);
          }}
          onDeleted={() => setSelectedAssetId(undefined)}
          onDismiss={() => setSelectedAssetId(undefined)}
        />
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

