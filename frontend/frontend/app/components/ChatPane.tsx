"use client";

import { InputRow } from "./InputRow";
import { MessageList } from "./MessageList";
import { MetricsGlossary } from "./MetricsGlossary";
import { useOmniDataStore } from "@/lib/store";

export function ChatPane() {
  const activeNav = useOmniDataStore((state) => state.activeNav);

  if (activeNav === "glossary") {
    return <MetricsGlossary />;
  }

  return (
    <section className="flex min-w-0 flex-1 flex-col overflow-hidden bg-bg-0">
      <MessageList />
      <InputRow />
    </section>
  );
}
