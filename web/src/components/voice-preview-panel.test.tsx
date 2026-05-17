/**
 * W11.x.2 (SESSION 175) — VoicePreviewPanel unit tests.
 *
 * The panel is exported from spokesperson-wizard.tsx and
 * mounted in place of Step4Confirm after a successful
 * clone-voice mutation. Tests cover the new surface area
 * without exercising the full wizard reducer.
 */
import { describe, expect, it, vi } from "vitest";
import { fireEvent, render, screen } from "@testing-library/react";

import { VoicePreviewPanel } from "./spokesperson-wizard";

describe("W11.x.2 — VoicePreviewPanel", () => {
  const PREVIEW = {
    spokespersonId: "sp-1",
    voiceId: "vc_abc123",
    previewUrl: "https://runway.cdn/preview.mp3?jwt=eyJh",
  };

  it("renders the preview audio with the Runway-supplied src", () => {
    render(<VoicePreviewPanel preview={PREVIEW} onContinue={vi.fn()} />);
    const audio = screen.getByTestId("voice-preview-audio") as HTMLAudioElement;
    expect(audio).toHaveAttribute("src", PREVIEW.previewUrl);
    expect(audio).toHaveAttribute("controls");
  });

  it("surfaces the voice id so operators can copy/reference it", () => {
    render(<VoicePreviewPanel preview={PREVIEW} onContinue={vi.fn()} />);
    expect(screen.getByText(/vc_abc123/)).toBeInTheDocument();
  });

  it("calls onContinue when the operator hits the Continue button", () => {
    const onContinue = vi.fn();
    render(<VoicePreviewPanel preview={PREVIEW} onContinue={onContinue} />);
    fireEvent.click(screen.getByTestId("voice-preview-continue"));
    expect(onContinue).toHaveBeenCalledTimes(1);
  });

  it("renders a fallback link for browsers without audio support", () => {
    render(<VoicePreviewPanel preview={PREVIEW} onContinue={vi.fn()} />);
    const link = screen.getByRole("link", { name: /open the preview/i });
    expect(link).toHaveAttribute("href", PREVIEW.previewUrl);
    expect(link).toHaveAttribute("target", "_blank");
    expect(link).toHaveAttribute("rel", expect.stringContaining("noopener"));
  });
});
