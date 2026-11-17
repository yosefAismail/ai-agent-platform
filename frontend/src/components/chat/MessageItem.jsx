export default function MessageItem({ message, typing = false }) {
  return (
    <div className={`message-row ${message.role}`}>
      <div className={`message ${message.role}${typing ? " typing" : ""}`}>
        <span className="message-label">{message.role === "user" ? "You" : "AI"}</span>
        <p>{message.content}</p>
      </div>
    </div>
  );
}
