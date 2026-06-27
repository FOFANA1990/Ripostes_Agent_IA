import { SeverityBadge } from "./SeverityBadge";
import { StatusBadge } from "./StatusBadge";
import type { EventSummary } from "../types";

interface Props {
  events: EventSummary[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export function ValidationQueue({ events, selectedId, onSelect }: Props) {
  const pending = events.filter((e) => e.status === "pending").length;
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm" aria-label="File de validation">
      <div className="mb-3 flex items-center justify-between">
        <h2 className="text-sm font-semibold text-ink">File de validation</h2>
        <span className="rounded-full bg-accent/10 px-2 py-0.5 text-xs font-semibold text-accent">
          {pending} en attente
        </span>
      </div>
      <ul className="space-y-2">
        {events.map((e) => {
          const selected = e.id === selectedId;
          return (
            <li key={e.id}>
              <button
                onClick={() => onSelect(e.id)}
                aria-pressed={selected}
                className={`w-full rounded-lg border p-3 text-left transition focus-visible:ring-2 ${
                  selected ? "border-brand bg-brand/5" : "border-slate-200 hover:border-slate-300 hover:bg-slate-50"
                }`}
              >
                <div className="flex items-center justify-between gap-2">
                  <div className="flex items-center gap-2">
                    <SeverityBadge level={e.level} />
                    <span className="text-xs font-mono text-slate-400">{e.event_id}</span>
                  </div>
                  <StatusBadge status={e.status} />
                </div>
                <p className="mt-2 text-sm font-medium text-ink">
                  Narratif : <span className="capitalize">{e.narratif_dominant}</span>
                </p>
                <p className="mt-0.5 text-xs text-slate-500">
                  Pic {e.peak_volume} posts/h (×{e.velocity_factor}) · {e.top_amplifiers.join(", ")}
                </p>
              </button>
            </li>
          );
        })}
      </ul>
    </section>
  );
}
