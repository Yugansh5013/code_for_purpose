import Link from 'next/link';

export default function LandingPage() {
  return (
    <div className="bg-surface text-on-surface overflow-x-hidden min-h-screen">
      {/* Top Navigation */}
      <header className="fixed top-0 w-full z-50 bg-inherit/80 dark:bg-slate-900/80 backdrop-blur-xl shadow-[0px_20px_40px_rgba(42,52,53,0.06)]">
        <div className="flex justify-between items-center px-12 py-6 max-w-screen-2xl mx-auto">
          <div className="text-2xl font-bold tracking-tighter text-slate-800 dark:text-slate-100 font-headline">OmniData</div>
          <nav className="hidden md:flex items-center space-x-10">
            <a href="#how-it-works" className="font-semibold text-sm tracking-tight text-slate-600 dark:text-slate-400 hover:text-teal-600 hover:scale-105 transition-transform duration-300 ease-out">How It Works</a>
            <a href="#architecture" className="font-semibold text-sm tracking-tight text-slate-600 dark:text-slate-400 hover:text-teal-600 hover:scale-105 transition-transform duration-300 ease-out">Architecture</a>
            <a href="#features" className="font-semibold text-sm tracking-tight text-slate-600 dark:text-slate-400 hover:text-teal-600 hover:scale-105 transition-transform duration-300 ease-out">Features</a>
          </nav>
          <Link href="/login" className="bg-gradient-to-br from-primary to-primary-container text-on-primary text-sm font-semibold tracking-tight px-6 py-2.5 rounded-full hover:scale-105 transition-transform duration-300 ease-out">
            Launch Dashboard
          </Link>
        </div>
      </header>

      <main className="relative">
        {/* Ethereal Background */}
        <div className="absolute inset-0 ethereal-gradient pointer-events-none opacity-50"></div>

        {/* ──────────────── Hero ──────────────── */}
        <section className="relative min-h-screen flex items-center pt-24 px-12 max-w-screen-2xl mx-auto overflow-hidden">
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-16 items-center w-full fade-slide-in">
            {/* Left Content */}
            <div className="max-w-2xl space-y-8 z-10">
              <div className="inline-flex items-center space-x-2 px-4 py-1.5 rounded-full bg-primary-container/30 text-on-primary-fixed-variant text-xs font-semibold tracking-widest uppercase">
                <span className="material-symbols-outlined text-sm">auto_awesome</span>
                <span>AI-Powered Data Intelligence</span>
              </div>
              
              <h1 className="text-7xl font-extrabold tracking-tighter text-on-surface leading-[1.05] font-headline">
                Ask Your Data <span className="text-primary-dim">in English</span>
              </h1>
              <p className="text-xl leading-relaxed text-on-surface-variant font-light max-w-xl">
                OmniData translates plain-English business questions into live SQL queries against your Snowflake warehouse, 
                Salesforce CRM, and internal knowledge base — returning charts, tables, and narrative insights in seconds.
              </p>
              
              <div className="flex items-center space-x-6 pt-4">
                <Link href="/login" className="bg-gradient-to-br from-primary to-primary-container text-on-primary px-8 py-4 rounded-full font-semibold shadow-lg shadow-primary/20 hover:scale-105 transition-transform duration-300">
                  Try It Now
                </Link>
                <a href="#how-it-works" className="px-8 py-4 rounded-full font-semibold text-on-surface border border-outline-variant/15 hover:border-outline-variant/40 hover:bg-surface-container-low transition-all duration-300 flex items-center space-x-2">
                  <span className="material-symbols-outlined">arrow_downward</span>
                  <span>See How</span>
                </a>
              </div>

              <div className="pt-12 grid grid-cols-3 gap-8">
                <div>
                  <div className="text-2xl font-bold text-on-surface">4</div>
                  <div className="text-xs uppercase tracking-widest text-on-surface-variant">Data Sources</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-on-surface">~3s</div>
                  <div className="text-xs uppercase tracking-widest text-on-surface-variant">Query to Insight</div>
                </div>
                <div>
                  <div className="text-2xl font-bold text-on-surface">100%</div>
                  <div className="text-xs uppercase tracking-widest text-on-surface-variant">Transparent SQL</div>
                </div>
              </div>
            </div>

            {/* Right Visual — Chat Preview */}
            <div className="relative flex justify-center items-center">
              <div className="relative w-full max-w-xl">
                {/* Mock Chat Conversation */}
                <div className="bg-surface-container-low rounded-[2rem] shadow-2xl p-8 space-y-5 border border-outline-variant/10">
                  {/* User message */}
                  <div className="flex justify-end">
                    <div className="bg-primary text-on-primary px-5 py-3 rounded-2xl rounded-tr-md max-w-[280px] text-sm font-medium shadow-md">
                      What were our total sales by region last quarter?
                    </div>
                  </div>
                  
                  {/* Bot thinking trace */}
                  <div className="flex items-start gap-3">
                    <div className="w-8 h-8 rounded-full bg-primary-container flex items-center justify-center shrink-0">
                      <span className="material-symbols-outlined text-primary text-sm">auto_awesome</span>
                    </div>
                    <div className="space-y-2.5 flex-1">
                      <div className="bg-surface-container rounded-2xl rounded-tl-md px-5 py-3 text-sm text-on-surface shadow-sm">
                        <div className="flex items-center gap-2 text-[10px] uppercase tracking-widest text-primary font-bold mb-2">
                          <span className="material-symbols-outlined text-xs">route</span> Agent Pipeline
                        </div>
                        <div className="space-y-1.5 text-xs text-on-surface-variant">
                          <div className="flex items-center gap-2"><span className="text-emerald-500">✓</span> Jargon rewrite: &quot;total sales&quot; → ACTUAL_SALES</div>
                          <div className="flex items-center gap-2"><span className="text-emerald-500">✓</span> SQL generated against AURA_SALES</div>
                          <div className="flex items-center gap-2"><span className="text-emerald-500">✓</span> 4 regions returned — chart rendered</div>
                        </div>
                      </div>
                      <div className="bg-surface-container rounded-2xl rounded-tl-md px-5 py-3 text-sm text-on-surface shadow-sm">
                        North led with <strong>£2.4M</strong>, followed by East at £1.8M. South saw a <strong>12% QoQ decline</strong> linked to higher return rates.
                      </div>
                    </div>
                  </div>

                  {/* Input bar */}
                  <div className="flex items-center gap-2 bg-surface rounded-xl px-4 py-3 border border-outline-variant/10">
                    <span className="text-sm text-on-surface-variant flex-1">Ask about sales, churn, products...</span>
                    <div className="w-8 h-8 rounded-lg bg-primary flex items-center justify-center">
                      <span className="material-symbols-outlined text-on-primary text-sm">arrow_upward</span>
                    </div>
                  </div>
                </div>

                {/* Floating Badge — Snowflake */}
                <div className="absolute -top-4 -right-4 glass-panel rounded-2xl px-4 py-3 shadow-xl z-30 hover:scale-[1.02] transition-transform duration-300">
                  <div className="flex items-center gap-2">
                    <div className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></div>
                    <span className="text-xs font-bold uppercase tracking-tight">Snowflake Live</span>
                  </div>
                </div>

                {/* Floating Badge — Confidence */}
                <div className="absolute -bottom-4 -left-4 glass-panel rounded-2xl px-4 py-3 shadow-xl z-30 hover:scale-[1.02] transition-transform duration-300">
                  <div className="text-xs font-bold text-on-surface-variant uppercase tracking-tight">Confidence</div>
                  <div className="text-xl font-extrabold text-primary mt-0.5">94%</div>
                </div>
              </div>
            </div>
          </div>
        </section>

        {/* ──────────────── How It Works ──────────────── */}
        <section id="how-it-works" className="py-32 px-12 max-w-screen-2xl mx-auto">
          <div className="mb-20 text-center space-y-4">
            <h2 className="text-4xl font-bold tracking-tight text-on-surface font-headline">From Question to Insight in 3 Seconds</h2>
            <p className="text-on-surface-variant max-w-2xl mx-auto">OmniData uses a multi-agent LangGraph pipeline to route, validate, execute, and narrate your data — with full transparency at every step.</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-4 gap-6">
            {[
              { icon: "edit_note", title: "You Ask", desc: "Type any business question in plain English. Jargon like 'revenue' is auto-rewritten to the correct column name.", color: "text-primary", step: "01" },
              { icon: "account_tree", title: "AI Routes", desc: "LangGraph classifies your question and routes to the right data source — Snowflake, Salesforce, Confluence, or Web.", color: "text-secondary", step: "02" },
              { icon: "code", title: "SQL Executes", desc: "A validated SQL query runs against your live Snowflake warehouse. Every query is shown in the transparency panel.", color: "text-tertiary", step: "03" },
              { icon: "insights", title: "You See", desc: "Get a natural-language narrative, auto-generated charts, confidence score, and the full agent trace — all in one view.", color: "text-primary-dim", step: "04" },
            ].map((step) => (
              <div key={step.step} className="bg-surface-container-low hover:bg-surface-container rounded-[2rem] p-8 transition-all duration-300 relative group hover:scale-[1.01]">
                <div className="absolute top-6 right-6 text-5xl font-black text-outline-variant/10 font-headline">{step.step}</div>
                <div className={`w-14 h-14 rounded-2xl bg-surface-container flex items-center justify-center ${step.color} mb-6`}>
                  <span className="material-symbols-outlined text-2xl" style={{fontVariationSettings: "'FILL' 1"}}>{step.icon}</span>
                </div>
                <h3 className="text-xl font-bold mb-3">{step.title}</h3>
                <p className="text-on-surface-variant text-sm leading-relaxed">{step.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ──────────────── Architecture Bento ──────────────── */}
        <section id="architecture" className="py-32 px-12 max-w-screen-2xl mx-auto">
          <div className="mb-20 text-center space-y-4">
            <h2 className="text-4xl font-bold tracking-tight text-on-surface font-headline">Enterprise Architecture</h2>
            <p className="text-on-surface-variant max-w-xl mx-auto">Five data sources, one multi-agent brain, zero black boxes.</p>
          </div>
          
          <div className="grid grid-cols-1 md:grid-cols-12 gap-8 h-auto md:h-[700px]">
            {/* Large Feature — Snowflake */}
            <div className="col-span-1 md:col-span-8 bg-surface-container-low hover:bg-surface-container transition-colors duration-500 rounded-[2rem] p-12 flex flex-col justify-between overflow-hidden relative">
              <div className="max-w-lg space-y-6 z-10">
                <span className="material-symbols-outlined text-4xl text-primary" style={{fontVariationSettings: "'FILL' 1"}}>database</span>
                <h3 className="text-3xl font-bold">Snowflake Data Warehouse</h3>
                <p className="text-on-surface-variant leading-relaxed">
                  The structured data backbone. OmniData generates validated SQL against your live OMNIDATA_DB warehouse across four schemas — 
                  Sales, Products, Returns, and Customers — with AI-powered query decomposition for complex, multi-table questions.
                </p>
                <div className="flex flex-wrap gap-2 pt-2">
                  {["AURA_SALES", "PRODUCT_CATALOGUE", "RETURN_EVENTS", "CUSTOMER_METRICS"].map(t => (
                    <span key={t} className="text-[10px] font-mono font-bold bg-primary/10 text-primary px-3 py-1.5 rounded-lg tracking-wide">{t}</span>
                  ))}
                </div>
              </div>
              <div className="absolute bottom-0 right-0 w-1/3 h-1/3 opacity-10 pointer-events-none">
                <span className="material-symbols-outlined text-[240px] text-primary">database</span>
              </div>
            </div>

            {/* Side Features */}
            <div className="col-span-1 md:col-span-4 flex flex-col gap-8">
              <div className="flex-1 bg-surface-container-highest rounded-[2rem] p-10 flex flex-col justify-center items-center text-center space-y-4 hover:scale-[1.02] transition-transform duration-300">
                <div className="w-16 h-16 rounded-full bg-surface-container-lowest flex items-center justify-center text-tertiary">
                  <span className="material-symbols-outlined text-3xl">visibility</span>
                </div>
                <h4 className="text-xl font-bold">Full Transparency</h4>
                <p className="text-sm text-on-surface-variant font-medium">Every query exposes the generated SQL, live agent trace, confidence score, and jargon rewrites. No black-box answers — ever.</p>
              </div>
              <Link href="/login" className="flex-1 block group bg-primary text-on-primary rounded-[2rem] p-10 flex flex-col justify-center space-y-4 relative overflow-hidden hover:scale-[1.02] transition-transform duration-300">
                <h4 className="text-xl font-bold z-10">Metric Glossary</h4>
                <p className="text-sm opacity-80 z-10 max-w-[220px]">12 business metrics with 93 natural-language aliases, units, and definitions — synced from Snowflake, browsable in the dashboard.</p>
                <div className="absolute -right-4 -bottom-4 opacity-20 group-hover:scale-110 transition-transform duration-500">
                  <span className="material-symbols-outlined text-[120px]">book</span>
                </div>
              </Link>
            </div>

            {/* Bottom Row — Data Sources */}
            <div className="col-span-1 md:col-span-3 bg-surface-container hover:bg-surface-container-highest transition-colors duration-300 rounded-[2rem] p-8 flex flex-col justify-center space-y-3">
              <div className="p-4 bg-surface-container-lowest/50 rounded-2xl shadow-sm w-fit">
                <span className="material-symbols-outlined text-3xl text-secondary">cloud</span>
              </div>
              <h4 className="font-bold text-on-surface">Salesforce CRM</h4>
              <p className="text-xs text-on-surface-variant font-semibold leading-relaxed">Accounts, opportunities, and churn risk — searched via Pinecone vectors with live SOQL fallback.</p>
            </div>

            <div className="col-span-1 md:col-span-3 bg-surface-container hover:bg-surface-container-highest transition-colors duration-300 rounded-[2rem] p-8 flex flex-col justify-center space-y-3">
              <div className="p-4 bg-surface-container-lowest/50 rounded-2xl shadow-sm w-fit">
                <span className="material-symbols-outlined text-3xl text-tertiary">article</span>
              </div>
              <h4 className="font-bold text-on-surface">Confluence Knowledge</h4>
              <p className="text-xs text-on-surface-variant font-semibold leading-relaxed">Internal policies, trading updates, and product briefs — retrieved via Pinecone RAG with source citations.</p>
            </div>

            <div className="col-span-1 md:col-span-3 bg-surface-container hover:bg-surface-container-highest transition-colors duration-300 rounded-[2rem] p-8 flex flex-col justify-center space-y-3">
              <div className="p-4 bg-surface-container-lowest/50 rounded-2xl shadow-sm w-fit">
                <span className="material-symbols-outlined text-3xl text-primary-dim">language</span>
              </div>
              <h4 className="font-bold text-on-surface">Web Intelligence</h4>
              <p className="text-xs text-on-surface-variant font-semibold leading-relaxed">Real-time competitor pricing, market trends, and industry benchmarks via Tavily live search.</p>
            </div>

            <div className="col-span-1 md:col-span-3 bg-surface-container hover:bg-surface-container-highest transition-colors duration-300 rounded-[2rem] p-8 flex flex-col justify-center space-y-3">
              <div className="p-4 bg-surface-container-lowest/50 rounded-2xl shadow-sm w-fit">
                <span className="material-symbols-outlined text-3xl text-primary">code_blocks</span>
              </div>
              <h4 className="font-bold text-on-surface">E2B Sandbox</h4>
              <p className="text-xs text-on-surface-variant font-semibold leading-relaxed">AI-generated Python visualization code runs in an isolated cloud sandbox — Plotly charts rendered securely.</p>
            </div>
          </div>
        </section>

        {/* ──────────────── Features ──────────────── */}
        <section id="features" className="py-32 px-12 max-w-screen-2xl mx-auto">
          <div className="mb-20 text-center space-y-4">
            <h2 className="text-4xl font-bold tracking-tight text-on-surface font-headline">Built for Real Business Users</h2>
            <p className="text-on-surface-variant max-w-xl mx-auto">No SQL knowledge required. No BI tool training. Just ask.</p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
            {[
              { icon: "translate", title: "Jargon Translation", desc: "Language rules automatically rewrite technical column names like ACTUAL_SALES and CHURN_RATE into plain business English before the user ever sees them.", badge: "Live" },
              { icon: "psychology", title: "LangGraph Agents", desc: "A multi-step agent pipeline classifies intent, decomposes complex queries, routes to 5 data sources in parallel, and synthesizes a unified narrative.", badge: "AI" },
              { icon: "bar_chart", title: "Auto Visualization", desc: "Every SQL result is visualized automatically — bar, line, grouped bar, or scatter — using AI-generated Python code executed in a secure E2B sandbox.", badge: "Visual" },
              { icon: "quiz", title: "Smart Clarification", desc: "Ambiguous terms like 'performance' or 'numbers' trigger clarification cards with specific options before any query executes.", badge: "UX" },
              { icon: "admin_panel_settings", title: "Role-Based Access", desc: "Region managers see only their region's data. Access rules are enforced at the synthesis layer — the AI acknowledges restrictions transparently.", badge: "Security" },
              { icon: "healing", title: "Self-Healing SQL", desc: "Domain experts can correct AI-generated queries and save them to a Pinecone vector store — the system learns and improves with every correction.", badge: "Learn" },
            ].map((feat) => (
              <div key={feat.title} className="bg-surface-container-low hover:bg-surface-container rounded-[2rem] p-8 transition-all duration-300 group hover:scale-[1.01] relative">
                <div className="absolute top-6 right-6">
                  <span className="text-[9px] font-bold uppercase tracking-widest bg-primary/10 text-primary px-2.5 py-1 rounded-md">{feat.badge}</span>
                </div>
                <div className="w-12 h-12 rounded-xl bg-surface-container flex items-center justify-center text-primary mb-5">
                  <span className="material-symbols-outlined text-2xl" style={{fontVariationSettings: "'FILL' 1"}}>{feat.icon}</span>
                </div>
                <h3 className="text-lg font-bold mb-2">{feat.title}</h3>
                <p className="text-on-surface-variant text-sm leading-relaxed">{feat.desc}</p>
              </div>
            ))}
          </div>
        </section>

        {/* ──────────────── CTA ──────────────── */}
        <section className="py-32 px-12">
          <div className="max-w-4xl mx-auto rounded-[3rem] bg-gradient-to-br from-primary-dim to-primary p-16 md:p-20 text-center text-on-primary shadow-2xl relative overflow-hidden hover:shadow-primary/30 transition-shadow duration-500">
            <div className="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-10"></div>
            <div className="relative z-10 space-y-8">
              <h2 className="text-5xl md:text-6xl font-extrabold tracking-tight">Stop writing SQL.<br/>Start asking questions.</h2>
              <p className="text-xl opacity-90 max-w-lg mx-auto font-light leading-relaxed">
                OmniData connects to your Snowflake warehouse and turns plain English into live business intelligence — with full transparency.
              </p>
              <div className="pt-8">
                <Link href="/login" className="bg-surface text-primary px-10 py-5 rounded-full font-bold text-lg hover:scale-105 transition-transform duration-300 shadow-xl inline-block">
                  Launch the Dashboard
                </Link>
              </div>
            </div>
          </div>
        </section>
      </main>

      {/* Footer */}
      <footer className="mt-16 bg-surface-container-low dark:bg-slate-950 w-full rounded-t-[2rem]">
        <div className="flex flex-col md:flex-row justify-between items-center px-12 py-16 w-full max-w-screen-2xl mx-auto">
          <div className="mb-8 md:mb-0">
            <div className="font-bold text-slate-800 dark:text-slate-100 text-xl font-headline mb-2">OmniData</div>
            <p className="text-xs leading-relaxed uppercase tracking-widest text-slate-500">AI-Powered Data Intelligence Platform</p>
          </div>
          <div className="flex flex-wrap justify-center gap-10">
            <span className="font-semibold text-xs uppercase tracking-widest text-slate-500">Snowflake · Salesforce · Confluence · Pinecone · LangGraph</span>
          </div>
        </div>
      </footer>
    </div>
  );
}
