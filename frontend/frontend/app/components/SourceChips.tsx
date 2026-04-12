import { cn, confidenceTier } from "@/lib/utils";
import type { SourceChip, SourceType } from "@/lib/types";

interface SourceChipsProps {
  chips: SourceChip[];
}

const sourceLabels: Record<SourceType, string> = {
  snowflake: "Snowflake",
  confluence: "Confluence",
  salesforce: "Salesforce",
  tavily: "Tavily",
  upload: "Uploaded docs"
};

const sourceClasses: Record<SourceType, string> = {
  snowflake: "border-green-border bg-green-dim text-green",
  confluence: "border-amber-border bg-amber-dim text-amber",
  salesforce: "border-blue-border bg-blue-dim text-blue-text",
  tavily: "border-purple-border bg-purple-dim text-purple",
  upload: "border-orange-border bg-orange-dim text-orange"
};

const confidenceDotClasses = {
  green: "bg-green",
  amber: "bg-amber",
  red: "bg-red"
};

export function SourceChips({ chips }: SourceChipsProps) {
  if (!chips.length) {
    return null;
  }

  return (
    <div className="mt-2 flex flex-wrap gap-[5px]">
      {chips.map((chip) => {
        const showConfidence =
          chip.source_type === "snowflake" || chip.source_type === "salesforce";
        const tier =
          typeof chip.confidence === "number"
            ? confidenceTier(chip.confidence)
            : "amber";

        return (
          <span
            key={`${chip.source_type}-${chip.label}`}
            className={cn(
              "flex items-center gap-1 rounded-[3px] border px-[7px] py-[3px] font-mono text-[8px] tracking-[0.04em]",
              sourceClasses[chip.source_type]
            )}
          >
            {showConfidence ? (
              <span
                className={cn(
                  "h-[5px] w-[5px] rounded-full",
                  confidenceDotClasses[tier]
                )}
              />
            ) : null}
            {sourceLabels[chip.source_type]} · {chip.label}
          </span>
        );
      })}
    </div>
  );
}
