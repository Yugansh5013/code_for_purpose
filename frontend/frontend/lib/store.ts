import { create } from "zustand";

import type { IntegrationStatus, OmniDataStore, StatUpdate } from "./types";

export const DEFAULT_INTEGRATION_STATUS: IntegrationStatus = {
  snowflake: "live",
  confluence: "syncing",
  salesforce: "live",
  tavily: "live"
};

export const DEFAULT_STATS: StatUpdate[] = [
  {
    label: "Return Rate",
    value: "4.2%",
    delta: "▲ +1.4pp QoQ",
    delta_direction: "neg"
  },
  {
    label: "Q1 Total Sales",
    value: "£3.8M",
    delta: "▼ −11%",
    delta_direction: "neg"
  },
  {
    label: "High-Risk Accts",
    value: "3",
    delta: "▲ 2 new",
    delta_direction: "neg"
  }
];

export function createSessionId(): string {
  const cryptoRef = globalThis.crypto;

  if (typeof cryptoRef?.randomUUID === "function") {
    return cryptoRef.randomUUID();
  }

  const bytes = new Uint8Array(16);

  if (typeof cryptoRef?.getRandomValues === "function") {
    cryptoRef.getRandomValues(bytes);
  } else {
    for (let index = 0; index < bytes.length; index += 1) {
      bytes[index] = Math.floor(Math.random() * 256);
    }
  }

  bytes[6] = (bytes[6] & 0x0f) | 0x40;
  bytes[8] = (bytes[8] & 0x3f) | 0x80;

  const hex = Array.from(bytes, (byte) => byte.toString(16).padStart(2, "0"));

  return [
    hex.slice(0, 4).join(""),
    hex.slice(4, 6).join(""),
    hex.slice(6, 8).join(""),
    hex.slice(8, 10).join(""),
    hex.slice(10, 16).join("")
  ].join("-");
}

export const useOmniDataStore = create<OmniDataStore>()((set) => ({
  sessionId: createSessionId(),
  resetSession: () =>
    set({
      sessionId: createSessionId(),
      messages: [],
      activeTransparency: null,
      activeChartData: null,
      activeStats: []
    }),

  messages: [],
  addMessage: (msg) =>
    set((state) => ({
      messages: [...state.messages, msg]
    })),
  clearMessages: () => set({ messages: [] }),

  isLoading: false,
  setLoading: (v) => set({ isLoading: v }),

  activeTransparency: null,
  setActiveTransparency: (t) => set({ activeTransparency: t }),

  activeChartData: null,
  setActiveChartData: (c) => set({ activeChartData: c }),

  activeStats: DEFAULT_STATS,
  setActiveStats: (s) => set({ activeStats: s }),

  integrationStatus: DEFAULT_INTEGRATION_STATUS,
  setIntegrationStatus: (s) => set({ integrationStatus: s }),

  activeNav: "chat",
  setActiveNav: (n) => set({ activeNav: n })
}));
