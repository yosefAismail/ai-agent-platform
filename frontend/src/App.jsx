import { useEffect } from "react";
import ChatWindow from "./components/chat/ChatWindow.jsx";
import ConversationSidebar from "./features/conversations/ConversationSidebar.jsx";
import useConversations from "./features/conversations/useConversations.js";
import useChat from "./hooks/useChat.js";
import "./App.css";

export default function App() {
  const {
    conversations,
    activeConversation,
    activeId,
    activeMessages,
    setActiveId,
    createConversation,
    updateMessages,
    deleteConversation,
    ready,
    loadingMessages,
    creating,
    error: conversationError,
  } = useConversations();

  useEffect(() => {
    if (ready && conversations.length === 0 && !creating) void createConversation();
  }, [ready, conversations.length, creating, createConversation]);

  const { messages, loading, error: chatError, sendMessage } = useChat({
    conversationId: activeId,
    initialMessages: activeMessages,
    onMessagesChange: updateMessages,
  });

  return (
    <main className="app-shell">
      <div className="workspace">
        <ConversationSidebar
          conversations={conversations}
          activeId={activeId}
          onSelect={setActiveId}
          onCreate={createConversation}
          onDelete={deleteConversation}
          creating={creating}
        />
        <ChatWindow
          messages={messages}
          loading={loading}
          disabled={!activeConversation || loadingMessages}
          error={chatError || conversationError}
          onSend={sendMessage}
        />
      </div>
    </main>
  );
}
