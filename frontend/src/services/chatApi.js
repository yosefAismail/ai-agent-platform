import { requestJson } from "./api.js";

export function sendChatMessage(messages) {
  return requestJson("/chat", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ messages }),
  });
}
