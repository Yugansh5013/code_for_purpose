import { EmptyState } from "./EmptyState";
import { cn } from "@/lib/utils";
import type { ContextChunk } from "@/lib/types";

interface ContextTabProps {
  chunks?: ContextChunk[];
}

export function ContextTab({ chunks }: ContextTabProps) {
  if (!chunks?.length) {
    return <EmptyState>No document context for this response</EmptyState>;
  }

  return (
    <div>
      {chunks.map((chunk) => (
        <article
          key={`${chunk.title}-${chunk.chunk_index}`}
          className="border-b border-border-0 py-2"
        >
          <div className="flex items-center gap-[6px]">
            <span
              className={cn(
                "rounded-[2px] px-[5px] py-[2px] font-mono text-[8px]",
                chunk.source_type === "confluence"
                  ? "bg-amber-dim text-amber"
                  : "bg-orange-dim text-orange"
              )}
            >
              {chunk.source_type === "confluence" ? "CONF" : "DOC"}
            </span>
            <span className="truncate font-sans text-[11px] font-medium text-text-0">
              {chunk.title}
            </span>
          </div>
          <p className="mt-[6px] font-sans text-[10px] leading-[1.6] text-text-1">
            {chunk.body}
          </p>
          <div className="mt-[6px] font-mono text-[9px] text-text-3">
            [{chunk.space_key ?? "UPLOAD"}] · Updated {chunk.updated_at} · chunk{" "}
            {chunk.chunk_index} of {chunk.total_chunks} · score:{" "}
            {chunk.score.toFixed(2)}
          </div>
        </article>
      ))}
    </div>
  );
}
