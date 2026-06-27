// Types partagés avec l'API backend (miroir des schémas Pydantic).

export type Level = "faible" | "montee" | "crise";
export type EventStatus =
  | "pending"
  | "approved"
  | "edited_approved"
  | "rejected"
  | "needs_factcheck";
export type DecisionAction = "validate" | "edit" | "reject" | "factcheck";

export interface Kpis {
  events_detected: number;
  pending_validation: number;
  reach_cumule: number;
  peak_volume: number;
  total_posts: number;
  negative_share_pct: number;
}

export interface AlertItem {
  ts: string;
  level: Level;
  message: string;
}

export interface TimelinePoint {
  hour: string;
  volume: number;
}

export interface Dashboard {
  kpis: Kpis;
  timeline: TimelinePoint[];
  alerts: AlertItem[];
}

export interface Amplifier {
  handle: string;
  reprises: number;
}
export interface SourcePost {
  post_id: string;
  url: string;
  author: string;
  retweets: number;
  text: string;
}
export interface DetectedEvent {
  event_id: string;
  level: Level;
  window_start: string;
  window_end: string;
  peak_hour: string;
  peak_volume: number;
  total_volume: number;
  velocity_factor: number;
  trigger_reason: string;
  top_amplifiers: Amplifier[];
  source_posts: SourcePost[];
  sentiment_counts: Record<string, number>;
  narrative_hits: Record<string, number>;
}
export interface SituationReport {
  event_id: string;
  resume: string;
  narratif_dominant: string;
  justification_narratif: string;
  acteurs_cles: string[];
  tonalite: string;
  affirmations_a_verifier: string[];
  niveau_confiance: string;
  post_ids_source: string[];
}
export interface RiposteDraft {
  angle: string;
  canal: string;
  tonalite: string;
  brouillon: string;
  appui_factuel: string[];
  mises_en_garde: string[];
  validation_humaine_requise: boolean;
}
export interface EventSummary {
  id: string;
  event_id: string;
  level: Level;
  status: EventStatus;
  peak_hour: string;
  peak_volume: number;
  velocity_factor: number;
  detected_at: string;
  narratif_dominant: string;
  top_amplifiers: string[];
}
export interface EventFull {
  id: string;
  status: EventStatus;
  detected_at: string;
  event: DetectedEvent;
  report: SituationReport;
  riposte: RiposteDraft;
  edited?: boolean;
  decision?: { action: DecisionAction; reason?: string; operator: string };
}
