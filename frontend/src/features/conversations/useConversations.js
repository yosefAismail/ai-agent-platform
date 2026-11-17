import { useCallback, useState } from "react";
import {
  createConversation,
  getConversations,
  saveConversations,
} from "../../services/conversationApi.js";

function persist(conversations) {
  saveConversations(conversations);
  return conversations;
}

export default function useConversations() {
  const [conversations, setConversations] = useState(getConversations);
  const [activeId, setActiveId] = useState(() => getConversations()[0]?.id ?? null);

  const createNewConversation = useCallback(() => {
    const conversation = createConversation();
    setConversations((current) => persist([conversation, ...current]));
    setActiveId(conversation.id);
  }, []);

  const updateMessages = useCallback((id, messages) => {
    setConversations((current) =>
      persist(
        current.map((conversation) => {
          if (conversation.id !== id) return conversation;
          const firstUserMessage = messages.find((message) => message.role === "user")?.content;
          return {
            ...conversation,
            messages,
            title: firstUserMessage
              ? firstUserMessage.slice(0, 36) + (firstUserMessage.length > 36 ? "…" : "")
              : conversation.title,
            updatedAt: new Date().toISOString(),
          };
        }),
      ),
    );
  }, []);

  const deleteConversation = useCallback((id) => {
    setConversations((current) => {
      const remaining = current.filter((conversation) => conversation.id !== id);
      persist(remaining);
      if (id === activeId) setActiveId(remaining[0]?.id ?? null);
      return remaining;
    });
  }, [activeId]);

  const activeConversation = conversations.find((conversation) => conversation.id === activeId) ?? null;

  return {
    conversations,
    activeConversation,
    activeId,
    setActiveId,
    createConversation: createNewConversation,
    updateMessages,
    deleteConversation,
  };
}
