import MessageItem from "./MessageItem.jsx";

export default function MessageList({ messages, loading }) {
  return (
    <section className="messages" aria-live="polite" aria-label="Conversation messages">
      {messages.length === 0 && !loading ? (
        <div className="empty-state"><p>Start a conversation with your AI assistant.</p></div>
      ) : messages.map((message, index) => (
        <MessageItem key={`${index}-${message.role}`} message={message} />
      ))}
      {loading && <MessageItem message={{ role: "assistant", content: "Thinking..." }} typing />}
    </section>
  );
}
