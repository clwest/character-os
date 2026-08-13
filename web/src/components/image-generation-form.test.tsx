/**
 * W11.6.3 — ImageGenerationForm unit tests.
 *
 * Anchors the form contract: default selections match the
 * locked scope (scene / sd3-large / 16:9), hover-text appears
 * on the model + ratio + purpose pickers (Contract rule 9),
 * Submit is gated by subject presence, submit payload matches
 * the API shape, error surface renders on failure.
 *
 * The style-preset picker is shared with its own test; here
 * we let the picker mount but only assert that selections
 * thread into the POST body.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { ImageGenerationForm } from "./image-generation-form";

const STYLE_LIBRARY_PAYLOAD = {
  total_presets: 1,
  categories: [
    {
      id: "photography",
      display_name: "Photography",
      description: "",
      icon: "📷",
      presets: [
        {
          name: "photorealistic",
          display_name: "Photorealistic",
          category: "photography",
          description: "Ultra-realistic photo",
          best_for: ["corporate"],
          mood: "professional",
          example_prompt_suffix: "photorealistic",
        },
      ],
    },
  ],
};

const GENERATE_RESPONSE_OK = {
  id: "img-123",
  workspace: "ws-1",
  asset_type: "image" as const,
  file_path: "data:image/png;base64,iVBORw0KGgo=",
  mime_type: "image/png",
  width: null,
  height: null,
  size_bytes: null,
  cost_micros: 6500,
  composition: null,
  purpose: "scene",
  model: "sd3-large",
  style_preset: "",
  prompt: "A detailed scene illustration of a sunrise.",
  negative_prompt: "",
  aspect_ratio: "16:9",
  spokesperson: null,
  created_at: "2026-05-16T20:00:00Z",
};

function renderForm(props: {
  onGenerated?: (id: string) => void;
} = {}) {
  const qc = new QueryClient({
    defaultOptions: {
      queries: { retry: false },
      mutations: { retry: false },
    },
  });
  return render(
    <QueryClientProvider client={qc}>
      <ImageGenerationForm
        workspace="ws-1"
        onGenerated={props.onGenerated}
      />
    </QueryClientProvider>,
  );
}

describe("W11.6.3 — ImageGenerationForm", () => {
  let postBodies: unknown[];

  beforeEach(() => {
    postBodies = [];
    vi.spyOn(global, "fetch").mockImplementation((url, init) => {
      const u = String(url);
      if (u.includes("/api/styles/")) {
        return Promise.resolve(
          new Response(JSON.stringify(STYLE_LIBRARY_PAYLOAD), {
            status: 200,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      if (u.includes("/api/images/") && init?.method === "POST") {
        postBodies.push(JSON.parse(String(init.body)));
        return Promise.resolve(
          new Response(JSON.stringify(GENERATE_RESPONSE_OK), {
            status: 201,
            headers: { "Content-Type": "application/json" },
          }),
        );
      }
      return Promise.resolve(new Response("[]", { status: 200 }));
    });
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("defaults to scene + sd3-large + 16:9 per scope-lock", async () => {
    renderForm();
    await screen.findByTestId("image-generation-form");
    expect(screen.getByTestId("image-purpose-scene")).toHaveAttribute(
      "data-selected",
      "true",
    );
    expect(screen.getByTestId("image-model-sd3-large")).toHaveAttribute(
      "data-selected",
      "true",
    );
    expect(screen.getByTestId("image-ratio-16:9")).toHaveAttribute(
      "data-selected",
      "true",
    );
  });

  it("surfaces hint copy on every model button (Contract rule 9)", async () => {
    renderForm();
    await screen.findByTestId("image-generation-form");
    const core = screen.getByTestId("image-model-core");
    expect(core).toHaveAttribute("title", expect.stringContaining("Fastest"));
    const ultra = screen.getByTestId("image-model-ultra");
    expect(ultra).toHaveAttribute(
      "title",
      expect.stringContaining("Premium flagship"),
    );
  });

  it("surfaces hint copy on every aspect-ratio button (Contract rule 9)", async () => {
    renderForm();
    await screen.findByTestId("image-generation-form");
    const square = screen.getByTestId("image-ratio-1:1");
    expect(square).toHaveAttribute("title", expect.stringContaining("Square"));
    const cinematic = screen.getByTestId("image-ratio-21:9");
    expect(cinematic).toHaveAttribute(
      "title",
      expect.stringContaining("Cinematic"),
    );
  });

  it("omits the avatar purpose (Contract rule 2 — wizard owns it)", async () => {
    renderForm();
    await screen.findByTestId("image-generation-form");
    expect(screen.queryByTestId("image-purpose-avatar")).toBeNull();
    expect(screen.getByTestId("image-purpose-scene")).toBeInTheDocument();
    expect(screen.getByTestId("image-purpose-broll")).toBeInTheDocument();
    expect(screen.getByTestId("image-purpose-product")).toBeInTheDocument();
    expect(screen.getByTestId("image-purpose-ad")).toBeInTheDocument();
  });

  it("Submit is disabled until subject is non-empty", async () => {
    renderForm();
    const submit = (await screen.findByTestId("image-submit")) as HTMLButtonElement;
    expect(submit.disabled).toBe(true);
    fireEvent.change(screen.getByTestId("image-subject"), {
      target: { value: "a hero shot of a coffee shop" },
    });
    expect(submit.disabled).toBe(false);
  });

  it("sends a POST with the expected shape on submit", async () => {
    const onGenerated = vi.fn();
    renderForm({ onGenerated });
    await screen.findByTestId("image-generation-form");
    fireEvent.click(screen.getByTestId("image-purpose-product"));
    fireEvent.click(screen.getByTestId("image-model-ultra"));
    fireEvent.click(screen.getByTestId("image-ratio-1:1"));
    fireEvent.change(screen.getByTestId("image-subject"), {
      target: { value: "a hand-blown glass mug" },
    });
    fireEvent.click(screen.getByTestId("image-submit"));

    await waitFor(() => {
      expect(postBodies.length).toBe(1);
    });
    expect(postBodies[0]).toMatchObject({
      workspace: "ws-1",
      purpose: "product",
      subject: "a hand-blown glass mug",
      model: "ultra",
      aspect_ratio: "1:1",
    });
    await waitFor(() => {
      expect(onGenerated).toHaveBeenCalledWith("img-123");
    });
  });

  it("renders the generated result card on success", async () => {
    renderForm();
    await screen.findByTestId("image-generation-form");
    fireEvent.change(screen.getByTestId("image-subject"), {
      target: { value: "subject text" },
    });
    fireEvent.click(screen.getByTestId("image-submit"));
    const result = await screen.findByTestId("image-result");
    expect(result).toBeInTheDocument();
    expect(result).toHaveTextContent("sd3-large");
  });

  it("renders an error banner on POST failure", async () => {
    vi.spyOn(global, "fetch").mockImplementation((url, init) => {
      const u = String(url);
      if (u.includes("/api/styles/")) {
        return Promise.resolve(
          new Response(JSON.stringify(STYLE_LIBRARY_PAYLOAD), { status: 200 }),
        );
      }
      if (u.includes("/api/images/") && init?.method === "POST") {
        return Promise.resolve(
          new Response(
            JSON.stringify({ error: "boom", code: "upstream_media_engine" }),
            { status: 502 },
          ),
        );
      }
      return Promise.resolve(new Response("[]", { status: 200 }));
    });

    renderForm();
    await screen.findByTestId("image-generation-form");
    fireEvent.change(screen.getByTestId("image-subject"), {
      target: { value: "subject text" },
    });
    fireEvent.click(screen.getByTestId("image-submit"));
    await waitFor(() => {
      expect(screen.getByTestId("image-error")).toBeInTheDocument();
    });
  });

  it("threads negative_prompt_override only when advanced+text supplied", async () => {
    renderForm();
    await screen.findByTestId("image-generation-form");
    fireEvent.change(screen.getByTestId("image-subject"), {
      target: { value: "subject" },
    });
    fireEvent.click(screen.getByTestId("image-advanced-toggle"));
    fireEvent.change(await screen.findByTestId("image-negative-prompt"), {
      target: { value: "no people" },
    });
    fireEvent.click(screen.getByTestId("image-submit"));
    await waitFor(() => {
      expect(postBodies.length).toBe(1);
    });
    expect(postBodies[0]).toMatchObject({
      negative_prompt_override: "no people",
    });
  });
});
