import type { Level } from "../types";

const MAP: Record<Level, { label: string; cls: string }> = {
  faible: { label: "Faible", cls: "bg-amber-100 text-amber-800 ring-amber-200" },
  montee: { label: "Montée", cls: "bg-orange-100 text-orange-800 ring-orange-200" },
  crise: { label: "Crise", cls: "bg-red-100 text-red-700 ring-red-200" },
};

export function SeverityBadge({ level }: { level: Level }) {
  const m = MAP[level];
  return (
    <span
      className={`inline-flex items-center gap-1 rounded-full px-2.5 py-0.5 text-xs font-semibold ring-1 ring-inset ${m.cls}`}
    >
      <span className="h-1.5 w-1.5 rounded-full bg-current" aria-hidden />
      {m.label}
    </span>
  );
}
