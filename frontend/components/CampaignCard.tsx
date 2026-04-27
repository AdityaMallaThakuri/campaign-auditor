"use client";
import Link from "next/link";
import { TrendingDown, Mail, BarChart2 } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { HealthScore } from "@/components/HealthScore";
import { cn } from "@/lib/utils";
import type { CampaignSummary, RootCause } from "@/lib/types";

const ROOT_CAUSE_CONFIG: Record<RootCause, { label: string; variant: "destructive" | "warning" | "info" | "purple" }> = {
  deliverability: { label: "Deliverability", variant: "destructive" },
  subject:        { label: "Subject Line",   variant: "warning" },
  copy:           { label: "Copy",           variant: "info" },
  targeting:      { label: "Targeting",      variant: "purple" },
};

const STATUS_DOT: Record<string, string> = {
  active:    "bg-emerald-500",
  paused:    "bg-amber-400",
  completed: "bg-slate-400",
  drafted:   "bg-slate-300",
};

function fmt(n: number) {
  return (n * 100).toFixed(1) + "%";
}

interface Props {
  campaign: CampaignSummary;
}

export function CampaignCard({ campaign }: Props) {
  const cause = campaign.root_cause
    ? ROOT_CAUSE_CONFIG[campaign.root_cause]
    : null;

  const dotColor = STATUS_DOT[campaign.status] ?? "bg-slate-300";

  return (
    <Link
      href={`/campaigns/${campaign.id}`}
      className={cn(
        "group block rounded-xl border border-slate-200 bg-white p-5",
        "transition-all duration-150",
        "hover:border-slate-300 hover:shadow-md",
        "focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-900 focus-visible:ring-offset-2",
      )}
    >
      {/* Top row */}
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0 flex-1">
          <div className="flex items-center gap-2 mb-1">
            <span className={cn("h-2 w-2 rounded-full flex-shrink-0", dotColor)} />
            <span className="text-xs text-slate-500 capitalize">{campaign.status}</span>
          </div>
          <h3 className="font-semibold text-slate-900 leading-tight truncate pr-1">
            {campaign.name}
          </h3>
        </div>
        <HealthScore score={campaign.health_score} size="md" />
      </div>

      {/* Root cause badge */}
      <div className="mt-3 flex items-center gap-2 flex-wrap">
        {cause ? (
          <Badge variant={cause.variant}>{cause.label}</Badge>
        ) : (
          <Badge variant="outline" className="text-slate-400">Not audited</Badge>
        )}
        {campaign.health_score !== null && campaign.health_score < 40 && (
          <Badge variant="destructive">Critical</Badge>
        )}
      </div>

      {/* Divider */}
      <div className="my-3 border-t border-slate-100" />

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-3">
        <div className="flex items-center gap-2">
          <Mail className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
          <div>
            <p className="text-xs text-slate-500">Open rate</p>
            <p className="text-sm font-semibold text-slate-800 tabular-nums">
              {campaign.health_score !== null ? fmt(0) : "—"}
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <BarChart2 className="h-3.5 w-3.5 text-slate-400 flex-shrink-0" />
          <div>
            <p className="text-xs text-slate-500">Reply rate</p>
            <p className="text-sm font-semibold text-slate-800 tabular-nums">
              {campaign.health_score !== null ? fmt(0) : "—"}
            </p>
          </div>
        </div>
      </div>

      {/* Leads count + decay warning */}
      <div className="mt-3 flex items-center justify-between">
        <span className="text-xs text-slate-400">
          {campaign.total_leads > 0 ? `${campaign.total_leads.toLocaleString()} leads` : ""}
        </span>
        {campaign.health_score !== null && campaign.health_score < 40 && (
          <span className="flex items-center gap-1 text-xs text-red-500 font-medium">
            <TrendingDown className="h-3 w-3" />
            Needs attention
          </span>
        )}
      </div>
    </Link>
  );
}
