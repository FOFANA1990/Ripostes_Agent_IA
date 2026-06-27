import { useState } from "react";
import { Header } from "./components/Header";
import { KpiCards } from "./components/KpiCards";
import { TimelineChart } from "./components/TimelineChart";
import { AlertsFeed } from "./components/AlertsFeed";
import { ValidationQueue } from "./components/ValidationQueue";
import { RiposteDetail } from "./components/RiposteDetail";
import { useMonitoring } from "./hooks/useMonitoring";

export default function App() {
  const { dashboard, events, loading, error, decide } = useMonitoring();
  const [selectedId, setSelectedId] = useState<string | null>(null);

  return (
    <div className="min-h-screen bg-[#f3f4f8]">
      <Header provider={dashboard ? "agents actifs" : undefined} />

      <main className="mx-auto max-w-7xl space-y-4 p-4 md:p-6">
        {error && (
          <div className="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-700">
            Connexion à l'API impossible : {error}. Vérifie que le backend tourne sur le port 8000.
          </div>
        )}

        {loading && !dashboard && <p className="text-sm text-slate-500">Chargement du tableau de bord…</p>}

        {dashboard && (
          <>
            <KpiCards kpis={dashboard.kpis} />

            <div className="grid grid-cols-1 gap-4 lg:grid-cols-3">
              <div className="space-y-4 lg:col-span-2">
                <TimelineChart data={dashboard.timeline} />
                <ValidationQueue events={events} selectedId={selectedId} onSelect={setSelectedId} />
              </div>
              <div className="lg:col-span-1">
                <AlertsFeed alerts={dashboard.alerts} />
              </div>
            </div>
          </>
        )}
      </main>

      {selectedId && (
        <RiposteDetail eventId={selectedId} onClose={() => setSelectedId(null)} onDecide={decide} />
      )}
    </div>
  );
}
