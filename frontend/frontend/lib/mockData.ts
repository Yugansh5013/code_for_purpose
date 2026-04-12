import type { ChatResponse, IntegrationStatus, MetricsResponse } from "./types";

export const MOCK_RESPONSE_1: ChatResponse = {
  message_id: "msg-001",
  type: "answer",
  answer: {
    text: "Your refund policy sets a <strong>30-day window</strong> for standard returns and <strong>90 days</strong> for enterprise accounts. In Q1 2026, your <strong>Return Rate</strong> reached <strong>4.2%</strong> — up from 2.8% in Q4 2025. The South Region drove the majority of returns (+22%), correlating with delayed shipments in your Operations runbook. Three enterprise accounts in Salesforce exceed the 90-day policy threshold.",
    branches: ["sql", "rag_confluence", "rag_salesforce"],
    trace: [
      { node: "intent_router", detail: "sql_likely=true, rag_present=true" },
      { node: "temporal_resolver", detail: "no date phrase detected" },
      { node: "metric_resolver", detail: '"return rates" → RETURN_RATE (unambiguous)' },
      { node: "e2b_sandbox", detail: "pre-warmed (sql_likely=true, async)" },
      { node: "branch_sql", detail: "schema_rag → sql_gen → sqlglot_validate → execute" },
      { node: "branch_rag", detail: "confluence_search → 3 chunks [score: 0.89]" },
      { node: "branch_soql", detail: "sf_schema_rag → soql_gen → validate → execute" },
      { node: "synthesis_node", detail: "merging 3 branch outputs → jargon audit" },
      { node: "semantic_validator", detail: "rag_present=true → 2 terms rewritten", highlight: true }
    ],
    metric_resolution: {
      alias: "return rates",
      display_name: "Return Rate (%)",
      column_name: "RETURN_RATE"
    },
    sources: [
      { source_type: "snowflake", label: "AURA_SALES", confidence: 0.87 },
      { source_type: "confluence", label: "Refund Policy" },
      { source_type: "salesforce", label: "Accounts", confidence: 0.81 }
    ],
    transparency: {
      sql: "SELECT\n  geo_territory,\n  SUM(actual_sales) AS total_sales,\n  AVG(return_rate) AS avg_return_rate\nFROM\n  OMNIDATA_DB.SALES.AURA_SALES\nWHERE\n  sale_date BETWEEN '2026-01-01' AND '2026-03-31'\nGROUP BY geo_territory\nORDER BY total_sales DESC;",
      soql: "SELECT\n  Id, Name, AnnualRevenue,\n  ChurnRisk__c, ReturnRate__c\nFROM Account\nWHERE\n  ReturnRate__c > 0.05\n  AND Type = 'Enterprise'\nORDER BY ChurnRisk__c DESC\nLIMIT 10;",
      raw_data: [
        { geo_territory: "North", total_sales: 1420000, avg_return_rate: 0.021, delta: "-0.3pp" },
        { geo_territory: "South", total_sales: 980000, avg_return_rate: 0.078, delta: "+4.2pp" },
        { geo_territory: "East", total_sales: 840000, avg_return_rate: 0.034, delta: "+0.8pp" },
        { geo_territory: "West", total_sales: 560000, avg_return_rate: 0.029, delta: "-0.1pp" }
      ],
      python_code: "import matplotlib.pyplot as plt\nimport pandas as pd\n\ndf = pd.DataFrame(results)\nfig, ax = plt.subplots(figsize=(6, 4))\ncolors = ['#22c55e', '#ef4444', '#3b82f6', '#3b82f6']\nax.barh(df['geo_territory'], df['total_sales'], color=colors, height=0.6)\nax.set_facecolor('#080a0c')\nfig.patch.set_facecolor('#080a0c')\nplt.tight_layout()\nplt.savefig('chart.png', dpi=150)",
      context_chunks: [
        {
          source_type: "confluence",
          title: "Enterprise Customer Refund Policy",
          space_key: "CUSTOPS",
          body: "Enterprise accounts are eligible for returns within 90 calendar days of purchase date, subject to account manager approval for values exceeding £50K.",
          updated_at: "2026-03-14",
          chunk_index: 2,
          total_chunks: 5,
          score: 0.91
        },
        {
          source_type: "confluence",
          title: "Operations Runbook — South Region",
          space_key: "OPS",
          body: "Delayed shipment events exceeding 5 business days in the South Region must be escalated to the logistics team. Return rates above 5% trigger an automatic review workflow.",
          updated_at: "2026-02-28",
          chunk_index: 1,
          total_chunks: 3,
          score: 0.83
        }
      ],
      confidence: {
        score: 0.87,
        tier: "green",
        signals: { schema_cosine: 0.92, retry_score: 1.0, row_sanity: 0.75 },
        explanation: "Strong schema match · 0 retries needed · non-empty result returned"
      },
      semantic_substitutions: [
        { original: "ChurnRisk__c", replaced_with: "Churn Risk Score", location: "paragraph 2" },
        { original: "IS_ACTIVE = 1", replaced_with: "active customers", location: "bullet 3" }
      ],
      validation_passed: true,
      validator_model: "llama-3.3-8b",
      validator_latency_ms: 312
    },
    chart_data: {
      type: "bar",
      labels: ["North", "East", "West", "South"],
      values: [1420, 840, 560, 980],
      colours: ["var(--green)", "var(--blue)", "var(--blue)", "var(--red)"],
      y_label: "Total Sales (£K)"
    },
    stat_updates: [
      { label: "Return Rate", value: "4.2%", delta: "▲ +1.4pp QoQ", delta_direction: "neg" },
      { label: "Q1 Total Sales", value: "£3.8M", delta: "▼ −11%", delta_direction: "neg" },
      { label: "High-Risk Accts", value: "3", delta: "▲ 2 new", delta_direction: "neg" }
    ]
  }
};

export const MOCK_CLARIFICATION: ChatResponse = {
  message_id: "msg-002",
  type: "clarification",
  clarification: {
    question: 'Which metric did you mean by "performance"? This term maps to multiple metrics.',
    ambiguous_term: "performance",
    options: ["Total Sales (GBP)", "Units Sold", "Customer Count"]
  }
};

export const MOCK_METRICS: MetricsResponse = {
  metrics: [
    {
      name: "Total Sales",
      display_name: "Total Sales",
      canonical_column: "ACTUAL_SALES",
      unit: "GBP",
      description: "Total transaction value before returns or adjustments.",
      aliases: ["money", "income", "earnings", "revenue", "turnover"],
      ambiguous: false
    },
    {
      name: "Return Rate",
      display_name: "Return Rate (%)",
      canonical_column: "RETURN_RATE",
      unit: "%",
      description: "Percentage of transactions resulting in a return within the policy window.",
      aliases: ["returns", "refund rate", "reversal rate"],
      ambiguous: false
    },
    {
      name: "Customer Churn",
      display_name: "Customer Churn",
      canonical_column: "CHURN_FLAG",
      unit: "count / rate",
      description: "Customers who did not renew or cancelled in the measurement period.",
      aliases: ["lost customers", "attrition", "cancellations", "drop-off"],
      ambiguous: false
    },
    {
      name: "Active Customers",
      display_name: "Active Customers",
      canonical_column: "IS_ACTIVE",
      unit: "count",
      description: "Customers with at least one transaction or login in the period.",
      aliases: ["DAU", "MAU", "engaged users", "active users"],
      ambiguous: false
    },
    {
      name: "Sales Pipeline Value",
      display_name: "Sales Pipeline Value",
      canonical_column: "Opportunity.Amount",
      unit: "GBP",
      description: "Total value of open Salesforce Opportunities not yet closed.",
      aliases: ["deals", "opportunities", "potential revenue", "open deals"],
      ambiguous: false
    },
    {
      name: "Transaction Volume",
      display_name: "Transaction Volume",
      canonical_column: "TXN_COUNT",
      unit: "count",
      description: "Total number of digital transactions processed in the period.",
      aliases: ["txn count", "transactions", "digital volume"],
      ambiguous: false
    },
    {
      name: "Unit Sales",
      display_name: "Unit Sales",
      canonical_column: "UNITS_SOLD",
      unit: "count",
      description: "Number of individual product units sold in the period.",
      aliases: ["units", "items sold", "quantity sold"],
      ambiguous: false
    }
  ]
};

export const MOCK_STATUS: IntegrationStatus = {
  snowflake: "live",
  confluence: "syncing",
  salesforce: "live",
  tavily: "live"
};
