import type { Kpis } from "../types";

function fmt(n: number): string {
  return n.toLocaleString("fr-FR");
}

export function KpiCards({ kpis }: { kpis: Kpis }) {
  const cards = [
    { label: "Événements détectés", value: fmt(kpis.events_detected), accent: "text-ink" },
    { label: "En attente de validation", value: fmt(kpis.pending_validation), accent: "text-accent" },
    { label: "Reach cumulé", value: fmt(kpis.reach_cumule), accent: "text-brand" },
    { label: "Pic (posts/h)", value: fmt(kpis.peak_volume), accent: "text-ink" },
    { label: "Posts analysés", value: fmt(kpis.total_posts), accent: "text-ink" },
    { label: "Sentiment négatif", value: `${kpis.negative_share_pct}%`, accent: "text-ink" },
  ];
  return (
    <div className="grid grid-cols-2 gap-3 md:grid-cols-3 xl:grid-cols-6">
      {cards.map((c) => (
        <div key={c.label} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
          <div className={`text-2xl font-bold ${c.accent}`}>{c.value}</div>
          <div className="mt-1 text-xs font-medium text-slate-500">{c.label}</div>
        </div>
      ))}
    </div>
  );
}
