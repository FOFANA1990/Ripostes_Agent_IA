// Hook de données : charge le dashboard + la file d'événements et applique les décisions.
import { useCallback, useEffect, useState } from "react";
import { api, type DecisionPayload } from "../api";
import type { Dashboard, EventSummary } from "../types";

export function useMonitoring() {
  const [dashboard, setDashboard] = useState<Dashboard | null>(null);
  const [events, setEvents] = useState<EventSummary[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      setError(null);
      const [d, e] = await Promise.all([api.getDashboard(), api.listEvents()]);
      setDashboard(d);
      setEvents(e);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Erreur inconnue");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void refresh();
  }, [refresh]);

  const decide = useCallback(
    async (id: string, payload: DecisionPayload) => {
      await api.decide(id, payload);
      await refresh();
    },
    [refresh]
  );

  return { dashboard, events, loading, error, refresh, decide };
}
