import { cn } from "@/lib/utils";

interface HealthScoreProps {
  score: number | null;
  size?: "sm" | "md" | "lg";
  showLabel?: boolean;
}

function getColor(score: number | null) {
  if (score === null) return { stroke: "#cbd5e1", text: "text-slate-400", bg: "bg-slate-50" };
  if (score >= 70) return { stroke: "#10b981", text: "text-emerald-600", bg: "bg-emerald-50" };
  if (score >= 40) return { stroke: "#f59e0b", text: "text-amber-600", bg: "bg-amber-50" };
  return { stroke: "#ef4444", text: "text-red-600", bg: "bg-red-50" };
}

const SIZES = {
  sm: { box: 44, r: 17, stroke: 4, fontSize: "text-xs" },
  md: { box: 56, r: 22, stroke: 5, fontSize: "text-sm" },
  lg: { box: 80, r: 32, stroke: 6, fontSize: "text-xl" },
};

export function HealthScore({ score, size = "md", showLabel = false }: HealthScoreProps) {
  const { box, r, stroke, fontSize } = SIZES[size];
  const circumference = 2 * Math.PI * r;
  const pct = score !== null ? Math.max(0, Math.min(100, score)) : 0;
  const offset = circumference - (pct / 100) * circumference;
  const { stroke: color, text } = getColor(score);
  const center = box / 2;

  return (
    <div className="flex flex-col items-center gap-1">
      <div className="relative flex items-center justify-center" style={{ width: box, height: box }}>
        <svg width={box} height={box} className="-rotate-90">
          <circle
            cx={center}
            cy={center}
            r={r}
            fill="none"
            stroke="#e2e8f0"
            strokeWidth={stroke}
          />
          <circle
            cx={center}
            cy={center}
            r={r}
            fill="none"
            stroke={color}
            strokeWidth={stroke}
            strokeLinecap="round"
            strokeDasharray={circumference}
            strokeDashoffset={score !== null ? offset : circumference}
            className="transition-all duration-700 ease-out"
          />
        </svg>
        <span className={cn("absolute font-bold tabular-nums", fontSize, text)}>
          {score !== null ? score : "—"}
        </span>
      </div>
      {showLabel && (
        <span className="text-xs text-slate-500">Health</span>
      )}
    </div>
  );
}
