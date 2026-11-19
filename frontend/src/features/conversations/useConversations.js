import { useCallback, useEffect, useRef, useState } from "react";
import {
  createConversation as createConversationRequest,
  deleteConversation as deleteConversationRequest,
  getConversation,
  listConversations,
} from "../../services/conversationApi.js";

export default function useConversations() {
  const [conversations, setConversations] = useState([]);
  const [activeId, setActiveId] = useState(null);
  const [messagesState, setMessagesState] = useState({ conversationId: null, messages: [] });
  const [ready, setReady] = useState(false);
  const [creating, setCreating] = useState(false);
  const [error, setError] = useState("");
  const createInFlight = useRef(null);

  useEffect(() => {
    let cancelled = false;
    listConversations()
      .then((result) => {
        if (cancelled) return;
        const items = Array.isArray(result) ? result : [];
        setConversations(items);
        setActiveId((currentId) =>
          currentId && items.some((item) => item.id === currentId)
            ? currentId
            : items[0]?.id ?? null,
        );
      })
      .catch((requestError) => {
        if (!cancelled) setError(requestError.message);
      })
      .finally(() => {
        if (!cancelled) setReady(true);
      });

    return () => { cancelled = true; };
  }, []);

  useEffect(() => {
    if (!activeId) return undefined;

    let cancelled = false;
    getConversation(activeId)
      .then((conversation) => {
        if (cancelled) return;
        setMessagesState({
          conversationId: conversation.id,
          messages: conversation.messages || [],
        });
        setConversations((current) => current.map((item) =>
          item.id === conversation.id ? { ...item, ...conversation } : item,
        ));
      })
      .catch((requestError) => {
        if (!cancelled) {
          setError(requestError.message);
          setMessagesState({ conversationId: activeId, messages: [] });
        }
      });

    return () => { cancelled = true; };
  }, [activeId]);

  const createNewConversation = useCallback(() => {
    if (createInFlight.current) return createInFlight.current;
    setCreating(true);
    setError("");
    createInFlight.current = createConversationRequest()
      .then((conversation) => {
        setConversations((current) => [conversation, ...current]);
        setMessagesState({ conversationId: conversation.id, messages: [] });
        setActiveId(conversation.id);
        return conversation;
      })
      .catch((requestError) => {
        setError(requestError.message);
        return null;
      })
      .finally(() => {
        setCreating(false);
        createInFlight.current = null;
      });
    return createInFlight.current;
  }, []);

  const updateMessages = useCallback((conversationId, messages) => {
    setMessagesState((current) => current.conversationId === conversationId
      ? { conversationId, messages }
      : current,
    );
  }, []);

  const removeConversation = useCallback(async (conversationId) => {
    setError("");
    try {
      await deleteConversationRequest(conversationId);
      const remaining = conversations.filter((item) => item.id !== conversationId);
      setConversations(remaining);
      if (activeId === conversationId) {
        const nextId = remaining[0]?.id ?? null;
        setMessagesState({ conversationId: nextId, messages: [] });
        setActiveId(nextId);
      }
    } catch (requestError) {
      setError(requestError.message);
    }
  }, [activeId, conversations]);

  const activeConversation = conversations.find((item) => item.id === activeId) ?? null;
  const activeMessages = messagesState.conversationId === activeId
    ? messagesState.messages
    : [];
  const loadingMessages = Boolean(activeId && messagesState.conversationId !== activeId);
  const clearError = useCallback(() => setError(""), []);

  return {
    conversations,
    activeConversation,
    activeId,
    activeMessages,
    setActiveId,
    createConversation: createNewConversation,
    updateMessages,
    deleteConversation: removeConversation,
    ready,
    loadingMessages,
    creating,
    error,
    clearError,
  };
}
