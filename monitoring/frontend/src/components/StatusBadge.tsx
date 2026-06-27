import type { EventStatus } from "../types";

const MAP: Record<EventStatus, { label: string; cls: string }> = {
  pending: { label: "En attente", cls: "bg-slate-100 text-slate-700 ring-slate-200" },
  approved: { label: "Validée", cls: "bg-emerald-100 text-emerald-700 ring-emerald-200" },
  edited_approved: { label: "Éditée & validée", cls: "bg-emerald-100 text-emerald-700 ring-emerald-200" },
  rejected: { label: "Rejetée", cls: "bg-red-100 text-red-700 ring-red-200" },
  needs_factcheck: { label: "Fact-check demandé", cls: "bg-violet-100 text-violet-700 ring-violet-200" },
};

export function StatusBadge({ status }: { status: EventStatus }) {
  const m = MAP[status];
  return (
    <span className={`inline-flex rounded-full px-2.5 py-0.5 text-xs font-medium ring-1 ring-inset ${m.cls}`}>
      {m.label}
    </span>
  );
}
