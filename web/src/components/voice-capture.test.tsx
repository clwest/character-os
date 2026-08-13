/**
 * SESSION 230 — Chapter 2 Beat 3 voice sampling.
 *
 * Focused test for the new list-of-rows PresetPanel. Covers the
 * primary contract:
 *
 *   - Rows render from the ``useVoicePresets`` response shape.
 *   - Picking a row enables "Use this voice"; committing fires
 *     ``onChange({mode: "preset", preset})``.
 *   - Presets with ``sample_url === null`` render the
 *     "Sample coming soon" state instead of a play button.
 *
 * Audio playback (HTMLAudioElement.play) is stubbed out globally
 * so the tests don't need to mock the audio graph; the click
 * paths still exercise the state transitions.
 */
import { describe, expect, it, vi, beforeEach } from "vitest";
import {
  act,
  fireEvent,
  render,
  screen,
  waitFor,
} from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { VoiceCapture } from "./voice-capture";

function renderVoiceCapture(onChange = vi.fn()) {
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false, gcTime: 0 } },
  });
  const result = render(
    <QueryClientProvider client={qc}>
      <VoiceCapture value={null} onChange={onChange} />
    </QueryClientProvider>,
  );
  return { ...result, onChange };
}

function installFetchSpy(presets: Array<{ name: string; sample_url: string | null }>) {
  vi.spyOn(global, "fetch").mockImplementation((url) => {
    const u = String(url);
    if (u.includes("/voice-presets/")) {
      return Promise.resolve(
        new Response(JSON.stringify({ presets }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    }
    return Promise.resolve(new Response("{}", { status: 200 }));
  });
}

describe("SESSION 230 — PresetPanel voice sampling", () => {
  beforeEach(() => {
    // HTMLAudioElement.play doesn't run in jsdom; stub so the
    // component's play() call resolves without crashing.
    Object.defineProperty(HTMLAudioElement.prototype, "play", {
      configurable: true,
      value: vi.fn().mockResolvedValue(undefined),
    });
    Object.defineProperty(HTMLAudioElement.prototype, "pause", {
      configurable: true,
      value: vi.fn(),
    });
  });

  it("renders a row per preset from the enriched shape", async () => {
    installFetchSpy([
      { name: "vincent", sample_url: "/voice-samples/vincent.mp3" },
      { name: "clara", sample_url: "/voice-samples/clara.mp3" },
    ]);
    renderVoiceCapture();
    await waitFor(() => {
      expect(screen.getByTestId("voice-preset-list")).toBeInTheDocument();
    });
    expect(screen.getByTestId("voice-preset-row-vincent")).toBeInTheDocument();
    expect(screen.getByTestId("voice-preset-row-clara")).toBeInTheDocument();
  });

  it("picking a row enables Use this voice; committing fires onChange", async () => {
    installFetchSpy([
      { name: "vincent", sample_url: "/voice-samples/vincent.mp3" },
      { name: "clara", sample_url: "/voice-samples/clara.mp3" },
    ]);
    const { onChange } = renderVoiceCapture();
    await waitFor(() => {
      expect(screen.getByTestId("voice-preset-pick-vincent")).toBeInTheDocument();
    });

    const use = screen.getByTestId("voice-preset-use") as HTMLButtonElement;
    expect(use.disabled).toBe(true);

    fireEvent.click(screen.getByTestId("voice-preset-pick-vincent"));
    expect(use.disabled).toBe(false);

    fireEvent.click(use);
    expect(onChange).toHaveBeenCalledWith({ mode: "preset", preset: "vincent" });
  });

  it("presets with a null sample_url render Sample coming soon", async () => {
    installFetchSpy([
      { name: "vincent", sample_url: null },
      { name: "clara", sample_url: "/voice-samples/clara.mp3" },
    ]);
    renderVoiceCapture();
    await waitFor(() => {
      expect(screen.getByTestId("voice-preset-row-vincent")).toBeInTheDocument();
    });
    expect(
      screen.getByTestId("voice-preset-unavailable-vincent"),
    ).toBeInTheDocument();
    // clara has a sample — should render a play button, not the
    // unavailable label.
    expect(screen.getByTestId("voice-preset-play-clara")).toBeInTheDocument();
    expect(
      screen.queryByTestId("voice-preset-unavailable-clara"),
    ).not.toBeInTheDocument();
  });

  it("clicking play transitions the row into a playing state", async () => {
    installFetchSpy([
      { name: "vincent", sample_url: "/voice-samples/vincent.mp3" },
    ]);
    renderVoiceCapture();
    await waitFor(() => {
      expect(screen.getByTestId("voice-preset-play-vincent")).toBeInTheDocument();
    });
    const play = screen.getByTestId("voice-preset-play-vincent");
    await act(async () => {
      fireEvent.click(play);
    });
    await waitFor(() => {
      const btn = screen.getByTestId("voice-preset-play-vincent");
      expect(btn.getAttribute("data-playing")).toBe("true");
    });
  });
});
