import { useCallback, useRef, useState } from "react";
import { ApiError, api, friendlyMessage } from "../api/client";
import type { ChatMessage } from "../components/ChatPanel";
import type { Decision, SessionInfo } from "../types/decision";

/** One customer conversation: lazily creates a backend session, sends messages, collects guard decisions. */
export function useConversation(mode: "chat" | "challenge") {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState<string | null>(null);
  const [left, setLeft] = useState<number | null>(null);
  const [latest, setLatest] = useState<Decision | null>(null);
  const session = useRef<SessionInfo | null>(null);
  const key = useRef("");

  const reset = useCallback((customerId: string, gullible: boolean) => {
    key.current = `${customerId}|${gullible}`;
    session.current = null;
    setMessages([]);
    setBlocked(null);
    setLeft(null);
    setLatest(null);
  }, []);

  const send = useCallback(
    async (customerId: string, gullible: boolean, text: string) => {
      const myKey = `${customerId}|${gullible}`;
      setMessages((m) => [...m, { role: "user", text }]);
      setBusy(true);
      try {
        if (!session.current) session.current = await api.createSession(customerId, mode, gullible);
        const r = await api.chat(session.current.session_id, text);
        if (key.current !== myKey) return; // persona or mode changed mid-request
        setMessages((m) => [...m, { role: "bot", text: r.reply, decisions: r.decisions }]);
        setLeft(r.messages_left);
        const last = r.decisions[r.decisions.length - 1];
        if (last) setLatest(last);
        if (r.messages_left <= 0) setBlocked("Message limit reached. Pick a persona to start again.");
      } catch (e) {
        setMessages((m) => [...m, { role: "system", text: friendlyMessage(e) }]);
        if (e instanceof ApiError && (e.kind === "rate_limited" || e.kind === "budget")) setBlocked(e.message);
        if (e instanceof ApiError && e.kind === "expired") session.current = null;
      } finally {
        setBusy(false);
      }
    },
    [mode],
  );

  return { messages, busy, blocked, left, latest, setLatest, reset, send };
}
