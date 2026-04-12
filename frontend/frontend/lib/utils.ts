import { clsx } from "clsx";
import { twMerge } from "tailwind-merge";

import type {
  BranchColour,
  BranchKey,
  ClassNameValue,
  ConfidenceTier,
  FormatCurrencyOptions,
  HighlightToken,
  StatDeltaDirection
} from "./types";

export function cn(...inputs: ClassNameValue[]): string {
  return twMerge(clsx(...inputs));
}

export function formatCurrency(
  value: number,
  options: FormatCurrencyOptions = {}
): string {
  const {
    currency = "GBP",
    compact = true,
    maximumFractionDigits = compact ? 1 : 0
  } = options;

  return new Intl.NumberFormat("en-GB", {
    style: "currency",
    currency,
    notation: compact ? "compact" : "standard",
    maximumFractionDigits
  }).format(value);
}

export function formatDelta(
  value: string,
  direction: StatDeltaDirection = "neutral"
): string {
  const trimmed = value.trim();

  if (
    trimmed.startsWith("▲") ||
    trimmed.startsWith("▼") ||
    trimmed.startsWith("-")
  ) {
    return trimmed;
  }

  if (direction === "pos") {
    return `▲ ${trimmed}`;
  }

  if (direction === "neg") {
    return `▼ ${trimmed}`;
  }

  return trimmed;
}

export function confidenceTier(score: number): ConfidenceTier {
  if (score >= 0.8) {
    return "green";
  }

  if (score >= 0.5) {
    return "amber";
  }

  return "red";
}

export function branchColour(branch: BranchKey): BranchColour {
  switch (branch) {
    case "sql":
      return {
        label: "SQL · SNOWFLAKE",
        bgClass: "bg-green-dim",
        textClass: "text-green",
        borderClass: "border-green-border",
        accentClass: "text-green"
      };
    case "rag_confluence":
      return {
        label: "RAG · CONFLUENCE",
        bgClass: "bg-amber-dim",
        textClass: "text-amber",
        borderClass: "border-amber-border",
        accentClass: "text-amber"
      };
    case "rag_salesforce":
      return {
        label: "SOQL · SALESFORCE",
        bgClass: "bg-blue-dim",
        textClass: "text-blue-text",
        borderClass: "border-blue-border",
        accentClass: "text-blue-text"
      };
    case "web":
      return {
        label: "WEB · TAVILY",
        bgClass: "bg-purple-dim",
        textClass: "text-purple",
        borderClass: "border-purple-border",
        accentClass: "text-purple"
      };
  }
}

export function highlightSql(code: string): HighlightToken[] {
  return tokenizeSyntax(
    code,
    /--[^\n]*|'(?:''|[^'])*'|\b(?:SELECT|FROM|WHERE|GROUP|BY|ORDER|BETWEEN|AND|LIMIT|AS|DESC|ASC|HAVING)\b|\b(?:SUM|AVG|COUNT|MIN|MAX)\b(?=\s*\()|\b[A-Z_][A-Z0-9_]*(?:\.[A-Z_][A-Z0-9_]*)+\b/gi,
    (token) => {
      const upper = token.toUpperCase();

      if (token.startsWith("--")) {
        return "text-text-2";
      }

      if (token.startsWith("'")) {
        return "text-amber";
      }

      if (/^(SUM|AVG|COUNT|MIN|MAX)$/i.test(token)) {
        return "text-purple";
      }

      if (token.includes(".")) {
        return "text-green";
      }

      if (
        [
          "SELECT",
          "FROM",
          "WHERE",
          "GROUP",
          "BY",
          "ORDER",
          "BETWEEN",
          "AND",
          "LIMIT",
          "AS",
          "DESC",
          "ASC",
          "HAVING"
        ].includes(upper)
      ) {
        return "text-blue-text";
      }

      return undefined;
    }
  );
}

export function highlightSoql(code: string): HighlightToken[] {
  return tokenizeSyntax(
    code,
    /'(?:\\'|[^'])*'|\b(?:SELECT|FROM|WHERE|ORDER|BY|LIMIT|AND|OR|DESC|ASC)\b|\b[A-Za-z_][A-Za-z0-9_]*__c\b|\b(?:Account|Opportunity|Contact|Lead|Case)\b/g,
    (token) => {
      const upper = token.toUpperCase();

      if (token.startsWith("'")) {
        return "text-amber";
      }

      if (token.endsWith("__c")) {
        return "text-amber";
      }

      if (["Account", "Opportunity", "Contact", "Lead", "Case"].includes(token)) {
        return "text-blue-text";
      }

      if (
        [
          "SELECT",
          "FROM",
          "WHERE",
          "ORDER",
          "BY",
          "LIMIT",
          "AND",
          "OR",
          "DESC",
          "ASC"
        ].includes(upper)
      ) {
        return "text-blue-text";
      }

      return undefined;
    }
  );
}

export function highlightPython(code: string): HighlightToken[] {
  return tokenizeSyntax(
    code,
    /#[^\n]*|"(?:\\"|[^"])*"|'(?:\\'|[^'])*'|\b(?:import|from|as|for|in|if|else|return|with|def|class)\b|\b[A-Za-z_][A-Za-z0-9_]*(?=\s*\()/g,
    (token) => {
      if (token.startsWith("#")) {
        return "text-text-2";
      }

      if (token.startsWith("'") || token.startsWith("\"")) {
        return "text-amber";
      }

      if (
        [
          "import",
          "from",
          "as",
          "for",
          "in",
          "if",
          "else",
          "return",
          "with",
          "def",
          "class"
        ].includes(token)
      ) {
        return "text-blue-text";
      }

      return "text-purple";
    }
  );
}

function tokenizeSyntax(
  code: string,
  pattern: RegExp,
  classify: (token: string) => string | undefined
): HighlightToken[] {
  const tokens: HighlightToken[] = [];
  let lastIndex = 0;
  let match: RegExpExecArray | null;

  pattern.lastIndex = 0;

  while ((match = pattern.exec(code)) !== null) {
    if (match.index > lastIndex) {
      tokens.push({ value: code.slice(lastIndex, match.index) });
    }

    tokens.push({
      value: match[0],
      className: classify(match[0])
    });
    lastIndex = pattern.lastIndex;
  }

  if (lastIndex < code.length) {
    tokens.push({ value: code.slice(lastIndex) });
  }

  return tokens;
}
