/**
 * W11.6.3 — StylePresetPicker unit tests.
 *
 * Covers the picker contract: renders categories, displays
 * preset metadata for Contract rule 9, selection callback fires
 * with the chosen preset slug, and selection clears via the
 * Clear button.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { StylePresetPicker } from "./style-preset-picker";

const STYLE_LIBRARY_PAYLOAD = {
  total_presets: 4,
  categories: [
    {
      id: "photography",
      display_name: "Photography Styles",
      description: "Realistic, professional photo-based looks",
      icon: "📷",
      presets: [
        {
          name: "photorealistic",
          display_name: "Photorealistic",
          category: "photography",
          description: "Ultra-realistic photography quality",
          best_for: ["corporate"],
          mood: "professional",
          example_prompt_suffix: "photorealistic, 8k uhd",
        },
        {
          name: "portrait",
          display_name: "Portrait Photography",
          category: "photography",
          description: "Professional headshot/portrait style",
          best_for: ["coaching"],
          mood: "trustworthy",
          example_prompt_suffix: "portrait photography, 85mm",
        },
      ],
    },
    {
      id: "genre",
      display_name: "Genre Styles",
      description: "Thematic visual styles",
      icon: "🌟",
      presets: [
        {
          name: "cyberpunk",
          display_name: "Cyberpunk",
          category: "genre",
          description: "Neon-lit futuristic high-tech style",
          best_for: ["gaming"],
          mood: "edgy",
          example_prompt_suffix: "cyberpunk style, neon lights",
        },
        {
          name: "fantasy",
          display_name: "Fantasy",
          category: "genre",
          description: "Magical, epic fantasy art style",
          best_for: ["gaming"],
          mood: "magical",
          example_prompt_suffix: "fantasy art, magical",
        },
      ],
    },
  ],
};

function renderPicker(props: {
  value?: string;
  onChange?: (v: string | undefined) => void;
}) {
  const onChange = props.onChange ?? vi.fn();
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return {
    onChange,
    ...render(
      <QueryClientProvider client={qc}>
        <StylePresetPicker value={props.value} onChange={onChange} />
      </QueryClientProvider>,
    ),
  };
}

describe("W11.6.3 — StylePresetPicker", () => {
  beforeEach(() => {
    vi.spyOn(global, "fetch").mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify(STYLE_LIBRARY_PAYLOAD), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      ),
    );
  });

  afterEach(() => {
    vi.restoreAllMocks();
  });

  it("renders a tab per category", async () => {
    renderPicker({});
    await screen.findByTestId("style-preset-tab-photography");
    expect(screen.getByTestId("style-preset-tab-photography")).toBeInTheDocument();
    expect(screen.getByTestId("style-preset-tab-genre")).toBeInTheDocument();
  });

  it("renders all presets in the active category with display + description", async () => {
    renderPicker({});
    const card = await screen.findByTestId("style-preset-photorealistic");
    expect(card).toHaveTextContent("Photorealistic");
    expect(card).toHaveTextContent("Ultra-realistic photography quality");
    expect(card).toHaveTextContent("professional");
  });

  it("surfaces best_for as a tooltip (Contract rule 9 hover-text)", async () => {
    renderPicker({});
    const card = await screen.findByTestId("style-preset-photorealistic");
    expect(card).toHaveAttribute(
      "title",
      expect.stringContaining("Good for"),
    );
  });

  it("fires onChange with the selected preset name", async () => {
    const user = userEvent.setup();
    const { onChange } = renderPicker({});
    // Switch to the genre tab so its preset cards are interactable
    // (Radix Tabs need real pointer events — fireEvent.click on the
    // trigger doesn't always flip the active panel under jsdom).
    await user.click(await screen.findByTestId("style-preset-tab-genre"));
    const card = await screen.findByTestId("style-preset-cyberpunk");
    await user.click(card);
    expect(onChange).toHaveBeenCalledWith("cyberpunk");
  });

  it("marks the controlled value as selected", async () => {
    renderPicker({ value: "fantasy" });
    const card = await screen.findByTestId("style-preset-fantasy");
    expect(card).toHaveAttribute("data-selected", "true");
  });

  it("shows a Clear button when something is selected and clears via undefined", async () => {
    const { onChange } = renderPicker({ value: "cyberpunk" });
    const clear = await screen.findByTestId("style-preset-clear");
    fireEvent.click(clear);
    expect(onChange).toHaveBeenCalledWith(undefined);
  });

  it("surfaces the selection summary in the header", async () => {
    renderPicker({ value: "cyberpunk" });
    const summary = await screen.findByTestId("style-preset-selection");
    expect(summary).toHaveTextContent("Cyberpunk");
    expect(summary).toHaveTextContent("edgy");
  });

  it("renders an error banner on library load failure", async () => {
    vi.spyOn(global, "fetch").mockImplementation(() =>
      Promise.resolve(new Response("oops", { status: 502 })),
    );
    renderPicker({});
    await waitFor(() => {
      expect(
        screen.getByTestId("style-preset-picker-error"),
      ).toBeInTheDocument();
    });
  });
});
