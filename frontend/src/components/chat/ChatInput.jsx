export default function ChatInput({ value, onChange, onSubmit, loading, disabled = false }) {
  return (
    <form onSubmit={onSubmit} className="chat-form">
      <label className="input-wrap">
        <span className="sr-only">Type your message</span>
        <input
          value={value}
          onChange={(event) => onChange(event.target.value)}
          placeholder="Ask something..."
          disabled={loading || disabled}
        />
      </label>
      <button type="submit" disabled={loading || disabled || !value.trim()}>
        {loading ? "Sending..." : "Send"}
      </button>
    </form>
  );
}
