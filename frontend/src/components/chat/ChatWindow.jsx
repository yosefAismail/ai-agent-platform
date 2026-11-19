import { useState } from "react";
import ChatInput from "./ChatInput.jsx";
import MessageList from "./MessageList.jsx";

export default function ChatWindow({ messages, loading, disabled = false, error = "", onSend }) {
  const [draft, setDraft] = useState("");

  const submit = async (event) => {
    event.preventDefault();
    if (loading || disabled || !draft.trim()) return;
    const content = draft.trim();
    setDraft("");
    await onSend(content);
  };

  return (
    <section className="chat-card">
      <header className="chat-header">
        <div className="brand-wrap">
          <div className="brand-mark">AI</div>
          <div><p className="eyebrow">assistant</p><h1>My First AI Agent</h1></div>
        </div>
      </header>
      {error && <p className="chat-error" role="alert">{error}</p>}
      <MessageList messages={messages} loading={loading} />
      <ChatInput
        value={draft}
        onChange={setDraft}
        onSubmit={submit}
        loading={loading}
        disabled={disabled}
      />
    </section>
  );
}
