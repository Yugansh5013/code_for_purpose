import { EmptyState } from "./EmptyState";
import { HighlightedCode } from "./HighlightedCode";
import { highlightPython } from "@/lib/utils";

interface CodeTabProps {
  code?: string;
}

export function CodeTab({ code }: CodeTabProps) {
  if (!code) {
    return <EmptyState>No visualisation code for this response</EmptyState>;
  }

  return <HighlightedCode tokens={highlightPython(code)} />;
}
