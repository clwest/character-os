/**
 * AvatarSessionInner unit tests — R8.2.
 *
 * The component lives inside `<AvatarCall>` and consumes
 * the SDK's `useClientEvents` hook. Tests mock the hook so
 * we can drive synthetic events through the dispatch path.
 */
import { describe, expect, it, vi } from "vitest";
import { render } from "@testing-library/react";

let captured: ((event: unknown) => void) | null = null;
vi.mock("@runwayml/avatars-react", () => ({
  useClientEvents: (handler: (event: unknown) => void) => {
    captured = handler;
  },
  useAvatarSession: () => ({
    state: "live",
    sessionId: "mock-session",
    error: null,
    end: vi.fn().mockResolvedValue(undefined),
  }),
}));

import { AvatarSessionInner } from "./avatar-session-inner";

describe("AvatarSessionInner (R8.2)", () => {
  beforeEach(() => {
    captured = null;
  });

  it("dispatches tool invocations to the parent", () => {
    const onToolInvocation = vi.fn();
    render(<AvatarSessionInner onToolInvocation={onToolInvocation} />);
    expect(typeof captured).toBe("function");
    captured!({
      type: "client_event",
      tool: "render_video",
      args: { script: "Pitch the spring sale." },
    });
    expect(onToolInvocation).toHaveBeenCalledWith("render_video", {
      script: "Pitch the spring sale.",
    });
  });

  it("ignores non-client_event payloads", () => {
    const onToolInvocation = vi.fn();
    render(<AvatarSessionInner onToolInvocation={onToolInvocation} />);
    captured!({ type: "transcription_entry", text: "hello" });
    expect(onToolInvocation).not.toHaveBeenCalled();
  });

  it("ignores events with missing tool name", () => {
    const onToolInvocation = vi.fn();
    render(<AvatarSessionInner onToolInvocation={onToolInvocation} />);
    captured!({ type: "client_event", tool: "", args: {} });
    expect(onToolInvocation).not.toHaveBeenCalled();
  });

  it("normalizes non-object args to empty {}", () => {
    const onToolInvocation = vi.fn();
    render(<AvatarSessionInner onToolInvocation={onToolInvocation} />);
    captured!({ type: "client_event", tool: "show_videos_tab", args: null });
    expect(onToolInvocation).toHaveBeenCalledWith("show_videos_tab", {});
  });
});
