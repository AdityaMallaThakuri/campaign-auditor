import type {
  AuditHistoryResult,
  AuditRunResult,
  CampaignDetail,
  ClustersResult,
  CrossCampaignIntel,
  DiagnoseResult,
  ReclusterResult,
  RewriteResult,
  RewritesResult,
  SyncResult,
  Thresholds,
  ThresholdUpdateResult,
} from "./types";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const body = await res.text();
    let detail = body;
    try {
      detail = JSON.parse(body)?.detail ?? body;
    } catch {}
    throw new Error(`${res.status} ${res.statusText}: ${detail}`);
  }
  return res.json() as Promise<T>;
}

// ── Campaigns ────────────────────────────────────────────────────────────────

export function getCampaigns() {
  return request<{ campaigns: import("./types").CampaignSummary[] }>("/campaigns");
}

export function getCampaign(id: number) {
  return request<CampaignDetail>(`/campaigns/${id}`);
}

export function syncCampaigns() {
  return request<SyncResult>("/campaigns/sync", { method: "POST" });
}

// ── Audit ─────────────────────────────────────────────────────────────────────

export function runAudit(campaignIds?: number[]) {
  return request<AuditRunResult>("/audit/run", {
    method: "POST",
    body: JSON.stringify({ campaign_ids: campaignIds ?? null }),
  });
}

export function getAuditHistory(campaignId: number) {
  return request<AuditHistoryResult>(`/audit/history/${campaignId}`);
}

export function getCrossCampaignIntel() {
  return request<CrossCampaignIntel>("/audit/cross-campaign");
}

// ── Replies ───────────────────────────────────────────────────────────────────

export function getReplyCluster(campaignId: number) {
  return request<ClustersResult>(`/replies/${campaignId}/clusters`);
}

export function reclusterReplies(campaignId: number) {
  return request<ReclusterResult>(`/replies/${campaignId}/recluster`, {
    method: "POST",
  });
}

// ── AI Optimize ───────────────────────────────────────────────────────────────

export function diagnoseCampaign(campaignId: number) {
  return request<DiagnoseResult>("/optimize/diagnose", {
    method: "POST",
    body: JSON.stringify({ campaign_id: campaignId }),
  });
}

export function rewriteStep(
  campaignId: number,
  stepId: number,
  instruction?: string,
) {
  return request<RewriteResult>("/optimize/rewrite", {
    method: "POST",
    body: JSON.stringify({ campaign_id: campaignId, step_id: stepId, instruction }),
  });
}

export function getRewrites(campaignId: number) {
  return request<RewritesResult>(`/optimize/rewrites/${campaignId}`);
}

// ── Config ────────────────────────────────────────────────────────────────────

export function getThresholds() {
  return request<Thresholds>("/config/thresholds");
}

export function updateThresholds(data: Partial<Thresholds>) {
  return request<ThresholdUpdateResult>("/config/thresholds", {
    method: "POST",
    body: JSON.stringify(data),
  });
}
