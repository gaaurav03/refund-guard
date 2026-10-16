import { useCallback, useRef, useState } from "react";
import { ApiError, api, friendlyMessage } from "../api/client";
import type { ChatMessage } from "../components/ChatPanel";
import type { Decision, SessionInfo } from "../types/decision";

/** What survives a page refresh: kept in this tab only (sessionStorage), never sent anywhere. */
interface Saved {
  key: string;
  messages: ChatMessage[];
  latest: Decision | null;
  left: number | null;
  blocked: string | null;
  session: SessionInfo | null;
}

const storageKey = (mode: string) => `rg-convo:${mode}`;
const convoKey = (customerId: string, gullible: boolean) => `${customerId}|${gullible}`;

function load(mode: string): Saved | null {
  try {
    const raw = sessionStorage.getItem(storageKey(mode));
    return raw ? (JSON.parse(raw) as Saved) : null;
  } catch {
    return null;
  }
}

function save(mode: string, s: Saved | null) {
  try {
    if (s) sessionStorage.setItem(storageKey(mode), JSON.stringify(s));
    else sessionStorage.removeItem(storageKey(mode));
  } catch {
    /* storage unavailable: the chat simply won't survive a refresh */
  }
}

/** The customer and mode of the conversation saved in this tab, if any (to restore the picker after a refresh). */
export function savedSelection(mode: "chat" | "challenge"): { customerId: string; gullible: boolean } | null {
  const s = load(mode);
  if (!s) return null;
  const [customerId, g] = s.key.split("|");
  return customerId ? { customerId, gullible: g === "true" } : null;
}

/** One customer conversation: lazily creates a backend session, sends messages, collects guard decisions. */
export function useConversation(mode: "chat" | "challenge") {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [busy, setBusy] = useState(false);
  const [blocked, setBlocked] = useState<string | null>(null);
  const [left, setLeft] = useState<number | null>(null);
  const [latest, setLatest] = useState<Decision | null>(null);
  const session = useRef<SessionInfo | null>(null);
  const key = useRef("");
  const snapshot = useRef<Saved | null>(null);

  const persist = useCallback(
    (patch: Partial<Saved>) => {
      const next: Saved = {
        key: key.current,
        messages: [],
        latest: null,
        left: null,
        blocked: null,
        session: session.current,
        ...snapshot.current,
        ...patch,
      };
      next.session = session.current;
      snapshot.current = next;
      save(mode, next);
    },
    [mode],
  );

  /** Switch to a customer/mode. Restores the saved chat for the same pair unless `fresh` is set. */
  const reset = useCallback(
    (customerId: string, gullible: boolean, fresh = false) => {
      const k = convoKey(customerId, gullible);
      key.current = k;
      const saved = fresh ? null : load(mode);
      if (saved && saved.key === k) {
        session.current = saved.session;
        snapshot.current = saved;
        setMessages(saved.messages);
        setLatest(saved.latest);
        setLeft(saved.left);
        setBlocked(saved.blocked);
        return;
      }
      session.current = null;
      snapshot.current = null;
      save(mode, null);
      setMessages([]);
      setBlocked(null);
      setLeft(null);
      setLatest(null);
    },
    [mode],
  );

  const send = useCallback(
    async (customerId: string, gullible: boolean, text: string) => {
      const myKey = convoKey(customerId, gullible);
      const sent: ChatMessage = { role: "user", text };
      setMessages((m) => {
        const next = [...m, sent];
        persist({ messages: next });
        return next;
      });
      setBusy(true);
      const notes: ChatMessage[] = [];
      try {
        if (!session.current) session.current = await api.createSession(customerId, mode, gullible);
        let r;
        try {
          r = await api.chat(session.current.session_id, text);
        } catch (e) {
          if (!(e instanceof ApiError && e.kind === "expired")) throw e;
          // The server forgot this chat (restart or 2-hour limit): continue in a new session, and say so.
          session.current = await api.createSession(customerId, mode, gullible);
          notes.push({ role: "system", text: "The earlier chat expired on the server, so the assistant starts fresh." });
          r = await api.chat(session.current.session_id, text);
        }
        if (key.current !== myKey) return; // persona or mode changed mid-request
        const reply = r;
        const last = reply.decisions[reply.decisions.length - 1];
        const isBlocked = reply.messages_left <= 0 ? "Message limit reached. Pick a persona to start again." : null;
        setMessages((m) => {
          const next = [...m, ...notes, { role: "bot" as const, text: reply.reply, decisions: reply.decisions }];
          persist({ messages: next, left: reply.messages_left, ...(last ? { latest: last } : {}), blocked: isBlocked });
          return next;
        });
        setLeft(reply.messages_left);
        if (last) setLatest(last);
        if (isBlocked) setBlocked(isBlocked);
      } catch (e) {
        setMessages((m) => {
          const next = [...m, ...notes, { role: "system" as const, text: friendlyMessage(e) }];
          persist({ messages: next });
          return next;
        });
        if (e instanceof ApiError && (e.kind === "rate_limited" || e.kind === "budget")) setBlocked(e.message);
        if (e instanceof ApiError && e.kind === "expired") session.current = null;
      } finally {
        setBusy(false);
      }
    },
    [mode, persist],
  );

  const select = useCallback(
    (d: Decision | null) => {
      setLatest(d);
      persist({ latest: d });
    },
    [persist],
  );

  return { messages, busy, blocked, left, latest, setLatest: select, reset, send };
}
