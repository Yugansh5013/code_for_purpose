"use client";

import { useChatSubmit } from "./useChatSubmit";
import type { ClarificationPayload } from "@/lib/types";

interface ClarificationCardProps {
  clarification: ClarificationPayload;
}

export function ClarificationCard({ clarification }: ClarificationCardProps) {
  const { isLoading, submitChat } = useChatSubmit();

  return (
    <div className="rounded-[4px] border border-blue-border bg-bg-1 px-[14px] py-3">
      <p className="font-sans text-[12px] leading-5 text-[#c8d8f0]">
        {highlightAmbiguousTerm(
          clarification.question,
          clarification.ambiguous_term
        )}
      </p>
      <div className="mt-3 flex flex-wrap gap-[7px]">
        {clarification.options.map((option) => (
          <button
            key={option}
            type="button"
            disabled={isLoading}
            className="rounded-[3px] border border-blue-border bg-blue-dim px-3 py-[5px] font-mono text-[9px] tracking-[0.04em] text-blue-text transition hover:bg-[#1e3a5c] disabled:cursor-not-allowed disabled:opacity-50"
            onClick={() =>
              submitChat({
                message: option,
                userContent: option,
                clarificationAnswer: option
              })
            }
          >
            {option}
          </button>
        ))}
      </div>
    </div>
  );
}

function highlightAmbiguousTerm(question: string, term: string) {
  const index = question.toLowerCase().indexOf(term.toLowerCase());

  if (index === -1) {
    return question;
  }

  return (
    <>
      {question.slice(0, index)}
      <strong className="font-semibold text-blue-text">
        {question.slice(index, index + term.length)}
      </strong>
      {question.slice(index + term.length)}
    </>
  );
}
