# VisionGuard AI — UI Guide

## Overview

The React frontend (`visionguard-ui`) already exists and is fully built. It currently runs on **mock data**. This guide documents what each screen shows, which API endpoint it needs, and what data mapping is required to make each screen real.

The UI was built in an AI studio and uses Tailwind CSS. **Do not modify the frontend** — only connect it to real API endpoints by making the UI's API base URL configurable via environment variable.

---

## Global Shell

### Sidebar Navigation
- Executive Dashboard → `/`
- Claims Explorer → `/claims`
- Provider Intelligence → `/providers`
- New Claim Scoring → `/scoring`

### System Status (Bottom of Sidebar)
- "Model AI: ONLINE" → driven by `GET /api/system/status` → `data.modelAi`
- "Pipeline: SYNCED" → `data.pipeline`

### Bell Icon (Notifications)
- Badge count → `GET /api/notifications` → `data.unreadCount`
- On click → list from `data.items`

### Header Search
- Calls `GET /api/search?query={value}` on input change (debounced 300ms)

---

## Screen 1 — Executive Dashboard

**Route:** `/`
**API:** `GET /api/dashboard/overview`

### KPI Cards (Top Row)
| UI Label | JSON path |
|---|---|
| Total Claims Analyzed | `data.kpis.totalClaimsAnalyzed.value` |
| +12% vs prev period | `data.kpis.totalClaimsAnalyzed.trendPercent` |
| Total Allowed Amount | `data.kpis.totalAllowedAmount.value` (format as $4.2M) |
| Average Fraud Score | `data.kpis.averageFraudScore.value` |
| Critical Claims Flagged | `data.kpis.criticalClaimsFlagged.value` |
| 2.1% of total volume | `data.kpis.criticalClaimsFlagged.shareOfTotalPercent` |

### Detected Fraud Value Trend (Area Chart)
- X-axis: `data.fraudTrend[].label` (Jan, Feb, Mar...)
- Y-axis: `data.fraudTrend[].fraudAmount`
- Data key for tooltip: `fraudAmount`

### Risk Distribution (Donut Chart)
- Slices: `data.riskDistribution.items[]`
- Center number: `data.riskDistribution.totalAnalyzed`
- Color map: Low=teal, Medium=yellow, High=orange, Critical=red/pink

### Top Suspicious Providers (Table)
- Columns: Provider ID | Name | Specialty | Risk Score | High-Risk Ratio | Allowed Amount
- Data: `data.topSuspiciousProviders[]`
- Risk Score shown as colored badge (same color scheme as Risk Distribution)

### Buttons
- "New Claim Scoring" → navigates to `/scoring`
- "Export Report" → calls `POST /api/dashboard/export` → show toast "Export queued"

---

## Screen 2 — Historical Claims Explorer

**Route:** `/claims`
**API:** `GET /api/claims` (with query params)

### Search Bar
- Calls `GET /api/claims?search={value}` on Enter or debounced

### Filter Buttons
- "All Risks" dropdown → `riskLevel` param
- "Date Range" → `dateFrom` + `dateTo` params
- "Advanced" → multiple additional filters

### Claims Table
| Column | JSON path |
|---|---|
| Claim ID | `items[].id` (links to `/claims/{id}`) |
| Provider | `items[].providerName` |
| Procedure | `items[].procedureCode` + `items[].procedureDesc` |
| Amount | `items[].allowedAmount` |
| Score | `items[].fraudScore` (colored badge) |
| Risk Level | `items[].riskLevel` (colored pill) |
| Fraud Type | `items[].fraudType` |
| Cluster | `items[].clusterId` |
| Action | ">" chevron → navigates to `/claims/{id}` |

### Score Badge Colors
```
Critical (80-100): red/pink bg (#ef4444 or similar)
High (60-79):      orange bg
Medium (40-59):    yellow bg
Low (0-39):        gray or teal bg
```

### Pagination
- Uses `data.pagination.page`, `totalPages`, `pageSize`
- "Previous" / "Next" buttons update `page` param

---

## Screen 3 — Claim Investigation View

**Route:** `/claims/:claimId`
**API:** `GET /api/claims/:claimId`

### Pipeline Stage Cards (Collapsible)
The screen shows 5 expandable stages. Each maps to an analysis sub-object:

**Stage 1 — Rules Analysis Engine**
- Header subtitle: "Triggered N deterministic rules"
- Expanded: Rule Score badge | Severity Flags badge
- Rule list: `analysis.rulesAnalysis.triggeredRules[]` → each shows `ruleCode` + `message`
- Color: R-xxx in red/orange pill

**Stage 2 — Statistical Analysis**
- Header subtitle: "Deviates +{Z}SD from mean"
- Expanded: Z-scores, provider percentile
- `analysis.statisticalAnalysis.claimAmountZScore` | `providerZScore` | `narrative`

**Stage 3 — ML Outlier Detection**
- Header subtitle: "High reconstruction error detected" or `mlAnalysis.modelSummary`
- Expanded:
  - "ISOLATION FOREST: {isolationForestScore} — Anomaly"
  - "PCA ERROR SCORE: {pcaErrorScore} — High"
- Data: `analysis.mlAnalysis.isolationForestScore` | `pcaErrorScore`

**Stage 4 — Behavioral Cluster Assignment**
- Header subtitle: "Mapped to Cluster {clusterId} ({clusterName})"
- Expanded: cluster description, claim count, risk characteristics
- Data: `analysis.clusterAssignment.cluster`

**Stage 5 — AI Investigation Summary**
- Header: "AI Investigation Summary" with green "GENERATED" badge
- Body: `analysis.aiSummary.summary` (bold key phrase)
- Risk Reasoning section: `analysis.aiSummary.riskReasoning`
- Recommendation section: `analysis.aiSummary.recommendation`

### Final Overall Risk Gauge (Right Panel)
- Big number: `data.claim.fraudScore`
- Risk level label: `data.claim.riskLevel`
- Color: same as badge scheme above
- "DETECTED FRAUD PATTERN": `data.claim.fraudType`

### Action Buttons
- "Assign to SIU Analyst" → `POST /api/claims/:claimId/flag-siu`
- "Download Report" → `GET /api/claims/:claimId/report` → open `data.downloadUrl`

---

## Screen 4 — Provider Intelligence

**Route:** `/providers`
**API:** `GET /api/providers` (list) + `GET /api/providers/:providerId` (detail)

### Monitored Entities List (Left Panel)
- Each item: Provider name | ID | Location | Specialty | Risk Score badge
- Click → loads provider detail in right panel
- Search: `GET /api/providers?search={value}`
- Data: `data.items[]`

### Provider Detail (Right Panel)

**Header Block**
- Name | Risk Level pill | `data.provider.riskScore`
- PRV-ID | Specialty | City, State

**KPI Row**
- Total Claims (12mo): `data.provider.claimCount`
- High Risk Ratio: `data.provider.highRiskRatio` (format as %)
- Total Allowed Amount: `data.provider.totalAllowedAmount` (format as $)

**Procedure Volume vs Peer Average (Bar Chart)**
- Grouped bars per procedure code
- Provider bar: `procedurePeerComparison[].providerVolume` (teal)
- Peer avg bar: `procedurePeerComparison[].peerAverageVolume` (dark blue)
- X-axis: `procedureCode`

**AI Analysis Summary (Right of Chart)**
- Pattern Deviation: `data.aiSummary.patternDeviation`
- Velocity Indicator: `data.aiSummary.velocityIndicator`
- Recommendation: `data.aiSummary.recommendation`

---

## Screen 5 — New Claim Scoring

**Route:** `/scoring`
**API:** POST/GET chain on `/api/scoring/jobs`

### Submission
- "Score New Claim" button → opens modal/form
- Form fields map to `ClaimInput` schema (see API Contracts)
- File upload option: `multipart/form-data` with `file` field
- On submit: `POST /api/scoring/jobs` → store `jobId`

### Pipeline Progress (After Submission)
- Poll `GET /api/scoring/jobs/:jobId` every 1.5 seconds
- Progress bar driven by `data.progressPercent`
- Active stage text: `data.activeStage`
- Each stage row updates `status`: pending → processing → completed

### Stage Status Icons
- `completed`: checkmark (green)
- `processing`: spinning loader
- `pending`: clock/gray

### Results Display (Same as Claim Investigation View)
- Once `status === "completed"`, call `GET /api/scoring/jobs/:jobId/result`
- Render exactly the same 5-stage + gauge layout as Screen 3
- "Assign to SIU Analyst" → `POST /api/scoring/jobs/:jobId/assign-siu`

---

## API Base URL Configuration

The frontend should read its API base URL from an environment variable. If the project uses Vite:

```
# visionguard-ui/.env.development
VITE_API_BASE_URL=http://localhost:8000
```

All API calls in the frontend should use:
```javascript
const BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000';
```

---

## Mock Data → Real Data Checklist

| Screen | Mock fields needing real values |
|---|---|
| Dashboard | All KPIs, trend chart months, risk donut counts |
| Claims Explorer | All rows, pagination totals |
| Claim Detail | All 5 pipeline stage values, AI summary text |
| Provider Intelligence | Provider list, peer comparison chart, AI summary |
| New Claim Scoring | Progress stages, final result |

---

## UI Quirks to Know

1. **Risk score badges** use numeric thresholds, not just the `riskLevel` string. The color is driven by `fraudScore` value, not `riskLevel`. Keep both in the API response.

2. **Provider list** shows ~5 providers in the screenshot. In reality, the API will return many more — the UI likely paginates or shows top N by default. Default sort should be `provider_risk_score DESC`.

3. **"GENERATED" badge** on AI Summary is a static green pill — it just indicates that OpenAI generated the text (not templated). The frontend probably checks if `aiSummary.summary` is non-empty. No special API field needed.

4. **Cluster IDs** like `CL-01`, `CL-03` in the UI exactly match the `clusterId` field. These are string identifiers, not integers.

5. **"N/A" in Fraud Type column** for low-risk claims is rendered when `fraudType` is `"No Significant Fraud Indicators"` or `null`. The UI may abbreviate this to "N/A".
