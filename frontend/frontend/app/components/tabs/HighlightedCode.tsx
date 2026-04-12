import { cn } from "@/lib/utils";
import type { HighlightToken } from "@/lib/types";

interface HighlightedCodeProps {
  tokens: HighlightToken[];
}

export function HighlightedCode({ tokens }: HighlightedCodeProps) {
  return (
    <pre className="overflow-x-auto whitespace-pre font-mono text-[10px] leading-[1.75] text-text-1">
      {tokens.map((token, index) => (
        <span key={`${token.value}-${index}`} className={cn(token.className)}>
          {token.value}
        </span>
      ))}
    </pre>
  );
}
