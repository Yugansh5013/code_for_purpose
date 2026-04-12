"use client";

import { useEffect, useRef } from "react";

import { MessageItem } from "./MessageItem";
import { TypingIndicator } from "./TypingIndicator";
import { useOmniDataStore } from "@/lib/store";

export function MessageList() {
  const messages = useOmniDataStore((state) => state.messages);
  const isLoading = useOmniDataStore((state) => state.isLoading);
  const scrollRef = useRef<HTMLDivElement | null>(null);
  const shouldAutoScrollRef = useRef(true);

  useEffect(() => {
    const element = scrollRef.current;

    if (!element || !shouldAutoScrollRef.current) {
      return;
    }

    element.scrollTop = element.scrollHeight;
  }, [messages.length, isLoading]);

  return (
    <div
      ref={scrollRef}
      className="flex flex-1 flex-col gap-[14px] overflow-y-auto px-4 py-[14px]"
      onScroll={(event) => {
        const element = event.currentTarget;
        const distanceFromBottom =
          element.scrollHeight - element.scrollTop - element.clientHeight;
        shouldAutoScrollRef.current = distanceFromBottom < 80;
      }}
    >
      {messages.length === 0 ? (
        <div className="mt-8 max-w-[560px] font-sans text-[13px] leading-6 text-text-2">
          Ask a plain-English question about revenue, returns, policy, accounts,
          or operational performance.
        </div>
      ) : null}

      {messages.map((message) => (
        <MessageItem key={message.id} message={message} />
      ))}

      {isLoading ? <TypingIndicator /> : null}
    </div>
  );
}
