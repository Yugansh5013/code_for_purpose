import { EmptyState } from "./EmptyState";
import { cn } from "@/lib/utils";
import type { ConfidenceScore, ConfidenceTier } from "@/lib/types";

interface ConfidenceTabProps {
  confidence?: ConfidenceScore;
}

const tierClasses: Record<ConfidenceTier, string> = {
  green: "text-green",
  amber: "text-amber",
  red: "text-red"
};

export function ConfidenceTab({ confidence }: ConfidenceTabProps) {
  if (!confidence) {
    return <EmptyState>No confidence data for this response</EmptyState>;
  }

  const signals = [
    { label: "Schema match", value: confidence.signals.schema_cosine },
    { label: "Retry score", value: confidence.signals.retry_score },
    { label: "Row sanity", value: confidence.signals.row_sanity }
  ];
  const tierClass = tierClasses[confidence.tier];

  return (
    <div className="font-mono">
      <div className={cn("text-[11px]", tierClass)}>
        ● CONFIDENCE: {confidence.score.toFixed(2)} —{" "}
        {confidence.tier.toUpperCase()}
      </div>

      <div className="mt-3 space-y-[7px]">
        {signals.map((signal) => (
          <div key={signal.label} className="flex items-center gap-2">
            <div className="w-[110px] font-sans text-[10px] text-text-1">
              {signal.label}
            </div>
            <div className="h-[2px] flex-1 bg-border-0">
              <div
                className={cn("h-full", tierClass.replace("text-", "bg-"))}
                style={{ width: `${Math.round(signal.value * 100)}%` }}
              />
            </div>
            <div className={cn("w-[30px] text-right text-[9px]", tierClass)}>
              {signal.value.toFixed(2)}
            </div>
          </div>
        ))}
      </div>

      <div className="mt-[6px] text-[10px] leading-[1.6] text-text-3">
        {confidence.explanation}
      </div>
      <div className="mt-[5px] text-[10px] leading-[1.6] text-text-3">
        (schema×0.4) + (retry×0.4) + (rows×0.2) ={" "}
        {confidence.score.toFixed(2)}
      </div>
    </div>
  );
}
