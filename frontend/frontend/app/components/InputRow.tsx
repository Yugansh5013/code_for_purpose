"use client";

import { FormEvent, KeyboardEvent, useEffect, useRef, useState } from "react";
import { ArrowRight } from "lucide-react";

import { useChatSubmit } from "./useChatSubmit";

const hintChips = [
  "Revenue by region",
  "Churn risk accounts",
  "YTD sales vs target",
  "Refund policy summary",
  "Upload a CSV"
];

export function InputRow() {
  const [value, setValue] = useState("");
  const textareaRef = useRef<HTMLTextAreaElement | null>(null);
  const { isLoading, submitChat } = useChatSubmit();

  useEffect(() => {
    const handlePrefill = (event: Event) => {
      const query = (event as CustomEvent<string>).detail;

      if (typeof query === "string") {
        setValue(query);
        textareaRef.current?.focus();
      }
    };

    window.addEventListener("omnidata:prefill-query", handlePrefill);

    return () => {
      window.removeEventListener("omnidata:prefill-query", handlePrefill);
    };
  }, []);

  useEffect(() => {
    const textarea = textareaRef.current;

    if (!textarea) {
      return;
    }

    textarea.style.height = "0px";
    textarea.style.height = `${Math.min(textarea.scrollHeight, 110)}px`;
  }, [value]);

  const submit = (event?: FormEvent) => {
    event?.preventDefault();

    const nextValue = value.trim();

    if (!nextValue || isLoading) {
      return;
    }

    setValue("");
    submitChat({ message: nextValue });
  };

  const onKeyDown = (event: KeyboardEvent<HTMLTextAreaElement>) => {
    if (event.key === "Enter" && !event.shiftKey) {
      event.preventDefault();
      submit();
    }
  };

  return (
    <div className="border-t border-border-0 bg-bg-1">
      <div className="flex flex-wrap gap-[6px] px-[14px] pt-[9px]">
        {hintChips.map((chip) => (
          <button
            key={chip}
            type="button"
            className="rounded-[2px] border border-border-0 bg-bg-2 px-[9px] py-[3px] font-mono text-[9px] tracking-[0.04em] text-text-2 transition hover:border-border-1 hover:text-text-1"
            onClick={() => {
              setValue(chip);
              textareaRef.current?.focus();
            }}
          >
            {chip}
          </button>
        ))}
      </div>

      <form
        className="flex items-end gap-2 px-[14px] pb-[10px] pt-[8px]"
        onSubmit={submit}
      >
        <textarea
          ref={textareaRef}
          value={value}
          rows={1}
          placeholder="Ask your data in plain English..."
          className="max-h-[110px] min-h-[38px] flex-1 resize-none rounded-[4px] border border-border-0 bg-bg-0 px-3 py-[9px] font-sans text-[13px] leading-5 text-text-0 outline-none placeholder:text-text-3 focus:border-blue-border"
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={onKeyDown}
        />
        <button
          type="submit"
          disabled={!value.trim() || isLoading}
          className="flex h-[35px] w-[35px] flex-shrink-0 items-center justify-center rounded-[3px] border border-blue-border bg-blue-dim text-blue-text transition hover:bg-[#1e3a5c] disabled:cursor-not-allowed disabled:opacity-45"
          aria-label="Send query"
        >
          <ArrowRight size={13} />
        </button>
      </form>
    </div>
  );
}
