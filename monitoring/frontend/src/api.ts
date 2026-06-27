// Client API typé. Centralise les appels au backend FastAPI.
import type {
  Dashboard,
  DecisionAction,
  EventFull,
  EventSummary,
} from "./types";

const BASE = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function http<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...init,
  });
  if (!res.ok) {
    const detail = await res.json().catch(() => ({}));
    throw new Error(detail?.detail ?? `Erreur ${res.status}`);
  }
  return res.json() as Promise<T>;
}

export interface DecisionPayload {
  action: DecisionAction;
  edited_text?: string;
  reason?: string;
  operator?: string;
}

export const api = {
  getDashboard: () => http<Dashboard>("/api/dashboard"),
  listEvents: () => http<EventSummary[]>("/api/events"),
  getEvent: (id: string) => http<EventFull>(`/api/events/${id}`),
  decide: (id: string, payload: DecisionPayload) =>
    http<EventFull>(`/api/events/${id}/decision`, {
      method: "POST",
      body: JSON.stringify(payload),
    }),
};
