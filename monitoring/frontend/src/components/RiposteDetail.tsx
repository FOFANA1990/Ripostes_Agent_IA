import { useEffect, useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FileSearch, Pencil, X, XCircle } from "lucide-react";
import { api, type DecisionPayload } from "../api";
import type { EventFull } from "../types";
import { SeverityBadge } from "./SeverityBadge";
import { StatusBadge } from "./StatusBadge";

interface Props {
  eventId: string;
  onClose: () => void;
  onDecide: (id: string, payload: DecisionPayload) => Promise<void>;
}

export function RiposteDetail({ eventId, onClose, onDecide }: Props) {
  const [data, setData] = useState<EventFull | null>(null);
  const [draft, setDraft] = useState("");
  const [reason, setReason] = useState("");
  const [showReject, setShowReject] = useState(false);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const panelRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    let active = true;
    api
      .getEvent(eventId)
      .then((d) => {
        if (!active) return;
        setData(d);
        setDraft(d.riposte.brouillon);
      })
      .catch((e) => setError(e instanceof Error ? e.message : "Erreur"));
    return () => {
      active = false;
    };
  }, [eventId]);

  useEffect(() => {
    const onKey = (e: KeyboardEvent) => e.key === "Escape" && onClose();
    document.addEventListener("keydown", onKey);
    panelRef.current?.focus();
    return () => document.removeEventListener("keydown", onKey);
  }, [onClose]);

  async function run(payload: DecisionPayload) {
    setBusy(true);
    setError(null);
    try {
      await onDecide(eventId, payload);
      onClose();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Échec de l'action");
      setBusy(false);
    }
  }

  const dirty = data ? draft.trim() !== data.riposte.brouillon.trim() : false;
  const decided = data ? data.status !== "pending" : false;

  return (
    <div className="fixed inset-0 z-40" role="dialog" aria-modal="true" aria-label="Détail de la riposte">
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} aria-hidden />
      <div
        ref={panelRef}
        tabIndex={-1}
        className="absolute inset-y-0 right-0 flex w-full max-w-xl flex-col overflow-y-auto bg-white shadow-2xl outline-none"
      >
        {!data ? (
          <div className="p-6 text-sm text-slate-500">{error ?? "Chargement…"}</div>
        ) : (
          <>
            <div className="flex items-start justify-between border-b border-slate-200 p-5">
              <div className="flex items-center gap-2">
                <SeverityBadge level={data.event.level} />
                <StatusBadge status={data.status} />
                <span className="font-mono text-xs text-slate-400">{data.event.event_id}</span>
              </div>
              <button onClick={onClose} aria-label="Fermer" className="rounded-md p-1 text-slate-400 hover:bg-slate-100">
                <X size={18} />
              </button>
            </div>

            <div className="space-y-5 p-5">
              {/* Fiche de situation */}
              <section>
                <h3 className="mb-2 text-xs font-bold uppercase tracking-wide text-slate-400">Fiche de situation</h3>
                <p className="text-sm text-slate-700">{data.report.resume}</p>
                <dl className="mt-3 grid grid-cols-2 gap-3 text-sm">
                  <div>
                    <dt className="text-xs text-slate-400">Narratif dominant</dt>
                    <dd className="font-medium capitalize text-ink">{data.report.narratif_dominant}</dd>
                  </div>
                  <div>
                    <dt className="text-xs text-slate-400">Tonalité</dt>
                    <dd className="font-medium text-ink">{data.report.tonalite}</dd>
                  </div>
                </dl>
                <div className="mt-3">
                  <dt className="text-xs text-slate-400">Amplificateurs</dt>
                  <dd className="mt-1 flex flex-wrap gap-1.5">
                    {data.event.top_amplifiers.slice(0, 6).map((a) => (
                      <span key={a.handle} className="rounded-md bg-slate-100 px-2 py-0.5 text-xs text-slate-700">
                        {a.handle} · {a.reprises}
                      </span>
                    ))}
                  </dd>
                </div>
                {data.report.affirmations_a_verifier.length > 0 && (
                  <div className="mt-3 rounded-lg border border-amber-200 bg-amber-50 p-3">
                    <p className="flex items-center gap-1.5 text-xs font-semibold text-amber-800">
                      <AlertTriangle size={14} /> À vérifier avant diffusion
                    </p>
                    <ul className="mt-1.5 list-inside list-disc space-y-1 text-xs text-amber-900">
                      {data.report.affirmations_a_verifier.slice(0, 3).map((c, i) => (
                        <li key={i} className="break-words">{c}</li>
                      ))}
                    </ul>
                  </div>
                )}
              </section>

              {/* Brouillon de riposte éditable */}
              <section>
                <div className="mb-2 flex items-center justify-between">
                  <h3 className="text-xs font-bold uppercase tracking-wide text-slate-400">Brouillon de riposte</h3>
                  <span className="text-xs text-slate-400">Canal : {data.riposte.canal}</span>
                </div>
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  disabled={decided || busy}
                  rows={5}
                  aria-label="Brouillon de riposte (éditable)"
                  className="w-full resize-y rounded-lg border border-slate-300 p-3 text-sm text-ink focus:border-brand"
                />
                <p className="mt-1.5 text-xs text-slate-400">
                  Appui factuel : {data.riposte.appui_factuel.join(" · ")}
                </p>
              </section>

              {error && <p className="rounded-lg bg-red-50 p-2 text-sm text-red-700">{error}</p>}
            </div>

            {/* Barre de décision */}
            {!decided && (
              <div className="sticky bottom-0 mt-auto border-t border-slate-200 bg-white p-4">
                {showReject ? (
                  <div className="space-y-2">
                    <label htmlFor="reason" className="text-xs font-medium text-slate-600">
                      Motif du rejet (obligatoire)
                    </label>
                    <textarea
                      id="reason"
                      value={reason}
                      onChange={(e) => setReason(e.target.value)}
                      rows={2}
                      className="w-full rounded-lg border border-slate-300 p-2 text-sm focus:border-red-400"
                    />
                    <div className="flex gap-2">
                      <button
                        disabled={busy || !reason.trim()}
                        onClick={() => run({ action: "reject", reason })}
                        className="flex-1 rounded-lg bg-red-600 px-3 py-2 text-sm font-semibold text-white disabled:opacity-50"
                      >
                        Confirmer le rejet
                      </button>
                      <button onClick={() => setShowReject(false)} className="rounded-lg border border-slate-300 px-3 py-2 text-sm">
                        Annuler
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 gap-2">
                    <button
                      disabled={busy}
                      onClick={() => run(dirty ? { action: "edit", edited_text: draft } : { action: "validate" })}
                      className="col-span-2 flex items-center justify-center gap-2 rounded-lg bg-emerald-600 px-3 py-2.5 text-sm font-semibold text-white hover:bg-emerald-700 disabled:opacity-50"
                    >
                      {dirty ? <Pencil size={16} /> : <CheckCircle2 size={16} />}
                      {dirty ? "Éditer puis valider" : "Valider / Publier"}
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => setShowReject(true)}
                      className="flex items-center justify-center gap-1.5 rounded-lg border border-red-300 px-3 py-2 text-sm font-medium text-red-700 hover:bg-red-50"
                    >
                      <XCircle size={16} /> Rejeter
                    </button>
                    <button
                      disabled={busy}
                      onClick={() => run({ action: "factcheck" })}
                      className="flex items-center justify-center gap-1.5 rounded-lg border border-violet-300 px-3 py-2 text-sm font-medium text-violet-700 hover:bg-violet-50"
                    >
                      <FileSearch size={16} /> Fact-check
                    </button>
                  </div>
                )}
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
}
