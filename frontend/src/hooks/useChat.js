import { useCallback, useState } from "react";
import { sendConversationMessage } from "../services/chatApi.js";

export default function useChat({
  conversationId,
  initialMessages = [],
  onMessagesChange,
}) {
  const [chatState, setChatState] = useState(() => ({
    conversationId,
    messages: initialMessages,
  }));
  const [loading, setLoading] = useState(false);
  const [chatError, setChatError] = useState({ conversationId, message: "" });
  const messages = chatState.conversationId === conversationId
    ? chatState.messages
    : initialMessages;

  const sendMessage = useCallback(async (content) => {
    const text = content.trim();
    if (!conversationId || !text || loading) return;

    const pendingMessages = [...messages, { role: "user", content: text }];
    setChatState({ conversationId, messages: pendingMessages });
    onMessagesChange(conversationId, pendingMessages);
    setLoading(true);
    setChatError({ conversationId, message: "" });

    try {
      const result = await sendConversationMessage(conversationId, text);
      const completeMessages = [
        ...pendingMessages.slice(0, -1),
        result.user_message,
        result.assistant_message,
      ];
      setChatState({ conversationId, messages: completeMessages });
      onMessagesChange(conversationId, completeMessages);
    } catch (requestError) {
      // The backend intentionally keeps the user message if Gemini fails.
      setChatError({ conversationId, message: requestError.message });
    } finally {
      setLoading(false);
    }
  }, [conversationId, loading, messages, onMessagesChange]);

  const error = chatError.conversationId === conversationId ? chatError.message : "";
  return { messages, loading, error, sendMessage };
}
