import { EmptyState } from "./EmptyState";
import type { SemanticSubstitution } from "@/lib/types";

interface LanguageTabProps {
  substitutions?: SemanticSubstitution[];
  validationPassed?: boolean;
  validatorModel?: string;
  validatorLatencyMs?: number;
}

export function LanguageTab({
  substitutions,
  validationPassed,
  validatorModel,
  validatorLatencyMs
}: LanguageTabProps) {
  if (!substitutions?.length) {
    return <EmptyState>No jargon detected — response is clean.</EmptyState>;
  }

  return (
    <div className="font-mono">
      <div className="mb-2 text-[8px] uppercase tracking-[0.1em] text-text-3">
        {substitutions.length} TERMS REWRITTEN BY SEMANTIC VALIDATOR · NODE 3
      </div>

      {substitutions.map((substitution) => (
        <div
          key={`${substitution.original}-${substitution.location}`}
          className="mb-[5px] flex items-center gap-[7px] rounded-[3px] border border-border-0 bg-bg-0 px-2 py-[5px]"
        >
          <span className="text-[10px] text-red line-through">
            {substitution.original}
          </span>
          <span className="text-text-3">→</span>
          <span className="text-[10px] text-green">
            {substitution.replaced_with}
          </span>
          <span className="ml-auto text-[8px] text-text-3">
            {substitution.location}
          </span>
        </div>
      ))}

      <div className="mt-2 border border-border-0 bg-bg-0 px-2 py-[5px] text-[10px] text-text-3">
        validation_passed: {String(validationPassed ?? true)} · model:{" "}
        {validatorModel ?? "unknown"} · latency: {validatorLatencyMs ?? 0}ms
      </div>
    </div>
  );
}
