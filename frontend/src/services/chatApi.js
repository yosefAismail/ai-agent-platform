import { requestJson } from "./api.js";

export function sendConversationMessage(conversationId, content) {
  return requestJson(`/conversations/${encodeURIComponent(conversationId)}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
  });
}
