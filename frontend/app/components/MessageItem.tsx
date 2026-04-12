import { BranchTags } from "./BranchTags";
import { ClarificationCard } from "./ClarificationCard";
import { ResolutionNote } from "./ResolutionNote";
import { SourceChips } from "./SourceChips";
import { ThinkingTrace } from "./ThinkingTrace";
import type { Message } from "@/lib/types";

interface MessageItemProps {
  message: Message;
}

export function MessageItem({ message }: MessageItemProps) {
  if (message.role === "system") {
    return (
      <div className="self-center font-mono text-[10px] tracking-[0.08em] text-text-3">
        {message.content}
      </div>
    );
  }

  if (message.role === "user") {
    return (
      <div className="flex justify-end">
        <div className="max-w-[78%] rounded-[8px_8px_2px_8px] border border-blue-border bg-blue-dim px-[13px] py-[9px] font-sans text-[13px] leading-[1.55] text-[#c8d8f0]">
          {message.content}
        </div>
      </div>
    );
  }

  if (message.role === "clarification" && message.clarification) {
    return (
      <div className="max-w-[78%]">
        <ClarificationCard clarification={message.clarification} />
      </div>
    );
  }

  if (!message.answer) {
    return (
      <div className="animate-ai-in max-w-[78%] rounded-[4px] border border-red-border bg-bg-1 px-[14px] py-3 font-sans text-[13px] leading-[1.65] text-text-0">
        {message.content}
      </div>
    );
  }

  return (
    <article className="animate-ai-in max-w-[92%] space-y-2">
      <div className="grid grid-cols-[1fr_auto] items-start gap-x-3">
        <BranchTags branches={message.answer.branches} />
        <ThinkingTrace trace={message.answer.trace} />
      </div>

      <ResolutionNote
        dateResolution={message.answer.date_resolution}
        metricResolution={message.answer.metric_resolution}
      />

      <div
        className="rounded-[4px] border border-border-0 bg-bg-1 px-[14px] py-3 font-sans text-[13px] leading-[1.65] text-text-0 [&_strong]:font-medium [&_strong]:text-[#e8edf5]"
        dangerouslySetInnerHTML={{ __html: message.answer.text }}
      />

      <SourceChips chips={message.answer.sources} />
    </article>
  );
}
