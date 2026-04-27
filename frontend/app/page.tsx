"use client";

import { useState, useEffect, useCallback } from "react";
import {
  RefreshCw,
  Play,
  BarChart3,
  AlertTriangle,
  CheckCircle2,
  Clock,
  ChevronRight,
  Inbox,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { Badge } from "@/components/ui/badge";
import { CampaignCard } from "@/components/CampaignCard";
import {
  getCampaigns,
  runAudit,
  syncCampaigns,
  getCrossCampaignIntel,
} from "@/lib/api";
import type {
  CampaignSummary,
  CrossCampaignIntel,
  AuditRunResult,
} from "@/lib/types";
import { cn } from "@/lib/utils";

// ── Stat card ────────────────────────────────────────────────────────────────

function StatCard({
  label,
  value,
  sub,
  icon: Icon,
  accent,
  loading,
}: {
  label: string;
  value: string | number;
  sub?: string;
  icon: React.ElementType;
  accent: string;
  loading?: boolean;
}) {
  if (loading) {
    return (
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <Skeleton className="h-4 w-24 mb-3" />
        <Skeleton className="h-8 w-16 mb-1" />
        <Skeleton className="h-3 w-32" />
      </div>
    );
  }
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-5">
      <div className="flex items-center justify-between mb-3">
        <span className="text-sm text-slate-500 font-medium">{label}</span>
        <div className={cn("p-2 rounded-lg", accent)}>
          <Icon className="h-4 w-4" />
        </div>
      </div>
      <p className="text-3xl font-bold text-slate-900 tabular-nums">{value}</p>
      {sub && <p className="text-xs text-slate-400 mt-1">{sub}</p>}
    </div>
  );
}

// ── Intel panel ──────────────────────────────────────────────────────────────

function IntelPanel({ intel }: { intel: CrossCampaignIntel }) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      {/* Subject styles */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-4">
          Subject line performance
        </h3>
        {intel.best_subject_styles.length === 0 ? (
          <p className="text-sm text-slate-400">Run an audit to see patterns.</p>
        ) : (
          <ul className="space-y-2">
            {intel.best_subject_styles.map((s) => (
              <li key={s.style} className="flex items-center justify-between">
                <span className="text-sm text-slate-700 capitalize">{s.style.replace("_", " ")}</span>
                <span className="text-sm font-semibold text-slate-900 tabular-nums">
                  {(s.avg_open_rate * 100).toFixed(1)}%
                </span>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Reply themes */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-4">
          Top reply themes
        </h3>
        {intel.top_reply_themes.length === 0 ? (
          <p className="text-sm text-slate-400">Run reply clustering to see themes.</p>
        ) : (
          <ul className="space-y-2">
            {intel.top_reply_themes.map((t) => (
              <li key={t.theme} className="flex items-center justify-between">
                <span className="text-sm text-slate-700 capitalize">{t.theme.replace("_", " ")}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900 tabular-nums">{t.count}</span>
                  <span className="text-xs text-slate-400">{t.campaigns_affected}c</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>

      {/* Worst steps */}
      <div className="rounded-xl border border-slate-200 bg-white p-5">
        <h3 className="text-sm font-semibold text-slate-900 mb-4">
          Weakest sequence steps
        </h3>
        {intel.worst_step_positions.length === 0 ? (
          <p className="text-sm text-slate-400">Run an audit to see step data.</p>
        ) : (
          <ul className="space-y-2">
            {intel.worst_step_positions.map((s) => (
              <li key={s.step_number} className="flex items-center justify-between">
                <span className="text-sm text-slate-700">Step {s.step_number}</span>
                <div className="flex items-center gap-2">
                  <span className="text-sm font-semibold text-slate-900 tabular-nums">
                    {(s.avg_reply_rate * 100).toFixed(2)}%
                  </span>
                  <span className="text-xs text-slate-400">{s.campaigns_affected}c</span>
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </div>
  );
}

// ── Audit toast ───────────────────────────────────────────────────────────────

function AuditResultBanner({ result, onDismiss }: { result: AuditRunResult; onDismiss: () => void }) {
  const critical = result.flags.filter(
    (f) => !f.error && (f.health_score ?? 100) < 40,
  );
  const errored = result.flags.filter((f) => !!f.error);

  return (
    <div className="rounded-xl border border-emerald-200 bg-emerald-50 px-5 py-4 flex items-start justify-between gap-4">
      <div className="flex items-start gap-3">
        <CheckCircle2 className="h-5 w-5 text-emerald-600 flex-shrink-0 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-emerald-900">
            Audit complete — {result.campaigns_audited} campaigns analysed
          </p>
          <p className="text-xs text-emerald-700 mt-0.5">
            {critical.length > 0
              ? `${critical.length} campaign${critical.length > 1 ? "s" : ""} flagged critical`
              : "No critical issues found"}
            {errored.length > 0 && ` · ${errored.length} failed`}
          </p>
        </div>
      </div>
      <button
        onClick={onDismiss}
        className="text-emerald-600 hover:text-emerald-800 text-sm font-medium flex-shrink-0"
      >
        Dismiss
      </button>
    </div>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function DashboardPage() {
  const [campaigns, setCampaigns] = useState<CampaignSummary[]>([]);
  const [intel, setIntel] = useState<CrossCampaignIntel | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [syncing, setSyncing] = useState(false);
  const [auditing, setAuditing] = useState(false);
  const [auditResult, setAuditResult] = useState<AuditRunResult | null>(null);
  const [filter, setFilter] = useState<"all" | "active" | "critical" | "unaudited">("all");

  const load = useCallback(async () => {
    try {
      setError(null);
      const [campaignsData, intelData] = await Promise.all([
        getCampaigns(),
        getCrossCampaignIntel(),
      ]);
      setCampaigns(campaignsData.campaigns);
      setIntel(intelData);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Failed to load campaigns");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  async function handleSync() {
    setSyncing(true);
    try {
      await syncCampaigns();
      await load();
    } finally {
      setSyncing(false);
    }
  }

  async function handleAudit() {
    setAuditing(true);
    setAuditResult(null);
    try {
      const result = await runAudit();
      setAuditResult(result);
      await load();
    } finally {
      setAuditing(false);
    }
  }

  // ── Derived stats ──
  const nonDrafted = campaigns.filter((c) => c.status !== "drafted");
  const audited = nonDrafted.filter((c) => c.health_score !== null);
  const avgHealth =
    audited.length > 0
      ? Math.round(audited.reduce((s, c) => s + (c.health_score ?? 0), 0) / audited.length)
      : null;
  const critical = audited.filter((c) => (c.health_score ?? 100) < 40);
  const unaudited = nonDrafted.filter((c) => c.health_score === null);

  // ── Filtered list ──
  const filtered = (() => {
    switch (filter) {
      case "active":    return nonDrafted.filter((c) => c.status === "active");
      case "critical":  return critical;
      case "unaudited": return unaudited;
      default:          return nonDrafted;
    }
  })();

  const FILTERS = [
    { key: "all",      label: "All",       count: nonDrafted.length },
    { key: "active",   label: "Active",    count: nonDrafted.filter((c) => c.status === "active").length },
    { key: "critical", label: "Critical",  count: critical.length },
    { key: "unaudited",label: "Unaudited", count: unaudited.length },
  ] as const;

  return (
    <div className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto max-w-7xl px-6 py-4 flex items-center justify-between gap-4">
          <div>
            <h1 className="text-xl font-bold text-slate-900">Campaign Audit</h1>
            <p className="text-sm text-slate-500 mt-0.5">
              Diagnose why cold email campaigns underperform
            </p>
          </div>
          <div className="flex items-center gap-2">
            <Button
              variant="outline"
              size="sm"
              onClick={handleSync}
              disabled={syncing || loading}
            >
              <RefreshCw className={cn("h-4 w-4", syncing && "animate-spin")} />
              {syncing ? "Syncing…" : "Sync"}
            </Button>
            <Button
              size="sm"
              onClick={handleAudit}
              disabled={auditing || loading}
            >
              <Play className={cn("h-4 w-4", auditing && "animate-pulse")} />
              {auditing ? "Auditing…" : "Run Audit"}
            </Button>
          </div>
        </div>
      </header>

      <main className="mx-auto max-w-7xl px-6 py-8 space-y-8">
        {/* Audit result banner */}
        {auditResult && (
          <AuditResultBanner
            result={auditResult}
            onDismiss={() => setAuditResult(null)}
          />
        )}

        {/* Error state */}
        {error && (
          <div className="rounded-xl border border-red-200 bg-red-50 px-5 py-4 flex items-center gap-3">
            <AlertTriangle className="h-5 w-5 text-red-500 flex-shrink-0" />
            <p className="text-sm text-red-700">{error}</p>
            <button
              className="ml-auto text-sm text-red-600 font-medium hover:text-red-800"
              onClick={load}
            >
              Retry
            </button>
          </div>
        )}

        {/* Stats row */}
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          <StatCard
            label="Total campaigns"
            value={loading ? "—" : nonDrafted.length}
            sub={loading ? undefined : `${campaigns.filter(c => c.status === "drafted").length} drafted`}
            icon={BarChart3}
            accent="bg-slate-100 text-slate-500"
            loading={loading}
          />
          <StatCard
            label="Avg health score"
            value={loading ? "—" : avgHealth !== null ? avgHealth : "—"}
            sub={loading ? undefined : audited.length > 0 ? `across ${audited.length} audited` : "Run an audit first"}
            icon={CheckCircle2}
            accent={
              avgHealth === null ? "bg-slate-100 text-slate-400"
              : avgHealth >= 70 ? "bg-emerald-100 text-emerald-600"
              : avgHealth >= 40 ? "bg-amber-100 text-amber-600"
              : "bg-red-100 text-red-600"
            }
            loading={loading}
          />
          <StatCard
            label="Critical campaigns"
            value={loading ? "—" : critical.length}
            sub={loading ? undefined : "Health score below 40"}
            icon={AlertTriangle}
            accent={critical.length > 0 ? "bg-red-100 text-red-500" : "bg-slate-100 text-slate-400"}
            loading={loading}
          />
          <StatCard
            label="Not yet audited"
            value={loading ? "—" : unaudited.length}
            sub={loading ? undefined : "Click Run Audit to analyse"}
            icon={Clock}
            accent="bg-blue-100 text-blue-500"
            loading={loading}
          />
        </div>

        {/* Filter tabs + campaign grid */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-base font-semibold text-slate-900">Campaigns</h2>
            <div className="flex items-center gap-1 bg-white border border-slate-200 rounded-lg p-1">
              {FILTERS.map(({ key, label, count }) => (
                <button
                  key={key}
                  onClick={() => setFilter(key)}
                  className={cn(
                    "px-3 py-1.5 rounded-md text-xs font-medium transition-colors",
                    filter === key
                      ? "bg-slate-900 text-white"
                      : "text-slate-600 hover:text-slate-900 hover:bg-slate-50",
                  )}
                >
                  {label}
                  <span className={cn(
                    "ml-1.5 tabular-nums",
                    filter === key ? "text-slate-400" : "text-slate-400",
                  )}>
                    {count}
                  </span>
                </button>
              ))}
            </div>
          </div>

          {loading ? (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {Array.from({ length: 8 }).map((_, i) => (
                <div key={i} className="rounded-xl border border-slate-200 bg-white p-5 space-y-3">
                  <Skeleton className="h-4 w-3/4" />
                  <Skeleton className="h-6 w-1/2" />
                  <Skeleton className="h-3 w-full" />
                  <Skeleton className="h-3 w-2/3" />
                </div>
              ))}
            </div>
          ) : filtered.length === 0 ? (
            <div className="flex flex-col items-center justify-center rounded-xl border border-dashed border-slate-300 bg-white py-16 text-center">
              <Inbox className="h-10 w-10 text-slate-300 mb-3" />
              <p className="text-sm font-medium text-slate-600">No campaigns here</p>
              <p className="text-xs text-slate-400 mt-1">
                {filter === "all" ? "Sync your Smartlead account to get started." : `No ${filter} campaigns.`}
              </p>
              {filter === "all" && (
                <Button variant="outline" size="sm" className="mt-4" onClick={handleSync}>
                  <RefreshCw className="h-4 w-4" />
                  Sync now
                </Button>
              )}
            </div>
          ) : (
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-4">
              {filtered.map((c) => (
                <CampaignCard key={c.id} campaign={c} />
              ))}
            </div>
          )}
        </section>

        {/* Cross-campaign intel */}
        {!loading && intel && (
          <section>
            <div className="flex items-center justify-between mb-4">
              <div>
                <h2 className="text-base font-semibold text-slate-900">Cross-campaign intelligence</h2>
                <p className="text-xs text-slate-500 mt-0.5">
                  Patterns aggregated across all audited campaigns
                </p>
              </div>
              <a
                href="#"
                className="text-xs text-slate-500 hover:text-slate-700 flex items-center gap-1"
              >
                View details <ChevronRight className="h-3 w-3" />
              </a>
            </div>
            <IntelPanel intel={intel} />
          </section>
        )}
      </main>
    </div>
  );
}
