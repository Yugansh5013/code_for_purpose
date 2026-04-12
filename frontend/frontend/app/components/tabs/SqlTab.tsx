import { EmptyState } from "./EmptyState";
import { HighlightedCode } from "./HighlightedCode";
import { highlightSql } from "@/lib/utils";

interface SqlTabProps {
  sql?: string;
}

export function SqlTab({ sql }: SqlTabProps) {
  if (!sql) {
    return <EmptyState>No SQL query for this response</EmptyState>;
  }

  return <HighlightedCode tokens={highlightSql(sql)} />;
}
