import type { MetricResolution } from "@/lib/types";

interface ResolutionNoteProps {
  dateResolution?: string;
  metricResolution?: MetricResolution;
}

export function ResolutionNote({
  dateResolution,
  metricResolution
}: ResolutionNoteProps) {
  if (!dateResolution && !metricResolution) {
    return null;
  }

  return (
    <div className="my-[3px] space-y-1 font-mono text-[10px] tracking-[0.02em] text-text-3">
      {dateResolution ? <div>Resolved {dateResolution}</div> : null}
      {metricResolution ? (
        <div>
          Interpreting{" "}
          <span className="italic text-text-2">{metricResolution.alias}</span>{" "}
          as{" "}
          <span className="italic text-text-2">
            {metricResolution.display_name}
          </span>{" "}
          <span className="rounded-[2px] border border-blue-border bg-blue-dim px-[5px] py-px text-[8px] text-blue-text">
            {metricResolution.column_name}
          </span>
        </div>
      ) : null}
    </div>
  );
}
