export default function ConversationSidebar({
  conversations,
  activeId,
  onSelect,
  onCreate,
  onDelete,
  creating,
}) {
  return (
    <aside className="conversation-sidebar" aria-label="Conversations">
      <div className="sidebar-heading">
        <div><p className="eyebrow">Your workspace</p><h2>Chats</h2></div>
        <button
          className="new-chat-button"
          type="button"
          onClick={onCreate}
          aria-label="New conversation"
          disabled={creating}
        >+</button>
      </div>
      <button className="sidebar-new-chat" type="button" onClick={onCreate} disabled={creating}>
        + New conversation
      </button>
      <div className="conversation-list">
        {conversations.map((conversation) => (
          <div
            className={`conversation-entry${conversation.id === activeId ? " active" : ""}`}
            key={conversation.id}
          >
            <button className="conversation-select" type="button" onClick={() => onSelect(conversation.id)}>
              <span className="conversation-icon" aria-hidden="true">o</span>
              <span className="conversation-title">{conversation.title}</span>
            </button>
            <button
              className="conversation-delete"
              type="button"
              onClick={() => onDelete(conversation.id)}
              aria-label={`Delete ${conversation.title}`}
              title="Delete conversation"
            >x</button>
          </div>
        ))}
        {conversations.length === 0 && <p className="sidebar-empty">Your conversations will appear here.</p>}
      </div>
      <p className="sidebar-footnote">Conversations are saved to the server.</p>
    </aside>
  );
}
