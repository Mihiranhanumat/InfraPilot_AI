# InfraPilot AI — Incident Investigation Report
**Incident ID:** `INC-1001` | **Severity:** `Validated hypothesis`
**Generated:** 2026-10-14 00:08:09 UTC
**Investigation Status:** `Validated hypothesis` (Critic Verdict: `PASS`)

---

## 1. Executive Summary
- **Observed Symptoms:** Order API p95 latency spiked above 2000ms with elevated 504 Gateway Timeouts impacting checkout flow. Users unable to place orders.
- **Leading Hypothesis:** Database latency elevation and connection pool saturation is the primary upstream root cause.
- **Identified Culprit Service:** `database`
- **Confidence Rating:** **99.0%** (*Heuristic Evidence Score (Transparent Multi-Source Metric)*)

---

## 2. Hypothesis Ranking & Heuristic Scoring
### Rank 1: `database` — Score: 99.0%
- **Claim:** Database latency elevation and connection pool saturation is the primary upstream root cause.
- **Reasoning:** Database metrics show sharp connection exhaustion and p95 latency elevation preceding Order API latency spikes. Database timeout logs match the failure window, and Order API directly depends on the database for checkout transactions.
- **Timeline Fit:** database anomaly began at 2026-10-13T10:16:00, strictly preceding downstream symptom onset at 2026-10-13T10:18:00.
- **Dependency Fit:** database is an upstream dependency topologically connected to symptom services (order_api, frontend).
- **Supporting Evidence IDs:** `METRIC-DAT-01, METRIC-DAT-04, METRIC-DAT-05, LOG-DAT-01, LOG-DAT-03, EVENT-DAT-01, EVENT-DAT-02, DEP-DAT-03`
- **Heuristic Score Breakdown:**
  - `metric_support`: 1.0
  - `log_support`: 1.0
  - `dependency_support`: 0.95
  - `timeline_support`: 1.0
  - `contradiction_penalty`: 0.0
  - `aggregate_heuristic_score`: 0.99

### Rank 2: `order_api` — Score: 88.0%
- **Claim:** Service 'order_api' exhibits anomalous signals that correlate with the ongoing incident.
- **Reasoning:** Telemetry signals on order_api exhibit divergence from baseline. Supporting evidence IDs: METRIC-ORD-02, METRIC-ORD-06, LOG-DAT-01, LOG-ORD-02, EVENT-ORD-03.
- **Timeline Fit:** order_api anomaly synchronized with symptom onset at 2026-10-13T10:18:00.
- **Dependency Fit:** order_api is an immediate endpoint experiencing reported symptoms.
- **Supporting Evidence IDs:** `METRIC-ORD-02, METRIC-ORD-06, LOG-DAT-01, LOG-ORD-02, EVENT-ORD-03`
- **Heuristic Score Breakdown:**
  - `metric_support`: 1.0
  - `log_support`: 1.0
  - `dependency_support`: 0.7
  - `timeline_support`: 0.75
  - `contradiction_penalty`: 0.0
  - `aggregate_heuristic_score`: 0.88

### Rank 3: `frontend` — Score: 72.0%
- **Claim:** Service 'frontend' exhibits anomalous signals that correlate with the ongoing incident.
- **Reasoning:** Telemetry signals on frontend exhibit divergence from baseline. Supporting evidence IDs: METRIC-FRO-03, METRIC-FRO-07, LOG-ORD-02.
- **Timeline Fit:** frontend anomaly onset (2026-10-13T10:19:00) lagged after symptoms (2026-10-13T10:18:00). Likely downstream symptom, not cause.
- **Dependency Fit:** frontend is an immediate endpoint experiencing reported symptoms.
- **Supporting Evidence IDs:** `METRIC-FRO-03, METRIC-FRO-07, LOG-ORD-02`
- **Heuristic Score Breakdown:**
  - `metric_support`: 1.0
  - `log_support`: 0.8
  - `dependency_support`: 0.7
  - `timeline_support`: 0.2
  - `contradiction_penalty`: 0.0
  - `aggregate_heuristic_score`: 0.72

---

## 3. Read-Only Diagnostic Validation
- **[PASS] Topological Viability Test:** Candidate 'database' has valid caller paths to ['order_api', 'frontend']
- **[PASS] Timeline Precedence Test:** database (p95_latency_ms) anomaly began at 2026-10-13T10:16:00, preceding order_api (p95_latency_ms) at 2026-10-13T10:18:00 by 120.0s.
- **[PASS] Log Correlation Verification:** Found 12 logs matching 'timeout|error|exception|saturated|eviction' on service database after 2026-10-13T10:16:00.

---

## 4. Evidence Trail
| Evidence ID | Source | Service | Support | Description |
|---|---|---|---|---|
| `METRIC-DAT-01` | metric | `database` | supports | database p95_latency_ms rose from baseline 11.51ms to 1387.96ms (+11962.6%), earliest onset 2026-10-13T10:16:00. |
| `METRIC-ORD-02` | metric | `order_api` | supports | order_api p95_latency_ms rose from baseline 40.56ms to 2022.27ms (+4885.5%), earliest onset 2026-10-13T10:18:00. |
| `METRIC-FRO-03` | metric | `frontend` | supports | frontend p95_latency_ms rose from baseline 64.56ms to 1956.4ms (+2930.1%), earliest onset 2026-10-13T10:19:00. |
| `METRIC-DAT-04` | metric | `database` | supports | database db_connections_pct rose from baseline 28.66% to 96.97% (+238.4%), earliest onset 2026-10-13T10:16:00. |
| `METRIC-DAT-05` | metric | `database` | supports | database cpu_pct rose from baseline 24.51% to 78.07% (+218.5%), earliest onset 2026-10-13T10:16:00. |
| `METRIC-ORD-06` | metric | `order_api` | supports | order_api error_rate_pct rose from baseline 0.12% to 16.0% (+13516.4%), earliest onset 2026-10-13T10:18:00. |
| `METRIC-FRO-07` | metric | `frontend` | supports | frontend error_rate_pct rose from baseline 0.06% to 13.75% (+23804.3%), earliest onset 2026-10-13T10:19:00. |
| `EVENT-DAT-01` | event | `database` | supports | Operational event [MAINTENANCE]: Routine database index defragmentation completed successfully. |
| `EVENT-DAT-02` | event | `database` | supports | Operational event [ALERT_FIRED]: DBConnectionPoolSaturation: Active connections exceeded 90% threshold. |
| `EVENT-ORD-03` | event | `order_api` | supports | Operational event [ALERT_FIRED]: ServiceLatencyP95Critical: Order API latency breached 2000ms SLO. |
| `LOG-DAT-01` | log | `database` | supports | Log cluster 'DB_TIMEOUT_OR_EXHAUSTION' (16 occurrences, WARN) on database, order_api. Sample: "Connection pool saturated: active=92/100 connections in use" |
| `LOG-ORD-02` | log | `order_api` | supports | Log cluster 'HTTP_5XX_ERROR' (8 occurrences, ERROR) on order_api, frontend. Sample: "Failed to complete checkout: 504 Gateway Timeout downstream dependency (database)" |
| `LOG-DAT-03` | log | `database` | supports | Log cluster 'QUERY_LATENCY_OR_TIMEOUT' (6 occurrences, ERROR) on database. Sample: "Query execution timeout after 30000ms: SELECT * FROM orders WHERE user_id=?" |
| `DEP-FRO-01` | dependency | `frontend` | supports | Topology verification: 'frontend' is an upstream dependency of symptom services (order_api, frontend). Call paths: frontend (direct symptom). |
| `DEP-ORD-02` | dependency | `order_api` | supports | Topology verification: 'order_api' is an upstream dependency of symptom services (order_api, frontend). Call paths: order_api (direct symptom); frontend -> order_api. |
| `DEP-DAT-03` | dependency | `database` | supports | Topology verification: 'database' is an upstream dependency of symptom services (order_api, frontend). Call paths: order_api -> database; frontend -> order_api -> database. |
| `DEP-PAY-04` | dependency | `payment_service` | supports | Topology verification: 'payment_service' is an upstream dependency of symptom services (order_api, frontend). Call paths: order_api -> payment_service; frontend -> order_api -> payment_service. |
| `DEP-INV-05` | dependency | `inventory_service` | supports | Topology verification: 'inventory_service' is an upstream dependency of symptom services (order_api, frontend). Call paths: order_api -> inventory_service; frontend -> order_api -> inventory_service. |
| `DEP-CAC-06` | dependency | `cache` | supports | Topology verification: 'cache' is an upstream dependency of symptom services (order_api, frontend). Call paths: order_api -> cache; frontend -> order_api -> cache. |
| `DIAG-DAT-01` | diagnostic | `database` | supports | Read-only diagnostic battery completed: 3/3 active checks passed for hypothesis 'Database latency elevation and connection pool saturation is the primary upstream root cause.'. |

---

## 5. Recommended Recovery Next Steps
> **NOTICE:** All actions are strictly advisory recommendations (`RECOMMENDATION_ONLY`). No automated mutations have been executed. Explicit human approval from an authorized engineer is required.

### Step 1: Inspect active database queries and slow query logs for unindexed scans or connection pool locks.
- **Target Service:** `database` | **Category:** `QUERY_INVESTIGATION` | **Risk:** `LOW`
- **Rationale:** Pinpoint long-running blocking queries causing thread saturation without restarting the cluster.
- **Post-Verification Check:** Observe active connection count drop below 70% threshold in monitoring dashboard.
- **Status:** `RECOMMENDATION_ONLY` (Reversible: `True`)

### Step 2: Review database connection pool settings and HikariCP maximumPoolSize across Order API worker instances.
- **Target Service:** `order_api` | **Category:** `CONNECTION_POOL_TUNING` | **Risk:** `LOW`
- **Rationale:** Prevent connection exhaustion cascades while queries are being optimized.
- **Post-Verification Check:** Verify Order API connection wait time drops below 50ms.
- **Status:** `RECOMMENDATION_ONLY` (Reversible: `True`)

### Step 3: Compare recent database schema changes or index migrations against incident onset timestamp.
- **Target Service:** `database` | **Category:** `CONFIGURATION_AUDIT` | **Risk:** `LOW`
- **Rationale:** Rule out inadvertent index drops or locks introduced by automated migration jobs.
- **Post-Verification Check:** Confirm query execution plan cost matches pre-incident baseline.
- **Status:** `RECOMMENDATION_ONLY` (Reversible: `True`)

### Step 4: Monitor downstream Order API p95 latency and HTTP 504 error rate after authorized engineer intervention.
- **Target Service:** `order_api` | **Category:** `DOWNSTREAM_MONITORING` | **Risk:** `LOW`
- **Rationale:** Ensure recovery propagates downstream to restore end-to-end checkout functionality.
- **Post-Verification Check:** Confirm Order API p95 latency stabilizes below 60ms and error rate < 0.2%.
- **Status:** `RECOMMENDATION_ONLY` (Reversible: `True`)

---

## 6. Uncertainty, Limitations & Safety Disclaimers
- **Telemetry Limitations:** Synthetically generated local telemetry. Correlations establish strong hypotheses, but causality is supported rather than definitively proven. No production claims or absolute certainty guaranteed.
- **Safety Policy Enforcement:** SIMULATION ONLY: Read-only diagnostics. No real cloud resources or infrastructure commands are modified.
- **Human Review Gate:** Human engineers must inspect live telemetry and review these findings prior to executing operational runbooks.
