"use client";

import { ChartPane } from "./ChartPane";
import { ChatPane } from "./ChatPane";
import { Sidebar } from "./Sidebar";
import { Topbar } from "./Topbar";
import { TransparencyDashboard } from "./TransparencyDashboard";

export function Dashboard() {
  return (
    <>
      <div className="flex h-screen items-center justify-center bg-bg-0 px-6 text-center font-mono text-[11px] uppercase tracking-[0.12em] text-text-2 min-[1100px]:hidden">
        Please use a wider screen to access OmniData.
      </div>
      <div className="hidden h-screen overflow-hidden bg-bg-0 text-text-0 min-[1100px]:block">
        <Topbar />
        <div className="grid h-[calc(100vh-38px)] grid-cols-[196px_minmax(0,1fr)_310px] overflow-hidden">
          <Sidebar />
          <ChatPane />
          <aside className="flex min-w-0 flex-col overflow-hidden border-l border-border-0 bg-bg-1">
            <ChartPane />
            <TransparencyDashboard />
          </aside>
        </div>
      </div>
    </>
  );
}
