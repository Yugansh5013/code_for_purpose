import { branchColour, cn } from "@/lib/utils";
import type { BranchKey } from "@/lib/types";

interface BranchTagsProps {
  branches: BranchKey[];
}

export function BranchTags({ branches }: BranchTagsProps) {
  if (!branches.length) {
    return null;
  }

  return (
    <div className="flex flex-wrap gap-[5px]">
      {branches.map((branch) => {
        const colour = branchColour(branch);

        return (
          <span
            key={branch}
            className={cn(
              "rounded-[2px] border px-[7px] py-[2px] font-mono text-[9px] tracking-[0.04em]",
              colour.bgClass,
              colour.textClass,
              colour.borderClass
            )}
          >
            {colour.label}
          </span>
        );
      })}
    </div>
  );
}
