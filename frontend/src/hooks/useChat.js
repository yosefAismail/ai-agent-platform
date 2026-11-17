import { useCallback, useState } from "react";
import { sendChatMessage } from "../services/chatApi.js";

export default function useChat({ conversationId, initialMessages = [], onMessagesChange }) {
  const [chatState, setChatState] = useState(() => ({ conversationId, messages: initialMessages }));
  const [loading, setLoading] = useState(false);
  const messages = chatState.conversationId === conversationId
    ? chatState.messages
    : initialMessages;

  const sendMessage = useCallback(async (content) => {
    const text = content.trim();
    if (!text || loading) return;

    const updatedMessages = [...messages, { role: "user", content: text }];
    setChatState({ conversationId, messages: updatedMessages });
    onMessagesChange(conversationId, updatedMessages);
    setLoading(true);

    try {
      const data = await sendChatMessage(updatedMessages);
      const completeMessages = [
        ...updatedMessages,
        { role: "assistant", content: data.response || "" },
      ];
      setChatState({ conversationId, messages: completeMessages });
      onMessagesChange(conversationId, completeMessages);
    } catch (error) {
      const failedMessages = [
        ...updatedMessages,
        { role: "assistant", content: `Error: ${error.message}` },
      ];
      setChatState({ conversationId, messages: failedMessages });
      onMessagesChange(conversationId, failedMessages);
    } finally {
      setLoading(false);
    }
  }, [conversationId, loading, messages, onMessagesChange]);

  return { messages, loading, sendMessage };
}
