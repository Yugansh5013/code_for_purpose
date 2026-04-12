import { cn, formatDelta } from "@/lib/utils";
import type { StatUpdate } from "@/lib/types";

interface StatCardProps {
  stat: StatUpdate;
}

export function StatCard({ stat }: StatCardProps) {
  return (
    <div className="rounded-[3px] border border-border-0 bg-bg-0 p-[9px]">
      <div className="truncate font-mono text-[8px] uppercase tracking-[0.1em] text-text-3">
        {stat.label}
      </div>
      <div className="mt-[5px] truncate font-mono text-[17px] font-medium text-[#e8edf5]">
        {stat.value}
      </div>
      <div
        className={cn(
          "mt-[4px] truncate font-mono text-[9px]",
          stat.delta_direction === "pos" && "text-green",
          stat.delta_direction === "neg" && "text-red",
          stat.delta_direction === "neutral" && "text-text-2"
        )}
      >
        {formatDelta(stat.delta, stat.delta_direction)}
      </div>
    </div>
  );
}
