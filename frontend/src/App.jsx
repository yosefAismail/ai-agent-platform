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
    setActiveId,
    createConversation,
    updateMessages,
    deleteConversation,
  } = useConversations();

  useEffect(() => {
    if (!activeId && conversations.length === 0) createConversation();
  }, [activeId, conversations.length, createConversation]);

  const { messages, loading, sendMessage } = useChat({
    conversationId: activeId,
    initialMessages: activeConversation?.messages ?? [],
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
        />
        <ChatWindow messages={messages} loading={loading} onSend={sendMessage} />
      </div>
    </main>
  );
}
