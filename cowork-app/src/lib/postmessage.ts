/**
 * PostMessage bridge between parent SvelteKit app and this cowork-app iframe.
 *
 * Protocol:
 *   Parent -> Iframe:
 *     { type: "cowork-init", payload: CoworkConfig }
 *     { type: "cowork-destroy" }
 *
 *   Iframe -> Parent:
 *     { type: "cowork-ready" }
 *     { type: "cowork-status", payload: { playerCount, roomId } }
 *     { type: "cowork-error", payload: { message } }
 */

import type { CoworkConfig } from "./socket";

export type ParentMessage =
  | { type: "cowork-init"; payload: CoworkConfig }
  | { type: "cowork-destroy" };

export function sendToParent(message: { type: string; payload?: unknown }): void {
  if (typeof window !== "undefined" && window.parent !== window) {
    window.parent.postMessage(message, "*");
  }
}

export function listenForParentMessages(
  onInit: (config: CoworkConfig) => void,
  onDestroy: () => void
): () => void {
  function handler(event: MessageEvent) {
    const data = event.data as ParentMessage;
    if (!data?.type) return;

    switch (data.type) {
      case "cowork-init":
        if (data.payload) onInit(data.payload);
        break;
      case "cowork-destroy":
        onDestroy();
        break;
    }
  }

  window.addEventListener("message", handler);
  return () => window.removeEventListener("message", handler);
}
