import { EmptyState } from "./EmptyState";
import { HighlightedCode } from "./HighlightedCode";
import { highlightSoql } from "@/lib/utils";

interface SoqlTabProps {
  soql?: string;
}

export function SoqlTab({ soql }: SoqlTabProps) {
  if (!soql) {
    return <EmptyState>No SOQL query for this response</EmptyState>;
  }

  return <HighlightedCode tokens={highlightSoql(soql)} />;
}
