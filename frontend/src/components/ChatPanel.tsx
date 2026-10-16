import { useEffect, useRef, useState, type FormEvent } from "react";
import { OutcomeChip } from "./OutcomeChip";
import type { Decision } from "../types/decision";

export interface ChatMessage {
  role: "user" | "bot" | "system";
  text: string;
  decisions?: Decision[];
}

export function ChatPanel({
  messages,
  busy,
  disabled,
  placeholder,
  onSend,
  onSelectDecision,
  suggestions = [],
}: {
  messages: ChatMessage[];
  busy: boolean;
  disabled?: string | null;
  placeholder: string;
  onSend: (text: string) => void;
  onSelectDecision?: (d: Decision) => void;
  suggestions?: string[];
}) {
  const [text, setText] = useState("");
  const end = useRef<HTMLDivElement>(null);
  // Braces matter: newer Chromium returns a Promise from scrollIntoView, and React would call it as a cleanup.
  useEffect(() => {
    end.current?.scrollIntoView?.({ behavior: "smooth", block: "end" });
  }, [messages, busy]);

  const submit = (e?: FormEvent) => {
    e?.preventDefault();
    const t = text.trim();
    if (!t || busy || disabled) return;
    setText("");
    onSend(t);
  };

  return (
    <div className="card flex h-full min-h-[420px] flex-col">
      <div className="flex-1 space-y-4 overflow-y-auto p-4" aria-live="polite">
        {messages.length === 0 && suggestions.length > 0 && (
          <div className="space-y-2">
            <p className="label">try one of these</p>
            {suggestions.map((s) => (
              <button
                key={s}
                type="button"
                onClick={() => !disabled && onSend(s)}
                className="block w-full rounded-lg border border-dashed border-hairline px-3 py-2 text-left text-sm text-muted hover:border-accent/50 hover:text-ink"
              >
                {s}
              </button>
            ))}
          </div>
        )}
        {messages.map((m, i) =>
          m.role === "system" ? (
            <p key={i} className="text-center font-mono text-[11px] text-muted">{m.text}</p>
          ) : (
            <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
              <div
                className={`max-w-[85%] whitespace-pre-wrap rounded-2xl px-4 py-2.5 text-[14px] leading-relaxed ${
                  m.role === "user" ? "bg-ink text-bg" : "border border-hairline bg-bg"
                }`}
              >
                {m.text}
                {m.decisions?.map((d) => (
                  <button
                    key={d.decision_id}
                    type="button"
                    onClick={() => onSelectDecision?.(d)}
                    className="mt-2 flex w-full items-center justify-between gap-2 rounded-lg border border-hairline bg-surface px-2.5 py-1.5 text-left"
                    title="See why"
                  >
                    <OutcomeChip outcome={d.outcome} amount={d.approved_amount} size="sm" />
                    <span className="font-mono text-[10px] text-muted">why? →</span>
                  </button>
                ))}
              </div>
            </div>
          ),
        )}
        {busy && (
          <div className="flex justify-start">
            <div className="rounded-2xl border border-hairline bg-bg px-4 py-2.5 font-mono text-[12px] text-muted">
              <span className="cursor">thinking · checking evidence</span>
            </div>
          </div>
        )}
        <div ref={end} />
      </div>
      <form onSubmit={submit} className="flex gap-2 border-t border-hairline p-3">
        <label htmlFor="chat-input" className="sr-only">Message</label>
        <input
          id="chat-input"
          value={text}
          onChange={(e) => setText(e.target.value)}
          maxLength={1000}
          placeholder={disabled ?? placeholder}
          disabled={!!disabled}
          className="min-h-[44px] flex-1 rounded-[10px] border border-hairline bg-bg px-3 text-[14px] placeholder:text-muted/80 focus:border-accent/60 focus:outline-none disabled:opacity-60"
        />
        <button type="submit" className="btn-primary px-4" disabled={busy || !!disabled || !text.trim()} aria-label="Send">
          ↵
        </button>
      </form>
    </div>
  );
}
