import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { TimelinePoint } from "../types";

function dayTick(iso: string): string {
  const d = new Date(iso);
  return `${String(d.getDate()).padStart(2, "0")}/${String(d.getMonth() + 1).padStart(2, "0")}`;
}

export function TimelineChart({ data }: { data: TimelinePoint[] }) {
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm" aria-label="Propagation dans le temps">
      <h2 className="mb-3 text-sm font-semibold text-ink">Propagation — volume de posts par heure</h2>
      <div className="h-56 w-full">
        <ResponsiveContainer width="100%" height="100%">
          <AreaChart data={data} margin={{ top: 4, right: 8, bottom: 0, left: -16 }}>
            <defs>
              <linearGradient id="vol" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#3A86FF" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#3A86FF" stopOpacity={0} />
              </linearGradient>
            </defs>
            <XAxis
              dataKey="hour"
              tickFormatter={dayTick}
              minTickGap={48}
              tick={{ fontSize: 11, fill: "#64748b" }}
              stroke="#cbd5e1"
            />
            <YAxis tick={{ fontSize: 11, fill: "#64748b" }} stroke="#cbd5e1" />
            <Tooltip
              labelFormatter={(v) => new Date(v as string).toLocaleString("fr-FR")}
              formatter={(v) => [`${v as number} posts/h`, "Volume"]}
              contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 12 }}
            />
            <Area type="monotone" dataKey="volume" stroke="#3A86FF" strokeWidth={1.6} fill="url(#vol)" />
          </AreaChart>
        </ResponsiveContainer>
      </div>
    </section>
  );
}
