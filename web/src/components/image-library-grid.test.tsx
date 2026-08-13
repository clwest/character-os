/**
 * W11.6.4 — ImageLibraryGrid unit tests.
 *
 * Covers: workspace images render, filter dropdowns appear,
 * filter selection refires the query with the new params,
 * onSelect callback fires with the clicked asset, empty state
 * with vs. without active filters, clear filters control.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ImageLibraryGrid } from "./image-library-grid";

const SCENE_ASSET = {
  id: "img-scene-1",
  workspace: "ws-1",
  asset_type: "image" as const,
  file_path: "data:image/png;base64,aaaa",
  mime_type: "image/png",
  width: null,
  height: null,
  size_bytes: null,
  cost_micros: 6500,
  composition: null,
  purpose: "scene",
  model: "sd3-large",
  style_preset: "minimalist",
  prompt: "A detailed scene illustration of a brewery.",
  subject: "a craft brewery",
  negative_prompt: "",
  aspect_ratio: "16:9",
  spokesperson: null,
  created_at: "2026-05-16T20:00:00Z",
};

const BROLL_ASSET = {
  ...SCENE_ASSET,
  id: "img-broll-1",
  purpose: "broll",
  model: "core",
  style_preset: "",
  subject: "industrial city skyline",
};

function renderGrid(props: {
  onSelect?: (a: unknown) => void;
  payload?: unknown;
  fetchImpl?: (url: string) => Promise<Response>;
} = {}) {
  const onSelect = vi.fn(props.onSelect);
  const fetchUrls: string[] = [];
  vi.spyOn(global, "fetch").mockImplementation((url) => {
    fetchUrls.push(String(url));
    if (props.fetchImpl) return props.fetchImpl(String(url));
    return Promise.resolve(
      new Response(JSON.stringify(props.payload ?? [SCENE_ASSET, BROLL_ASSET]), {
        status: 200,
        headers: { "Content-Type": "application/json" },
      }),
    );
  });
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    onSelect,
    fetchUrls,
    ...render(
      <QueryClientProvider client={qc}>
        <ImageLibraryGrid workspace="ws-1" onSelect={onSelect} />
      </QueryClientProvider>,
    ),
  };
}

describe("W11.6.4 — ImageLibraryGrid", () => {
  beforeEach(() => {
    // fetch spy is set per-test in renderGrid
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a card per asset", async () => {
    renderGrid();
    await screen.findByTestId("image-card-img-scene-1");
    expect(screen.getByTestId("image-card-img-scene-1")).toBeInTheDocument();
    expect(screen.getByTestId("image-card-img-broll-1")).toBeInTheDocument();
  });

  it("renders an empty state when the workspace has no images", async () => {
    renderGrid({ payload: [] });
    const empty = await screen.findByTestId("image-library-empty");
    expect(empty).toHaveTextContent("No images in this workspace yet");
  });

  it("fires onSelect with the clicked asset", async () => {
    const { onSelect } = renderGrid();
    const card = await screen.findByTestId("image-card-img-broll-1");
    fireEvent.click(card);
    expect(onSelect).toHaveBeenCalledTimes(1);
    expect(onSelect.mock.calls[0]?.[0]).toMatchObject({
      id: "img-broll-1",
      purpose: "broll",
    });
  });

  it("changes the fetch URL when a filter selection updates", async () => {
    const { fetchUrls } = renderGrid();
    await screen.findByTestId("image-card-img-scene-1");
    fireEvent.change(screen.getByTestId("filter-purpose"), {
      target: { value: "product" },
    });
    await waitFor(() => {
      expect(
        fetchUrls.some((u) => u.includes("purpose=product")),
      ).toBe(true);
    });
  });

  it("shows the Clear filters control once a filter is active", async () => {
    renderGrid();
    await screen.findByTestId("image-card-img-scene-1");
    expect(screen.queryByTestId("filter-clear")).toBeNull();
    fireEvent.change(screen.getByTestId("filter-purpose"), {
      target: { value: "scene" },
    });
    await screen.findByTestId("filter-clear");
  });

  it("shows a filter-aware empty message when filters return nothing", async () => {
    let callCount = 0;
    renderGrid({
      fetchImpl: (_url) => {
        callCount++;
        // First call returns assets; once a filter is set, return empty.
        const body = callCount === 1 ? [SCENE_ASSET] : [];
        return Promise.resolve(
          new Response(JSON.stringify(body), { status: 200 }),
        );
      },
    });
    await screen.findByTestId("image-card-img-scene-1");
    fireEvent.change(screen.getByTestId("filter-purpose"), {
      target: { value: "product" },
    });
    const empty = await screen.findByTestId("image-library-empty");
    expect(empty).toHaveTextContent("No images match the active filters");
  });
});
