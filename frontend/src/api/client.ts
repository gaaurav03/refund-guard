// Typed wrappers for every backend route (docs/architecture.md section 4).
import type {
  ChatResponse,
  Decision,
  Health,
  Meta,
  Persona,
  Scoreboard,
  SessionInfo,
} from "../types/decision";

export type ApiErrorKind = "offline" | "rate_limited" | "budget" | "expired" | "unauthorized" | "invalid" | "server";

export class ApiError extends Error {
  constructor(
    public readonly kind: ApiErrorKind,
    message: string,
    public readonly status = 0,
  ) {
    super(message);
  }
}

export function errorKind(status: number): ApiErrorKind {
  if (status === 429) return "rate_limited";
  if (status === 503) return "budget";
  if (status === 404) return "expired";
  if (status === 401) return "unauthorized";
  if (status === 409 || status === 422) return "invalid";
  return "server";
}

export function friendlyMessage(e: unknown): string {
  if (!(e instanceof ApiError)) return "Something went wrong. Nothing was refunded.";
  switch (e.kind) {
    case "offline":
      return "The demo is asleep right now. Nothing was refunded.";
    case "rate_limited":
    case "budget":
    case "invalid":
    case "unauthorized":
      return e.message;
    case "expired":
      return "This session has expired. Start a new one.";
    default:
      return "Something went wrong on our side. Nothing was refunded.";
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      ...init,
      headers: { "content-type": "application/json", ...(init.headers ?? {}) },
    });
  } catch {
    throw new ApiError("offline", "The demo is offline.");
  }
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = (await res.json()) as { detail?: unknown };
      if (typeof body.detail === "string") detail = body.detail;
    } catch {
      /* not JSON */
    }
    throw new ApiError(errorKind(res.status), detail, res.status);
  }
  return (await res.json()) as T;
}

export const api = {
  health: () => request<Health>("/api/health"),
  meta: () => request<Meta>("/api/meta"),
  personas: () => request<Persona[]>("/api/personas"),
  createSession: (customer_id: string, mode: "chat" | "challenge", gullible: boolean) =>
    request<SessionInfo>("/api/sessions", {
      method: "POST",
      body: JSON.stringify({ customer_id, mode, gullible }),
    }),
  chat: (session_id: string, message: string) =>
    request<ChatResponse>("/api/chat", { method: "POST", body: JSON.stringify({ session_id, message }) }),
  live: (since = "") => request<Decision[]>(`/api/decisions/live?since=${encodeURIComponent(since)}`),
  scoreboard: () => request<Scoreboard>("/api/scoreboard"),
  reviews: (token: string) => request<Decision[]>("/api/review", { headers: { "x-reviewer-token": token } }),
  resolve: (token: string, decision_id: string, action: "approve" | "deny", amount: number | null, note: string) =>
    request<{ status: string; paid_amount: number }>(`/api/review/${encodeURIComponent(decision_id)}`, {
      method: "POST",
      headers: { "x-reviewer-token": token },
      body: JSON.stringify({ action, amount, note }),
    }),
};
