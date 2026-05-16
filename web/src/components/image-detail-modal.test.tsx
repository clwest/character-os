/**
 * W11.6.4 — ImageDetailModal unit tests.
 *
 * Anchors: regenerate POSTs the original subject + same
 * params (not the composed prompt — sending the composed
 * prompt would double-apply purpose framing), delete needs
 * a confirm tap before firing, dismiss callbacks fire on
 * the right gestures, pre-W11.6.4 rows (empty subject)
 * disable Regenerate with a tooltip pointing to the
 * Generate tab.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ImageDetailModal } from "./image-detail-modal";
import type { ImageAsset } from "@/lib/api/images";

const ASSET: ImageAsset = {
  id: "img-1",
  workspace: "ws-1",
  asset_type: "image",
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
  prompt: "A detailed scene illustration of a craft brewery.",
  subject: "a craft brewery at sunrise",
  negative_prompt: "no people",
  aspect_ratio: "16:9",
  spokesperson: null,
  created_at: "2026-05-16T20:00:00Z",
};

const REGEN_RESPONSE = {
  ...ASSET,
  id: "img-2",
  prompt: "A detailed scene illustration of a craft brewery (new seed).",
};

function renderModal(props: {
  asset?: ImageAsset;
  onRegenerated?: (a: ImageAsset) => void;
  onDeleted?: () => void;
  onDismiss?: () => void;
  fetchImpl?: (url: string, init?: RequestInit) => Promise<Response>;
} = {}) {
  const onRegenerated = vi.fn(props.onRegenerated);
  const onDeleted = vi.fn(props.onDeleted);
  const onDismiss = vi.fn(props.onDismiss);
  const calls: Array<{ url: string; method: string; body: unknown }> = [];
  vi.spyOn(global, "fetch").mockImplementation((url, init) => {
    const method = (init?.method ?? "GET").toUpperCase();
    let parsedBody: unknown = undefined;
    if (init?.body) {
      try {
        parsedBody = JSON.parse(String(init.body));
      } catch {
        parsedBody = init.body;
      }
    }
    calls.push({ url: String(url), method, body: parsedBody });
    if (props.fetchImpl) return props.fetchImpl(String(url), init);
    if (method === "POST") {
      return Promise.resolve(
        new Response(JSON.stringify(REGEN_RESPONSE), {
          status: 201,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }
    if (method === "DELETE") {
      return Promise.resolve(new Response(null, { status: 204 }));
    }
    return Promise.resolve(new Response("[]", { status: 200 }));
  });
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return {
    onRegenerated,
    onDeleted,
    onDismiss,
    calls,
    ...render(
      <QueryClientProvider client={qc}>
        <ImageDetailModal
          asset={props.asset ?? ASSET}
          onRegenerated={onRegenerated}
          onDeleted={onDeleted}
          onDismiss={onDismiss}
        />
      </QueryClientProvider>,
    ),
  };
}

describe("W11.6.4 — ImageDetailModal", () => {
  beforeEach(() => {
    // fetch spy is set per-test
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders the image + key metadata", () => {
    renderModal();
    expect(screen.getByTestId("image-detail-modal")).toBeInTheDocument();
    expect(screen.getByTestId("image-detail-image")).toHaveAttribute(
      "src",
      ASSET.file_path,
    );
    expect(screen.getByText("sd3-large")).toBeInTheDocument();
    expect(screen.getByText("minimalist")).toBeInTheDocument();
  });

  it("regenerate POSTs the original subject + same params (NOT the composed prompt)", async () => {
    const { calls, onRegenerated } = renderModal();
    fireEvent.click(screen.getByTestId("image-detail-regenerate"));
    await waitFor(() => {
      const posts = calls.filter((c) => c.method === "POST");
      expect(posts.length).toBe(1);
    });
    const post = calls.find((c) => c.method === "POST");
    expect(post?.body).toMatchObject({
      workspace: "ws-1",
      purpose: "scene",
      subject: "a craft brewery at sunrise",
      model: "sd3-large",
      aspect_ratio: "16:9",
      style_preset: "minimalist",
    });
    // Critically: we send subject, NOT the composed prompt
    // (sending the composed prompt would double-apply framing).
    expect((post?.body as { subject: string }).subject).not.toContain(
      "A detailed scene illustration of",
    );
    await waitFor(() => {
      expect(onRegenerated).toHaveBeenCalledTimes(1);
    });
    expect(onRegenerated.mock.calls[0]?.[0]).toMatchObject({ id: "img-2" });
  });

  it("regenerate is disabled (with a tooltip) when subject is empty (pre-W11.6.4 row)", () => {
    renderModal({ asset: { ...ASSET, subject: "" } });
    const btn = screen.getByTestId(
      "image-detail-regenerate",
    ) as HTMLButtonElement;
    expect(btn.disabled).toBe(true);
    expect(btn.getAttribute("title")).toContain("Subject not available");
  });

  it("delete needs a confirm tap before firing DELETE", async () => {
    const { calls, onDeleted } = renderModal();
    const del = screen.getByTestId("image-detail-delete");
    fireEvent.click(del);
    // First click flips into confirm mode — no DELETE yet.
    expect(calls.some((c) => c.method === "DELETE")).toBe(false);
    expect(screen.getByTestId("image-detail-confirm-text")).toBeInTheDocument();
    // Second click confirms.
    fireEvent.click(del);
    await waitFor(() => {
      const dels = calls.filter((c) => c.method === "DELETE");
      expect(dels.length).toBe(1);
    });
    await waitFor(() => {
      expect(onDeleted).toHaveBeenCalledTimes(1);
    });
  });

  it("X dismisses without firing any action", () => {
    const { onDismiss, calls } = renderModal();
    fireEvent.click(screen.getByTestId("image-detail-dismiss"));
    expect(onDismiss).toHaveBeenCalledTimes(1);
    expect(calls.length).toBe(0);
  });

  it("renders an error banner on regenerate failure", async () => {
    renderModal({
      fetchImpl: () =>
        Promise.resolve(
          new Response(
            JSON.stringify({ error: "stability down" }),
            { status: 502 },
          ),
        ),
    });
    fireEvent.click(screen.getByTestId("image-detail-regenerate"));
    await waitFor(() => {
      expect(screen.getByTestId("image-detail-error")).toBeInTheDocument();
    });
  });
});
