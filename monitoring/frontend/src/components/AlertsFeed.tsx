import { SeverityBadge } from "./SeverityBadge";
import type { AlertItem } from "../types";

function hhmm(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")} ${String(
    d.getHours()
  ).padStart(2, "0")}:00`;
}

export function AlertsFeed({ alerts }: { alerts: AlertItem[] }) {
  const items = [...alerts].reverse();
  return (
    <section className="flex h-full flex-col rounded-xl border border-slate-200 bg-white p-4 shadow-sm" aria-label="Flux d'alertes">
      <h2 className="mb-3 text-sm font-semibold text-ink">Flux d'alertes</h2>
      <ul className="flex-1 space-y-2 overflow-y-auto pr-1" style={{ maxHeight: 360 }}>
        {items.length === 0 && <li className="text-sm text-slate-400">Aucune alerte.</li>}
        {items.map((a, i) => (
          <li key={i} className="flex items-start gap-2 rounded-lg border border-slate-100 bg-slate-50 p-2.5">
            <SeverityBadge level={a.level} />
            <div className="min-w-0">
              <p className="truncate text-xs font-medium text-slate-700">{a.message}</p>
              <p className="text-[11px] text-slate-400">{hhmm(a.ts)}</p>
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
