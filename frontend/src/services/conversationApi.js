const STORAGE_KEY = "my-first-ai-agent.conversations";

function createId() {
  return globalThis.crypto?.randomUUID?.() || `${Date.now()}-${Math.random()}`;
}

export function getConversations() {
  try {
    const stored = JSON.parse(localStorage.getItem(STORAGE_KEY) || "[]");
    return Array.isArray(stored) ? stored : [];
  } catch {
    return [];
  }
}

export function saveConversations(conversations) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(conversations));
}

export function createConversation() {
  return {
    id: createId(),
    title: "New conversation",
    messages: [],
    updatedAt: new Date().toISOString(),
  };
}
