import {
  MOCK_CLARIFICATION,
  MOCK_METRICS,
  MOCK_RESPONSE_1,
  MOCK_STATUS
} from "./mockData";
import type {
  ChatRequest,
  ChatResponse,
  IntegrationStatus,
  MetricsResponse
} from "./types";

const DEFAULT_API_URL = "http://localhost:8000";

function apiBaseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL ?? DEFAULT_API_URL;
}

function useMockApi(): boolean {
  return process.env.NEXT_PUBLIC_USE_MOCK === "true";
}

async function requestJson<T>(
  path: string,
  init?: RequestInit
): Promise<T> {
  const response = await fetch(`${apiBaseUrl()}${path}`, {
    ...init,
    headers: {
      "Content-Type": "application/json",
      ...init?.headers
    }
  });

  if (!response.ok) {
    throw new Error(`Request failed: ${response.status} ${response.statusText}`);
  }

  return response.json() as Promise<T>;
}

export async function postChat(payload: ChatRequest): Promise<ChatResponse> {
  if (useMockApi()) {
    await waitForMockLatency();

    if (
      payload.message.toLowerCase().includes("performance") &&
      !payload.clarification_answer
    ) {
      return MOCK_CLARIFICATION;
    }

    return MOCK_RESPONSE_1;
  }

  return requestJson<ChatResponse>("/api/chat", {
    method: "POST",
    body: JSON.stringify(payload)
  });
}

export async function getMetrics(): Promise<MetricsResponse> {
  if (useMockApi()) {
    return MOCK_METRICS;
  }

  return requestJson<MetricsResponse>("/api/metrics");
}

export async function getStatus(): Promise<IntegrationStatus> {
  if (useMockApi()) {
    return MOCK_STATUS;
  }

  return requestJson<IntegrationStatus>("/api/status");
}

function waitForMockLatency(): Promise<void> {
  return new Promise((resolve) => {
    setTimeout(resolve, 450);
  });
}
