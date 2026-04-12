"use client";

import { useCallback } from "react";

import { postChat } from "@/lib/api";
import { createSessionId, useOmniDataStore } from "@/lib/store";
import type { ChatResponse, Message } from "@/lib/types";

interface SubmitChatOptions {
  message: string;
  clarificationAnswer?: string;
  userContent?: string;
}

export function useChatSubmit() {
  const sessionId = useOmniDataStore((state) => state.sessionId);
  const isLoading = useOmniDataStore((state) => state.isLoading);
  const addMessage = useOmniDataStore((state) => state.addMessage);
  const setLoading = useOmniDataStore((state) => state.setLoading);
  const setActiveTransparency = useOmniDataStore(
    (state) => state.setActiveTransparency
  );
  const setActiveChartData = useOmniDataStore(
    (state) => state.setActiveChartData
  );
  const setActiveStats = useOmniDataStore((state) => state.setActiveStats);
  const setChartPanels = useOmniDataStore((state) => state.setChartPanels);
  const setRagDocuments = useOmniDataStore((state) => state.setRagDocuments);
  const setWebResults = useOmniDataStore((state) => state.setWebResults);
  const setSalesforceRecords = useOmniDataStore((state) => state.setSalesforceRecords);

  const applyResponse = useCallback(
    (response: ChatResponse) => {
      if (response.type === "answer") {
        addMessage({
          id: response.message_id,
          role: "ai",
          content: response.answer.text,
          answer: response.answer,
          timestamp: new Date()
        });
        setActiveTransparency(response.answer.transparency);
        setActiveChartData(
          response.answer.branches.includes("sql")
            ? response.answer.chart_data ?? null
            : null
        );

        if (response.answer.stat_updates?.length) {
          setActiveStats(response.answer.stat_updates);
        }

        // Store multi-chart panels
        setChartPanels(response.answer.charts ?? []);

        // Store RAG documents
        setRagDocuments(response.answer.rag_documents ?? []);

        // Store web results
        setWebResults(response.answer.web_results ?? []);

        // Store Salesforce records
        setSalesforceRecords(response.answer.salesforce_records ?? []);

        return;
      }

      addMessage({
        id: response.message_id,
        role: "clarification",
        content: response.clarification.question,
        clarification: response.clarification,
        timestamp: new Date()
      });
    },
    [addMessage, setActiveChartData, setActiveStats, setActiveTransparency, setChartPanels, setRagDocuments, setWebResults, setSalesforceRecords]
  );

  const submitChat = useCallback(
    async ({ message, clarificationAnswer, userContent }: SubmitChatOptions) => {
      const trimmedMessage = message.trim();
      const trimmedUserContent = (userContent ?? message).trim();

      if (!trimmedUserContent || isLoading) {
        return;
      }

      const userMessage: Message = {
        id: createSessionId(),
        role: "user",
        content: trimmedUserContent,
        timestamp: new Date()
      };

      addMessage(userMessage);
      setLoading(true);

      try {
        const response = await postChat({
          session_id: sessionId,
          message: trimmedMessage,
          clarification_answer: clarificationAnswer
        });

        applyResponse(response);
      } catch (error) {
        console.error(error);
        addMessage({
          id: createSessionId(),
          role: "ai",
          content: "Something went wrong. Please try again.",
          timestamp: new Date()
        });
      } finally {
        setLoading(false);
      }
    },
    [addMessage, applyResponse, isLoading, sessionId, setLoading]
  );

  return { isLoading, submitChat };
}
