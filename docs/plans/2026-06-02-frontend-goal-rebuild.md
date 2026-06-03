# Quant Frontend Goal Rebuild Implementation Plan

> **For Codex:** continue this goal without interrupting for minor choices. Stop only before backend API, database, payload, business-rule, token, or paid-provider changes.

**Goal:** Rebuild the quant frontend into a restrained research workspace for admin demos while preserving the client report and all backend contracts.

**Architecture:** Keep API calls, form ownership, and data refresh in `frontend-admin/src/App.tsx`; move view structure into section-level React files. Keep `frontend-display` as a single-file app and make only scoped style/reliability refinements.

**Tech Stack:** React 19, TypeScript, Ant Design 6, `@ant-design/icons`, Vite, existing CSS.

---

### Phase 1: Admin Structure And Navigation

**Files:**
- Modify: `frontend-admin/src/App.tsx`
- Modify: `frontend-admin/src/App.css`
- Create: `frontend-admin/src/components/MetricTile.tsx`
- Create: `frontend-admin/src/components/CommandRail.tsx`
- Create: `frontend-admin/src/components/SectionShell.tsx`
- Create: `frontend-admin/src/components/StatusTag.tsx`
- Create: `frontend-admin/src/components/CopyLinkButton.tsx`
- Create: `frontend-admin/src/utils/format.ts`
- Create: `frontend-admin/src/utils/labels.ts`

**Steps:**
1. Move pure formatting and label helpers out of `App.tsx`.
2. Create small presentational components for metrics, status, rail, shells, and temporary latest-link copy/open actions.
3. Replace old sidebar keys with aligned sections: `overview`, `data`, `strategy`, `backtest`, `publication`, `paper`, `audit`.
4. Add `activeSection` state in `App.tsx`.
5. Build with `cd frontend-admin; npm.cmd run build`.

**Acceptance:**
- No route dependency is added.
- Sidebar and command rail both switch sections through React state.
- Existing login and API refresh behavior stays intact.

### Phase 2: Admin Sections

**Files:**
- Create: `frontend-admin/src/sections/OverviewSection.tsx`
- Create: `frontend-admin/src/sections/DataSection.tsx`
- Create: `frontend-admin/src/sections/StrategySection.tsx`
- Create: `frontend-admin/src/sections/BacktestSection.tsx`
- Create: `frontend-admin/src/sections/PublicationSection.tsx`
- Create: `frontend-admin/src/sections/PaperSection.tsx`
- Create: `frontend-admin/src/sections/AuditSection.tsx`
- Modify: `frontend-admin/src/App.tsx`
- Modify: `frontend-admin/src/App.css`

**Steps:**
1. Extract each visible module into a section component.
2. Keep handlers and form instances passed as props from `App.tsx`.
3. Group instruments, portfolios, public fetch, CSV fallback, quality, import tasks, and schedules under Data.
4. Group snapshot publishing and share-link management under Publication.
5. Keep Paper copy as simulated audit/monitoring, not live trading.
6. Build with `cd frontend-admin; npm.cmd run build`.

**Acceptance:**
- Data, Strategy, Backtest, Publication, Paper, and Audit render independently.
- Recent selected backtest review still controls snapshot form defaults.
- Latest share token is shown only from the latest publish/create response.

### Phase 3: Admin Visual System

**Files:**
- Modify: `frontend-admin/src/App.css`

**Steps:**
1. Replace card-stack feel with fixed sidebar, compact top bar, command rail, summary strip, section shell, and two-column work surfaces.
2. Keep Ant Design form/table/button/tag components.
3. Add responsive rules for projection and mobile widths.
4. Build and browser-check admin desktop and mobile.

**Acceptance:**
- No nested UI cards as primary layout.
- Tables remain scroll-safe.
- Top bar, rail, controls, and tables do not overlap on narrow width.

### Phase 4: Display Refinement

**Files:**
- Modify: `frontend-display/src/App.tsx`
- Modify: `frontend-display/src/App.css`

**Steps:**
1. Keep payload normalization and report fallback behavior.
2. Lightly reduce K-line dark-terminal emphasis.
3. Tighten hero density and table/chart mobile behavior.
4. Build with `cd frontend-display; npm.cmd run build`.

**Acceptance:**
- Old snapshots remain readable.
- Token error/loading/no-data states remain stable.
- Negative returns remain professional risk disclosure, with no special demo-failure explanation.

### Phase 5: Verification And Delivery

**Commands:**
```powershell
cd frontend-admin
npm.cmd run build

cd ..\frontend-display
npm.cmd run build
```

**Browser checks:**
- Admin desktop: section switching, command rail, data, backtest, publication, paper, audit.
- Admin mobile: no overlap and no broken controls.
- Display desktop/mobile: report hero, metrics, charts, tables, assumptions, risk disclosure.

**Delivery notes:**
- Summarize IA/layout changes, demo-path improvements, display refinements, compatibility, verification, and residual risks.
