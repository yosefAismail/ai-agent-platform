export default function ChatInput({ value, onChange, onSubmit, loading }) {
  return (
    <form onSubmit={onSubmit} className="chat-form">
      <label className="input-wrap">
        <span className="sr-only">Type your message</span>
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask something..."
          disabled={loading}
        />
      </label>
      <button type="submit" disabled={loading || !value.trim()}>
        {loading ? "Sending..." : "Send"}
      </button>
    </form>
  );
}
