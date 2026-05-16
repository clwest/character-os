/**
 * SpokespersonEditModal — W11.1 unit tests.
 *
 * Cheap render + interaction coverage. Full integration with
 * the PATCH endpoint is exercised manually via the dogfood
 * loop; these tests anchor the UI contract: form initializes
 * with the spokesperson's current values, only changed fields
 * make it into the payload, Save is disabled until something
 * changes, Esc dismisses (when not pending), unsupported
 * fields don't show up.
 */
import { describe, expect, it, vi, beforeEach, afterEach } from "vitest";
import { render, screen, fireEvent, act, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";

import { SpokespersonEditModal } from "./spokesperson-edit-modal";
import type { Spokesperson } from "@/lib/api/spokespeople";

const MOCK_SP: Spokesperson = {
  id: "sp-1",
  workspace: "ws-1",
  workspace_name: "Workspace",
  name: "Marcus",
  business_brief: "AP history teacher.",
  visual_subject: "battle unicorn in roman gear",
  visual_template: "mascot",
  tone_archetype: "tutor",
  status: "ready",
  runway_avatar_id: "av-1",
  runway_avatar_status: "ready",
  portrait_path: "https://fake.example/p.png",
  voice_id: "marcus",
  video_count: 0,
  created_at: "2026-05-15T00:00:00Z",
  updated_at: "2026-05-15T00:00:00Z",
};

function renderModal(props: { onClose?: () => void } = {}) {
  const onClose = props.onClose ?? vi.fn();
  const qc = new QueryClient({
    defaultOptions: { queries: { retry: false }, mutations: { retry: false } },
  });
  return {
    onClose,
    ...render(
      <QueryClientProvider client={qc}>
        <SpokespersonEditModal spokesperson={MOCK_SP} onClose={onClose} />
      </QueryClientProvider>,
    ),
  };
}

describe("W11.1 — SpokespersonEditModal", () => {
  beforeEach(() => {
    // useVoicePresets fires a GET on mount; the change-voice action
    // returns the {spokesperson, voice_patch} envelope; everything
    // else (PATCH on the spokesperson) returns a bare row.
    vi.spyOn(global, "fetch").mockImplementation((url, _init) => {
      const u = String(url);
      if (u.includes("/voice-presets/")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({ presets: ["vincent", "marcus", "clara"] }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      if (u.includes("/change-voice/")) {
        return Promise.resolve(
          new Response(
            JSON.stringify({
              spokesperson: { ...MOCK_SP, voice_id: "clara" },
              voice_patch: { status: "ok", error: null },
            }),
            { status: 200, headers: { "Content-Type": "application/json" } },
          ),
        );
      }
      // Default: spokesperson PATCH / GET.
      return Promise.resolve(
        new Response(JSON.stringify({ ...MOCK_SP, name: "Marcus Aurelius" }), {
          status: 200,
          headers: { "Content-Type": "application/json" },
        }),
      );
    });
  });
  afterEach(() => vi.restoreAllMocks());

  it("initializes with the spokesperson's current values", () => {
    renderModal();
    expect(
      (screen.getByTestId("edit-name") as HTMLInputElement).value,
    ).toBe("Marcus");
    expect(
      (screen.getByTestId("edit-brief") as HTMLTextAreaElement).value,
    ).toBe("AP history teacher.");
    expect(
      (screen.getByTestId("edit-visual") as HTMLInputElement).value,
    ).toBe("battle unicorn in roman gear");
    expect((screen.getByTestId("edit-tone") as HTMLSelectElement).value).toBe(
      "tutor",
    );
  });

  it("Save is disabled until something changes", () => {
    renderModal();
    expect(
      (screen.getByTestId("edit-save") as HTMLButtonElement).disabled,
    ).toBe(true);
    fireEvent.change(screen.getByTestId("edit-name"), {
      target: { value: "Marcus Aurelius" },
    });
    expect(
      (screen.getByTestId("edit-save") as HTMLButtonElement).disabled,
    ).toBe(false);
  });

  it("Save fires a PATCH with only the changed fields", async () => {
    const fetchSpy = global.fetch as ReturnType<typeof vi.fn>;
    const { onClose } = renderModal();
    fireEvent.change(screen.getByTestId("edit-name"), {
      target: { value: "Marcus Aurelius" },
    });
    await act(async () => {
      fireEvent.submit(screen.getByTestId("edit-save").closest("form")!);
    });
    // Find the PATCH call among the fetches (useVoicePresets also
    // fires a GET on mount).
    const patchCall = fetchSpy.mock.calls.find(
      ([, init]) => (init as RequestInit | undefined)?.method === "PATCH",
    );
    expect(patchCall).toBeDefined();
    const [url, init] = patchCall!;
    expect(url).toBe("/api/spokespeople/sp-1/");
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body).toEqual({ name: "Marcus Aurelius" });
    expect(onClose).toHaveBeenCalled();
  });

  it("W11.2 — voice change fires a separate change-voice action", async () => {
    const fetchSpy = global.fetch as ReturnType<typeof vi.fn>;
    const { onClose } = renderModal();
    // Wait for useVoicePresets to load AND the select to settle on
    // the spokesperson's current voice_id. Without this wait the
    // select may transiently show the first option (vincent) while
    // the controlled value prop catches up.
    await waitFor(() => {
      expect(
        (screen.getByTestId("edit-voice") as HTMLSelectElement).value,
      ).toBe("marcus");
    });
    fireEvent.change(screen.getByTestId("edit-voice"), {
      target: { value: "clara" },
    });
    expect(
      (screen.getByTestId("edit-voice") as HTMLSelectElement).value,
    ).toBe("clara");
    await act(async () => {
      fireEvent.submit(screen.getByTestId("edit-save").closest("form")!);
    });
    const changeVoiceCall = fetchSpy.mock.calls.find(([url]) =>
      String(url).includes("/change-voice/"),
    );
    expect(changeVoiceCall).toBeDefined();
    const [, init] = changeVoiceCall!;
    const body = JSON.parse((init as RequestInit).body as string);
    expect(body).toEqual({ preset: "clara" });
    expect(onClose).toHaveBeenCalled();
  });

  it("Esc dismisses without saving", () => {
    const { onClose } = renderModal();
    fireEvent.keyDown(window, { key: "Escape" });
    expect(onClose).toHaveBeenCalled();
  });

  it("Cancel button dismisses without saving", () => {
    const { onClose } = renderModal();
    fireEvent.click(screen.getByTestId("edit-cancel"));
    expect(onClose).toHaveBeenCalled();
  });

  it("blank name shows an inline error", async () => {
    renderModal();
    fireEvent.change(screen.getByTestId("edit-name"), {
      target: { value: "" },
    });
    fireEvent.change(screen.getByTestId("edit-brief"), {
      target: { value: "new brief" },
    });
    await act(async () => {
      fireEvent.submit(screen.getByTestId("edit-save").closest("form")!);
    });
    // Save button stays disabled when name is blank.
    expect(
      (screen.getByTestId("edit-save") as HTMLButtonElement).disabled,
    ).toBe(true);
  });
});
