/**
 * AvatarSessionInner — R8.2 (SESSION 155).
 *
 * Component rendered INSIDE ``<AvatarCall>`` so it can use
 * the SDK's ``useClientEvents`` hook. The avatar's LLM
 * invokes tools by sending ``{type: 'client_event', tool,
 * args}`` over the WebRTC data channel; this component
 * receives those events and dispatches them to the backend
 * via R8.1's ``useInvokeTool`` hook. The parent's tool
 * routing logic (``onToolInvocation``) decides what to do
 * with the result (open modal for awaiting_approval, surface
 * in ToolResultPanel otherwise).
 *
 * **Narration loop (Q-r-2 v1 reality)**:
 * Runway's SDK doesn't expose a ``sendClientEvent`` — the
 * tool-invocation channel is one-way (avatar → SPA). The
 * v1 narration story is therefore:
 *   * Avatar fires `render_video` (LLM-driven).
 *   * SPA's modal pops; operator approves / rejects.
 *   * Operator continues the conversation verbally:
 *     "yeah go ahead" → avatar continues; or "no, let's
 *     refine the script first" → avatar pivots.
 *   * The audit row's `error_message` captures the
 *     operator's reason server-side for retrospective
 *     review.
 *
 * In-conversation rejection narration via a backend-pushed
 * event channel is a v2 concern (or a Runway SDK feature
 * request).
 */
import { useClientEvents, type ClientEvent } from "@runwayml/avatars-react";

export interface AvatarSessionInnerProps {
  /** Fires when the avatar invokes a tool. Parent routes
   *  the dispatch result through the TalkRoute lifecycle
   *  (modal for awaiting_approval, panel otherwise). */
  onToolInvocation: (toolName: string, args: Record<string, unknown>) => void;
}

export function AvatarSessionInner({
  onToolInvocation,
}: AvatarSessionInnerProps) {
  // Listen to ALL client events. Filtering happens here
  // rather than per-tool because v1's tool registry lives
  // server-side; the SPA dispatches anything the avatar
  // sends and lets the backend reject unknowns.
  useClientEvents((event: ClientEvent) => {
    if (event.type !== "client_event") return;
    if (typeof event.tool !== "string" || !event.tool) return;
    const args =
      event.args && typeof event.args === "object"
        ? (event.args as Record<string, unknown>)
        : {};
    onToolInvocation(event.tool, args);
  });

  // No visible markup — the SDK renders the avatar's
  // video/audio via its sibling primitives. This component
  // is hook-only.
  return null;
}
