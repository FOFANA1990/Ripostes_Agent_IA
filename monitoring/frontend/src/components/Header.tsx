import { ShieldCheck } from "lucide-react";

export function Header({ provider }: { provider?: string }) {
  return (
    <header className="flex items-center justify-between border-b border-slate-200 bg-white px-6 py-4">
      <div className="flex items-center gap-3">
        <span className="grid h-10 w-10 place-items-center rounded-xl bg-ink text-white">
          <ShieldCheck size={20} aria-hidden />
        </span>
        <div>
          <h1 className="text-lg font-bold leading-tight text-ink">CNC — Veille & Riposte</h1>
          <p className="text-xs text-slate-500">Supervision humaine des ripostes proposées par les agents</p>
        </div>
      </div>
      <div className="flex items-center gap-2 text-xs text-slate-500">
        <span className="relative flex h-2.5 w-2.5">
          <span className="absolute inline-flex h-full w-full animate-ping rounded-full bg-emerald-400 opacity-75" />
          <span className="relative inline-flex h-2.5 w-2.5 rounded-full bg-emerald-500" />
        </span>
        Surveillance active{provider ? ` · ${provider}` : ""}
      </div>
    </header>
  );
}
