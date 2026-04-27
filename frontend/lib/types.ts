// ── Campaigns ────────────────────────────────────────────────────────────────

export interface CampaignSummary {
  id: number;
  smartlead_id: string;
  name: string;
  status: "active" | "paused" | "completed" | "drafted";
  total_leads: number;
  health_score: number | null;
  root_cause: RootCause | null;
  audited_at: string | null;
  fetched_at: string | null;
}

export interface SequenceStep {
  id: number;
  campaign_id: number;
  step_number: number;
  subject: string | null;
  body: string | null;
  open_rate: number;
  reply_rate: number;
  word_count: number;
  cta_detected: string | null;
}

export interface ReplyCluster {
  category: ReplyCategory;
  count: number;
  percentage: number;
  themes: string[];
  samples: string[];
}

export interface AuditSnapshot {
  audited_at: string;
  health_score: number;
  open_rate: number;
  reply_rate: number;
  bounce_rate: number;
}

export interface CampaignDetail {
  campaign: CampaignSummary & {
    created_at: string;
    fetched_at: string | null;
  };
  latest_audit: FullAuditSnapshot | null;
  sequences: SequenceStep[];
  reply_clusters: ReplyCluster[];
}

export interface FullAuditSnapshot extends AuditSnapshot {
  id: number;
  campaign_id: number;
  root_cause: RootCause | null;
  root_cause_detail: string | null;
  step_dropoff: StepDropoff | null;
  subject_patterns: Record<string, unknown> | null;
}

export interface StepDropoff {
  dropoff_at_step: number | null;
  steps: Array<{
    step_number: number;
    open_rate: number;
    reply_rate: number;
  }>;
}

export interface SyncResult {
  synced: number;
  duration_ms: number;
}

// ── Audit ─────────────────────────────────────────────────────────────────────

export interface AuditFlag {
  campaign_id: number;
  name: string;
  root_cause?: RootCause;
  health_score?: number;
  open_rate?: number;
  reply_rate?: number;
  bounce_rate?: number;
  decaying?: boolean;
  error?: string;
}

export interface AuditRunResult {
  audit_id: string;
  campaigns_audited: number;
  flags: AuditFlag[];
}

export interface AuditHistoryResult {
  campaign_id: number;
  snapshots: AuditSnapshot[];
}

export interface CrossCampaignIntel {
  best_subject_styles: Array<{
    style: string;
    avg_open_rate: number;
  }>;
  top_reply_themes: Array<{
    theme: string;
    count: number;
    campaigns_affected: number;
  }>;
  worst_step_positions: Array<{
    step_number: number;
    avg_reply_rate: number;
    campaigns_affected: number;
  }>;
}

// ── Replies ───────────────────────────────────────────────────────────────────

export interface ClustersResult {
  campaign_id: number;
  total_replies: number;
  clusters: ReplyCluster[];
}

export interface ReclusterResult {
  clusters_updated: number;
}

// ── AI Optimize ───────────────────────────────────────────────────────────────

export interface DiagnoseResult {
  campaign_id: number;
  diagnosis: string;
  root_cause: RootCause;
  confidence: "high" | "medium" | "low";
  evidence: string[];
}

export interface RewriteResult {
  step_id: number;
  step_number: number;
  original: string | null;
  rewrite: string;
  subject_alternatives: string[];
  rationale: string;
}

export interface SavedRewrite {
  id: number;
  step_number: number;
  original: string | null;
  rewrite: string | null;
  suggestions: string[];
  model_used: string;
  generated_at: string;
}

export interface RewritesResult {
  campaign_id: number;
  rewrites: SavedRewrite[];
}

// ── Config ────────────────────────────────────────────────────────────────────

export interface Thresholds {
  open_rate_warn: number;
  open_rate_critical: number;
  reply_rate_warn: number;
  reply_rate_critical: number;
  bounce_rate_warn: number;
  bounce_rate_critical: number;
  cache_ttl_minutes: number;
}

export interface ThresholdUpdateResult {
  updated: boolean;
}

// ── Shared enums ──────────────────────────────────────────────────────────────

export type RootCause = "deliverability" | "subject" | "copy" | "targeting";

export type ReplyCategory =
  | "interested"
  | "price_objection"
  | "timing"
  | "wrong_person"
  | "not_relevant"
  | "competitor"
  | "other";
