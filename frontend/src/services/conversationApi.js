import { requestJson } from "./api.js";

export function listConversations() {
  return requestJson("/conversations");
}

export function getConversation(conversationId) {
  return requestJson(`/conversations/${encodeURIComponent(conversationId)}`);
}

export function getConversationMessages(conversationId) {
  return requestJson(`/conversations/${encodeURIComponent(conversationId)}/messages`);
}

export function createConversation(title = "New conversation") {
  return requestJson("/conversations", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ title }),
  });
}

export function deleteConversation(conversationId) {
  return requestJson(`/conversations/${encodeURIComponent(conversationId)}`, {
    method: "DELETE",
  });
}
