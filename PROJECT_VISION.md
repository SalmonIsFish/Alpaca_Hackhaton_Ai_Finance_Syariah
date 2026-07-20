# Amanah Trader Vision

Amanah Trader is a Shariah-aware investment operating system, not only a compliance checker.

The long-term product direction is an Islamic investment firm workflow with local-first agent teams:

- Shariah Research Agent: verifies investable universe and compliance evidence.
- Market Data Agent: collects prices, history, and market context.
- Quant Strategy Agent: generates rule-based signals and later strategy variants.
- Risk Manager Agent: enforces hard limits before any recommendation or order.
- Portfolio Manager Agent: manages watchlists, exposures, and allocation ideas.
- Execution Agent: handles paper execution only after explicit controls allow it.
- Audit and Compliance Agent: records decisions, approvals, execution attempts, and evidence.

Trading modes should gate behavior:

- `advisory`: agents analyze and recommend only.
- `approval`: agents prepare trades, human approval is required.
- `autonomous_paper`: future mode where agents can execute paper trades under strict limits.

Live autonomous trading is out of scope until the paper workflow, kill switch, audit trail, and risk controls are mature.
