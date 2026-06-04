# VisionGuard AI — API Contracts

## Conventions

- **Base URL:** `http://localhost:8000` (dev)
- **Content-Type:** `application/json` for all endpoints except file upload
- **Response Envelope:** All responses use:

```json
{
  "data": {},
  "meta": {
    "requestId": "req_uuid",
    "generatedAt": "2026-06-04T09:30:00Z"
  },
  "error": null
}
```

- **Scores:** numeric `0–100`
- **Amounts:** numeric in dollars, e.g. `495.0`
- **Ratios:** decimal e.g. `0.28`
- **Dates:** ISO 8601 strings

## Enums

```
RiskLevel:        Low | Medium | High | Critical
ClaimStatus:      Pending | Flagged | Cleared | Investigating
ScoringJobStatus: queued | validating | processing | completed | failed
SourceType:       x12_837 | csv | json | manual
```

---

## 1. Executive Dashboard

### `GET /api/dashboard/overview`

Returns KPIs, fraud trend, risk distribution, top suspicious providers.

**Response:**
```json
{
  "data": {
    "kpis": {
      "totalClaimsAnalyzed": { "value": 45291, "trendPercent": 12.0, "trendDirection": "up" },
      "totalAllowedAmount": { "value": 4200000, "trendPercent": 5.0, "trendDirection": "up" },
      "averageFraudScore": { "value": 74.2, "trendPercent": 12.8, "trendDirection": "up" },
      "criticalClaimsFlagged": { "value": 312, "shareOfTotalPercent": 2.1 }
    },
    "fraudTrend": [
      { "period": "2026-01", "label": "Jan", "fraudAmount": 12000, "claimCount": 450 },
      { "period": "2026-02", "label": "Feb", "fraudAmount": 15000, "claimCount": 510 }
    ],
    "riskDistribution": {
      "totalAnalyzed": 10000,
      "items": [
        { "riskLevel": "Low", "count": 6200 },
        { "riskLevel": "Medium", "count": 2400 },
        { "riskLevel": "High", "count": 1100 },
        { "riskLevel": "Critical", "count": 300 }
      ]
    },
    "topSuspiciousProviders": [
      {
        "id": "PRV-8834",
        "name": "ClearSight Associates",
        "specialty": "Ophthalmology",
        "riskScore": 94,
        "highRiskRatio": 0.35,
        "totalAllowedAmount": 210500
      }
    ]
  },
  "meta": { "requestId": "req_dashboard_001", "generatedAt": "2026-06-04T09:30:00Z" },
  "error": null
}
```

**Implementation note:** Computed from `claims` + `provider_gold` tables. `fraudTrend` groups by `ServiceMonth`. `riskDistribution` groups `Final_Risk_Level`. `topSuspiciousProviders` = top 5 by `Provider_Risk_Score` from `provider_gold`.

---

### `POST /api/dashboard/export`

Triggers PDF export of dashboard. Returns a job ID (async).

**Request:** `{}` (no body required, or optional `{ "format": "pdf" }`)

**Response:**
```json
{
  "data": { "exportId": "exp_001", "status": "queued", "format": "pdf" },
  "meta": { "requestId": "req_export_001", "generatedAt": "2026-06-04T09:31:00Z" },
  "error": null
}
```

---

## 2. Historical Claims Explorer

### `GET /api/claims`

Paginated, filterable list of all scored claims.

**Query Parameters:**

| Param | Type | Description |
|---|---|---|
| `search` | string | Searches ClaimId, ProviderId, ProcedureCode |
| `riskLevel` | string | Filter by RiskLevel enum |
| `dateFrom` | ISO date | Service date start |
| `dateTo` | ISO date | Service date end |
| `providerId` | string | Filter by provider |
| `procedureCode` | string | Filter by V-code |
| `fraudType` | string | Filter by fraud type |
| `status` | string | Filter by claim status |
| `minFraudScore` | int | Minimum fraud score |
| `maxFraudScore` | int | Maximum fraud score |
| `page` | int | Page number (default: 1) |
| `pageSize` | int | Results per page (default: 25, max: 100) |
| `sortBy` | string | Field to sort by (default: `fraudScore`) |
| `sortDir` | string | `asc` or `desc` (default: `desc`) |

**Response:**
```json
{
  "data": {
    "items": [
      {
        "id": "CLM-3310928",
        "providerId": "PRV-3391",
        "providerName": "Advanced Glaucoma Group",
        "memberId": "MEM-11029",
        "procedureCode": "92250",
        "procedureDesc": "Fundus Photography",
        "allowedAmount": 185.0,
        "fraudScore": 91,
        "riskLevel": "Critical",
        "fraudType": "Unbundling",
        "clusterId": "CL-03",
        "date": "2026-06-03",
        "status": "Flagged"
      }
    ],
    "pagination": {
      "page": 1,
      "pageSize": 25,
      "totalItems": 10000,
      "totalPages": 400
    },
    "filters": {
      "applied": { "search": null, "riskLevel": null },
      "availableRiskLevels": ["Low", "Medium", "High", "Critical"],
      "availableStatuses": ["Pending", "Flagged", "Cleared", "Investigating"]
    }
  },
  "meta": { "requestId": "req_claims_001", "generatedAt": "2026-06-04T09:32:00Z" },
  "error": null
}
```

---

## 3. Claim Investigation View

### `GET /api/claims/:claimId`

Full detail for a single claim including analysis breakdown.

**Response:**
```json
{
  "data": {
    "claim": {
      "id": "CLM-3310928",
      "providerId": "PRV-3391",
      "providerName": "Advanced Glaucoma Group",
      "memberId": "MEM-11029",
      "procedureCode": "92250",
      "procedureDesc": "Fundus Photography",
      "allowedAmount": 185.0,
      "fraudScore": 91,
      "riskLevel": "Critical",
      "fraudType": "Unbundling",
      "clusterId": "CL-03",
      "date": "2026-06-03",
      "status": "Flagged"
    },
    "analysis": {
      "pipeline": {
        "runId": "RUN-20260603-009",
        "status": "completed",
        "submittedAt": "2026-06-03T15:11:00Z",
        "completedAt": "2026-06-03T15:11:24Z",
        "statusText": "Pipeline execution completed"
      },
      "member": {
        "memberId": "MEM-11029",
        "age": 42,
        "gender": "Male",
        "location": { "city": "Chicago", "state": "IL" }
      },
      "providerContext": {
        "providerId": "PRV-3391",
        "providerName": "Advanced Glaucoma Group",
        "specialty": "Ophthalmology",
        "city": "New York",
        "state": "NY",
        "historicalZScore": 2.1,
        "historicalPercentile": 95
      },
      "procedure": {
        "code": "92250",
        "description": "Fundus Photography",
        "allowedAmount": 185.0
      },
      "rulesAnalysis": {
        "engine": "Deterministic Engine",
        "status": "triggered",
        "ruleScore": 72,
        "severity": "High",
        "triggeredRules": [
          { "ruleCode": "R001", "severity": "high", "message": "Premium material code (V2700–V2799) detected — possible material upcoding." }
        ]
      },
      "statisticalAnalysis": {
        "claimAmountZScore": 3.1,
        "providerZScore": 2.4,
        "narrative": "Allowed amount is 3.1 SD above mean.",
        "providerPercentile": 98
      },
      "mlAnalysis": {
        "anomalyScore": 0.91,
        "isolationForestScore": 0.88,
        "pcaErrorScore": 0.93,
        "modelSummary": "High reconstruction error detected"
      },
      "clusterAssignment": {
        "clusterId": "CL-03",
        "matched": true,
        "confidence": 0.94,
        "cluster": {
          "id": "CL-03",
          "name": "Unbundling - Glaucoma Screening",
          "riskCharacteristics": "Same-day billing of multiple distinct structural imaging codes that should typically be bundled or mutually exclusive for the same patient encounter.",
          "claimCount": 85
        }
      },
      "aiSummary": {
        "summary": "There is a very high probability of intentional Unbundling.",
        "riskReasoning": "Procedure 92250 was billed alongside 92134 on the same date for the same patient.",
        "recommendation": "Suspend auto-adjudication and route the claim to a Tier 2 SIU analyst."
      },
      "actions": {
        "canDownloadReport": true,
        "canFlagForSiu": true,
        "canAssignAnalyst": true
      }
    }
  },
  "meta": { "requestId": "req_claim_detail_001", "generatedAt": "2026-06-04T09:33:00Z" },
  "error": null
}
```

---

### `POST /api/claims/:claimId/flag-siu`

Flags a claim for SIU review. Updates status in DB.

**Response:**
```json
{
  "data": {
    "claimId": "CLM-3310928",
    "status": "Investigating",
    "queue": "SIU",
    "flaggedAt": "2026-06-04T09:34:00Z"
  },
  "meta": { "requestId": "req_flag_001", "generatedAt": "2026-06-04T09:34:00Z" },
  "error": null
}
```

---

### `GET /api/claims/:claimId/report`

Returns a download URL for the claim investigation report PDF.

**Response:**
```json
{
  "data": {
    "claimId": "CLM-3310928",
    "reportId": "rpt_001",
    "downloadUrl": "/api/claims/CLM-3310928/report/download",
    "expiresAt": "2026-06-04T10:34:00Z"
  },
  "meta": { "requestId": "req_report_001", "generatedAt": "2026-06-04T09:34:10Z" },
  "error": null
}
```

---

## 4. Provider Intelligence

### `GET /api/providers`

Paginated list of providers with risk metrics.

**Query Parameters:** `search`, `riskLevel`, `page`, `pageSize`, `sortBy`, `sortDir`

**Response:**
```json
{
  "data": {
    "items": [
      {
        "id": "PRV-8834",
        "name": "ClearSight Associates",
        "specialty": "Ophthalmology",
        "riskScore": 94,
        "claimCount": 320,
        "highRiskRatio": 0.35,
        "totalAllowedAmount": 210500,
        "city": "Las Vegas",
        "state": "NV"
      }
    ],
    "pagination": { "page": 1, "pageSize": 50, "totalItems": 186 }
  },
  "meta": { "requestId": "req_providers_001", "generatedAt": "2026-06-04T09:35:00Z" },
  "error": null
}
```

---

### `GET /api/providers/:providerId`

Full provider detail with peer comparison and AI summary.

**Response:**
```json
{
  "data": {
    "provider": {
      "id": "PRV-8834",
      "name": "ClearSight Associates",
      "specialty": "Ophthalmology",
      "riskScore": 94,
      "claimCount": 320,
      "highRiskRatio": 0.35,
      "totalAllowedAmount": 210500,
      "city": "Las Vegas",
      "state": "NV"
    },
    "procedurePeerComparison": [
      { "procedureCode": "92004", "providerVolume": 120, "peerAverageVolume": 45 },
      { "procedureCode": "V2784", "providerVolume": 150, "peerAverageVolume": 30 }
    ],
    "aiSummary": {
      "patternDeviation": "Significant deviation from regional peers in billing codes V2784 and 92250.",
      "velocityIndicator": "Claim submission volume for premium services increased by 45% in the last quarter.",
      "recommendation": "Initiate targeted audit for medical necessity documentation on code V2784."
    }
  },
  "meta": { "requestId": "req_provider_detail_001", "generatedAt": "2026-06-04T09:35:15Z" },
  "error": null
}
```

**Implementation note:** `procedurePeerComparison` is computed as: for each procedure code the provider billed, compare their volume to the mean volume of all providers who billed the same code.

---

## 5. New Claim Scoring

### `POST /api/scoring/jobs`

Submit a new claim for scoring. Accepts multipart file upload OR JSON body.

**JSON Body (manual entry):**
```json
{
  "sourceType": "manual",
  "claim": {
    "procedureCode": "92250",
    "procedureDesc": "Fundus Photography",
    "allowedAmount": 185.0,
    "amtCharged": 420.0,
    "units": 1,
    "memberAge": 42,
    "memberGender": "Male",
    "providerId": "PRV-3391",
    "serviceDate": "2026-06-04",
    "benefitType": "Exam",
    "serviceCategoryName": "Eye Exam",
    "benefitCategoryName": "Professional Services"
  }
}
```

**File Upload (multipart):** Field name `file`, accepts `.xlsx`, `.csv`, `.json`

**Response:**
```json
{
  "data": {
    "jobId": "JOB-20260604-001",
    "status": "queued",
    "sourceType": "manual",
    "submittedAt": "2026-06-04T09:36:00Z"
  },
  "meta": { "requestId": "req_score_create_001", "generatedAt": "2026-06-04T09:36:00Z" },
  "error": null
}
```

---

### `GET /api/scoring/jobs/:jobId`

Poll for job status and pipeline progress.

**Response:**
```json
{
  "data": {
    "jobId": "JOB-20260604-001",
    "status": "processing",
    "progressPercent": 75,
    "activeStage": "ML Outlier Detection...",
    "stages": [
      { "code": "validate",   "label": "Validating Format...",          "status": "completed",  "progressPercent": 15 },
      { "code": "rules",      "label": "Rule Engine Analysis...",       "status": "completed",  "progressPercent": 35 },
      { "code": "statistics", "label": "Statistical Profiling...",      "status": "completed",  "progressPercent": 55 },
      { "code": "ml",         "label": "ML Outlier Detection...",       "status": "processing", "progressPercent": 75 },
      { "code": "cluster",    "label": "Assigning Behavioral Clusters...","status": "pending",   "progressPercent": 85 },
      { "code": "summary",    "label": "Generating AI Summary...",      "status": "pending",    "progressPercent": 95 }
    ]
  },
  "meta": { "requestId": "req_score_status_001", "generatedAt": "2026-06-04T09:36:15Z" },
  "error": null
}
```

---

### `GET /api/scoring/jobs/:jobId/result`

Fetch full ClaimAnalysis once job is completed. Uses the **same contract** as `GET /api/claims/:claimId`.

```json
{
  "data": {
    "claim": {
      "id": "TEMP-20260604-a1b2c3d4",
      "providerId": "PRV-3391",
      "procedureCode": "92250",
      "allowedAmount": 185.0,
      "fraudScore": 86,
      "riskLevel": "Critical",
      "fraudType": "Unbundling Exclusivity",
      "status": "Pending"
    },
    "analysis": {
      "pipeline": {
        "runId": "RUN-20260604-015",
        "status": "completed",
        "submittedAt": "2026-06-04T09:36:00Z",
        "completedAt": "2026-06-04T09:36:28Z",
        "statusText": "Scoring Complete"
      },
      "rulesAnalysis": { "...": "same structure as claim detail" },
      "statisticalAnalysis": { "...": "same structure as claim detail" },
      "mlAnalysis": { "...": "same structure as claim detail" },
      "clusterAssignment": { "...": "same structure as claim detail" },
      "aiSummary": {
        "summary": "There is a very high probability of intentional Unbundling.",
        "riskReasoning": "Codes 92250 and 92134 were billed together without the expected modifier pattern.",
        "recommendation": "Suspend auto-adjudication and route to Tier 2 SIU review."
      },
      "actions": { "canAssignAnalyst": true }
    }
  },
  "meta": { "requestId": "req_score_result_001", "generatedAt": "2026-06-04T09:36:28Z" },
  "error": null
}
```

---

### `POST /api/scoring/jobs/:jobId/assign-siu`

Assign a scored claim to the SIU queue.

**Response:**
```json
{
  "data": {
    "jobId": "JOB-20260604-001",
    "assignedQueue": "SIU",
    "assignedAt": "2026-06-04T09:37:00Z",
    "status": "Investigating"
  },
  "meta": { "requestId": "req_assign_001", "generatedAt": "2026-06-04T09:37:00Z" },
  "error": null
}
```

---

## 6. Global Services

### `GET /api/search?query=<string>`

Cross-entity search across claims and providers.

**Response:**
```json
{
  "data": {
    "claims": [
      { "id": "CLM-7718290", "providerName": "Vision Center Excellence", "riskLevel": "High" }
    ],
    "providers": [
      { "id": "PRV-1029", "name": "Vision Center Excellence", "riskScore": 89 }
    ]
  },
  "meta": { "requestId": "req_search_001", "generatedAt": "2026-06-04T09:38:00Z" },
  "error": null
}
```

---

### `GET /api/notifications`

Bell icon notifications.

**Response:**
```json
{
  "data": {
    "unreadCount": 3,
    "items": [
      {
        "id": "NTF-001",
        "type": "claim_flagged",
        "title": "Critical claim flagged",
        "message": "Claim CLM-3310928 exceeded fraud threshold.",
        "createdAt": "2026-06-04T09:20:00Z",
        "read": false
      }
    ]
  },
  "meta": { "requestId": "req_notifications_001", "generatedAt": "2026-06-04T09:38:15Z" },
  "error": null
}
```

---

### `GET /api/system/status`

Model AI and pipeline status for the sidebar.

**Response:**
```json
{
  "data": {
    "modelAi": "ONLINE",
    "pipeline": "SYNCED",
    "lastSuccessfulRunAt": "2026-06-04T09:25:00Z"
  },
  "meta": { "requestId": "req_status_001", "generatedAt": "2026-06-04T09:38:30Z" },
  "error": null
}
```

---

## Error Responses

All errors follow this format:

```json
{
  "data": null,
  "meta": { "requestId": "req_001", "generatedAt": "2026-06-04T09:38:00Z" },
  "error": {
    "code": "CLAIM_NOT_FOUND",
    "message": "Claim with ID CLM-9999 was not found.",
    "statusCode": 404
  }
}
```

**Standard error codes:**

| HTTP Status | Code | Meaning |
|---|---|---|
| 400 | `VALIDATION_ERROR` | Invalid request body or params |
| 404 | `NOT_FOUND` | Resource not found |
| 409 | `JOB_ALREADY_EXISTS` | Duplicate scoring job |
| 422 | `INVALID_CLAIM_FORMAT` | Claim data fails pipeline validation |
| 500 | `PIPELINE_ERROR` | Internal pipeline failure |
| 503 | `AI_SERVICE_UNAVAILABLE` | OpenAI API unreachable |
