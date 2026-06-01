# Client Report Redesign Research

Date: 2026-06-01

## Purpose

This research supports the next client display frontend redesign. The goal is to upgrade the report from an engineering-readable snapshot into a customer-facing investment strategy report while keeping V1 boundaries: no live trading, no customer-side parameter editing, no strategy logic in the frontend, and no copied proprietary UI.

## References Inspected

1. Bloomberg Portfolio & Risk Analytics
   - Link: https://professional.bloomberg.com/products/bloomberg-terminal/portfolio-analytics/
   - Relevant finding: Bloomberg positions portfolio reporting around unified positions, risk, performance, attribution, scenario analysis, data validation, and templates for client/internal reports.

2. Morningstar Direct Advisory Suite: Client-Friendly Reports
   - Link: https://www.morningstar.com/business/products/direct-advisory-suite/reports
   - Relevant finding: Morningstar emphasizes clear communication, client-ready report templates, progress toward goals, risk alignment, performance over time, interactive reports, and trusted research context.

3. Morningstar Direct Advisory Suite overview
   - Link: https://www.morningstar.com/business/products/direct-advisory-suite
   - Relevant finding: Morningstar frames advisor software around proving advice value, client-friendly proposals, risk scoring, regulatory confidence, and client reporting workflows.

4. Morningstar Portfolio X-Ray training material
   - Link: https://advisor.morningstar.com/enterprise/vtc/xray_wtutr.pdf
   - Relevant finding: Portfolio X-Ray-style reports use visual composition, sector exposure, style, geography, and diversification views to support client conversations.

5. Morningstar Advisor Workstation report guide
   - Link: https://advisor.morningstar.com/enterprise/vtc/annotatedreports/UsingAWSReports.pdf
   - Relevant finding: Portfolio reports are separated by communication purpose: snapshot reports for portfolio-level strategy, X-Ray reports for exposure/diversification, comparison reports for strategy shifts, and hypothetical illustrations for backtested strategy stories.

6. BlackRock Advisor Center 360
   - Link: https://www.blackrock.com/us/financial-professionals/tools/advisor-center-360
   - Relevant finding: BlackRock emphasizes portfolio analysis, risk, tax, client-ready reports, stress testing, current-vs-proposed comparisons, holdings-based risk, and scenario conversations.

## Borrowable Patterns

- Lead with a plain-language strategy summary before charts.
- Make the first viewport answer: strategy, target stock/portfolio, period, frequency, return, risk, and snapshot status.
- Separate customer-facing interpretation from raw analytics.
- Pair performance with risk in the same visual hierarchy.
- Include method and assumption disclosure near the analysis, not only at the end.
- Use report-like metadata: snapshot version, publication time, generated time, publisher, data frequency, and scope.
- Show weak-data or short-sample warnings explicitly.
- Use dense charts but keep labels, legends, and section titles readable.
- Treat risk disclosure as structured compliance-style content.

## Rejected Patterns

- Live dashboard language such as real-time monitoring or live signal streams, because V1 is snapshot-only.
- Customer scenario editing or interactive allocation editing, because V1 forbids customer-side parameter changes.
- Stress testing and tax analysis modules, because they would overpromise beyond the current quant engine.
- Proprietary Bloomberg, Morningstar, or BlackRock visual treatments, because references are for structure and trust patterns only.
- Deep portfolio X-Ray exposure analytics, because current V1 data is stock/portfolio OHLCV and does not yet include sector, geography, or holdings look-through data.

## Chosen Visual Direction

Use a restrained institutional report style:

- Tone: professional, credible, calm, and analytical.
- Layout: report-first, with a strong summary hero, compact evidence cards, and large analysis panels.
- Palette: paper-like background, dark ink text, restrained blue/teal accents, red/orange only for risk warnings.
- Typography: system-safe Chinese-first stack, compact tables, readable chart labels.
- Interaction: read-only inspection. Charts may have tooltips, but the page should not feel like a trading terminal.

## Implementation Implications

- Refactor the display frontend into named report sections.
- Convert all visible copy to Chinese.
- Expand immutable snapshot payload for new snapshots with report metadata and assumptions while keeping old snapshots compatible.
- Add explicit short-sample, missing-field, and incomplete-assumption warnings in the frontend.
- Preserve backend-only strategy logic and token-only public access.
- Verify desktop, tablet, and mobile layouts in a real browser after implementation.
