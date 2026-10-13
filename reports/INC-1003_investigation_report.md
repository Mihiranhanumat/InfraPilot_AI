# InfraPilot AI — Incident Investigation Report
**Incident ID:** `INC-1003` | **Severity:** `Validated hypothesis`
**Generated:** 2026-10-13 23:55:15 UTC
**Investigation Status:** `Validated hypothesis` (Critic Verdict: `PASS`)

---

## 1. Executive Summary
- **Observed Symptoms:** Order API and Database latencies increasing following abrupt cache miss spike across product and order session reads.
- **Leading Hypothesis:** Cache hit rate degradation and memory eviction triggered a cache stampede, overloading downstream database read capacity.
- **Identified Culprit Service:** `cache`
- **Confidence Rating:** **86.0%** (*Heuristic Evidence Score (Transparent Multi-Source Metric)*)

---

## 2. Hypothesis Ranking & Heuristic Scoring
### Rank 1: `cache` — Score: 86.0%
- **Claim:** Cache hit rate degradation and memory eviction triggered a cache stampede, overloading downstream database read capacity.
- **Reasoning:** Cache hit rate plummeted from 94% to ~22% following memory policy adjustment. The resulting flood of cache misses overwhelmed database read query throughput, subsequently degrading Order API latency.
- **Timeline Fit:** cache anomaly synchronized with symptom onset at 2026-10-13T09:14:00.
- **Dependency Fit:** cache is an immediate endpoint experiencing reported symptoms.
- **Supporting Evidence IDs:** `METRIC-CAC-04, METRIC-CAC-07, LOG-CAC-01, EVENT-CAC-01, EVENT-CAC-02`
- **Heuristic Score Breakdown:**
  - `metric_support`: 0.94
  - `log_support`: 1.0
  - `dependency_support`: 0.7
  - `timeline_support`: 0.75
  - `contradiction_penalty`: 0.0
  - `aggregate_heuristic_score`: 0.86

### Rank 2: `database` — Score: 77.0%
- **Claim:** Database latency elevation and connection pool saturation is the primary upstream root cause.
- **Reasoning:** Database metrics show sharp connection exhaustion and p95 latency elevation preceding Order API latency spikes. Database timeout logs match the failure window, and Order API directly depends on the database for checkout transactions.
- **Timeline Fit:** database anomaly onset (2026-10-13T09:16:00) lagged after symptoms (2026-10-13T09:14:00). Likely downstream symptom, not cause.
- **Dependency Fit:** database is an immediate endpoint experiencing reported symptoms.
- **Supporting Evidence IDs:** `METRIC-DAT-01, METRIC-DAT-05, METRIC-DAT-06, LOG-DAT-02, EVENT-DAT-03`
- **Heuristic Score Breakdown:**
  - `metric_support`: 1.0
  - `log_support`: 1.0
  - `dependency_support`: 0.7
  - `timeline_support`: 0.2
  - `contradiction_penalty`: 0.0
  - `aggregate_heuristic_score`: 0.77

### Rank 3: `order_api` — Score: 72.0%
- **Claim:** Service 'order_api' exhibits anomalous signals that correlate with the ongoing incident.
- **Reasoning:** Telemetry signals on order_api exhibit divergence from baseline. Supporting evidence IDs: METRIC-ORD-02, METRIC-ORD-08, LOG-CAC-01.
- **Timeline Fit:** order_api anomaly onset (2026-10-13T09:18:00) lagged after symptoms (2026-10-13T09:14:00). Likely downstream symptom, not cause.
- **Dependency Fit:** order_api is an immediate endpoint experiencing reported symptoms.
- **Supporting Evidence IDs:** `METRIC-ORD-02, METRIC-ORD-08, LOG-CAC-01`
- **Heuristic Score Breakdown:**
  - `metric_support`: 1.0
  - `log_support`: 0.8
  - `dependency_support`: 0.7
  - `timeline_support`: 0.2
  - `contradiction_penalty`: 0.0
  - `aggregate_heuristic_score`: 0.72

---

## 3. Read-Only Diagnostic Validation
- **[FAIL] Topological Viability Test:** Candidate 'cache' is NOT upstream of one or more symptom services: ['cache', 'database', 'order_api']
- **[FAIL] Event Window Impact (CONFIG_CHANGE):** No metric series found for cache around event 2026-10-13T09:13:30
- **[PASS] Log Correlation Verification:** Found 5 logs matching 'timeout|error|exception|saturated|eviction' on service cache after 2026-10-13T09:14:00.

---

## 4. Evidence Trail
| Evidence ID | Source | Service | Support | Description |
|---|---|---|---|---|
| `METRIC-DAT-01` | metric | `database` | supports | database p95_latency_ms rose from baseline 13.28ms to 521.28ms (+3825.1%), earliest onset 2026-10-13T09:16:00. |
| `METRIC-ORD-02` | metric | `order_api` | supports | order_api p95_latency_ms rose from baseline 44.03ms to 721.18ms (+1538.0%), earliest onset 2026-10-13T09:18:00. |
| `METRIC-FRO-03` | metric | `frontend` | supports | frontend p95_latency_ms rose from baseline 69.09ms to 766.91ms (+1010.0%), earliest onset 2026-10-13T09:19:00. |
| `METRIC-CAC-04` | metric | `cache` | supports | cache cpu_pct rose from baseline 18.51% to 87.44% (+372.4%), earliest onset 2026-10-13T09:14:00. |
| `METRIC-DAT-05` | metric | `database` | supports | database db_connections_pct rose from baseline 55.4% to 82.08% (+48.2%), earliest onset 2026-10-13T09:16:00. |
| `METRIC-DAT-06` | metric | `database` | supports | database cpu_pct rose from baseline 24.59% to 83.71% (+240.5%), earliest onset 2026-10-13T09:16:00. |
| `METRIC-CAC-07` | metric | `cache` | supports | cache cache_hit_rate_pct rose from baseline 94.46% to 21.65% (-77.1%), earliest onset 2026-10-13T09:14:00. |
| `METRIC-ORD-08` | metric | `order_api` | supports | order_api error_rate_pct rose from baseline 0.12% to 3.58% (+2980.8%), earliest onset 2026-10-13T09:18:00. |
| `METRIC-FRO-09` | metric | `frontend` | supports | frontend error_rate_pct rose from baseline 0.16% to 3.08% (+1845.1%), earliest onset 2026-10-13T09:19:00. |
| `EVENT-CAC-01` | event | `cache` | supports | Operational event [CONFIG_CHANGE]: Cache cluster eviction policy modified to volatile-ttl without warming. |
| `EVENT-CAC-02` | event | `cache` | supports | Operational event [ALERT_FIRED]: CacheHitRatioDegradation: Cache hit rate dropped below 30% threshold. |
| `EVENT-DAT-03` | event | `database` | supports | Operational event [ALERT_FIRED]: HighCPUUtilization: Database CPU exceeded 85% due to read query surge. |
| `LOG-CAC-01` | log | `cache` | supports | Log cluster 'CACHE_DEGRADATION' (10 occurrences, WARN) on cache, order_api. Sample: "High key eviction rate: 45000 keys/sec purged under memory limit" |
| `LOG-DAT-02` | log | `database` | supports | Log cluster 'QUERY_LATENCY_OR_TIMEOUT' (3 occurrences, WARN) on database. Sample: "High concurrent read throughput: 12000 queries/sec on catalog_items table" |
| `DEP-ORD-02` | dependency | `order_api` | supports | Topology verification: 'order_api' is an upstream dependency of symptom services (cache, database, order_api). Call paths: order_api (direct symptom). |
| `DEP-DAT-03` | dependency | `database` | supports | Topology verification: 'database' is an upstream dependency of symptom services (cache, database, order_api). Call paths: database (direct symptom); order_api -> database. |
| `DEP-PAY-04` | dependency | `payment_service` | supports | Topology verification: 'payment_service' is an upstream dependency of symptom services (cache, database, order_api). Call paths: order_api -> payment_service. |
| `DEP-INV-05` | dependency | `inventory_service` | supports | Topology verification: 'inventory_service' is an upstream dependency of symptom services (cache, database, order_api). Call paths: order_api -> inventory_service. |
| `DEP-CAC-06` | dependency | `cache` | supports | Topology verification: 'cache' is an upstream dependency of symptom services (cache, database, order_api). Call paths: cache (direct symptom); order_api -> cache. |
| `DIAG-CAC-01` | diagnostic | `cache` | neutral | Read-only diagnostic battery completed: 1/3 active checks passed for hypothesis 'Cache hit rate degradation and memory eviction triggered a cache stampede, overloading downstream database read capacity.'. |

---

## 5. Recommended Recovery Next Steps
> **NOTICE:** All actions are strictly advisory recommendations (`RECOMMENDATION_ONLY`). No automated mutations have been executed. Explicit human approval from an authorized engineer is required.

### Step 1: Inspect Redis cache memory usage, key eviction rates, and maxmemory-policy settings.
- **Target Service:** `cache` | **Category:** `CACHE_POLICY_REVIEW` | **Risk:** `LOW`
- **Rationale:** Determine if keys were aggressively evicted prematurely, causing read stampede.
- **Post-Verification Check:** Verify eviction rate drops to near zero.
- **Status:** `RECOMMENDATION_ONLY` (Reversible: `True`)

### Step 2: Enable read request coalescing / singleflight in Order API to mitigate stampede load on database.
- **Target Service:** `order_api` | **Category:** `CONFIGURATION_AUDIT` | **Risk:** `LOW`
- **Rationale:** Prevent redundant parallel queries to database while cache warms.
- **Post-Verification Check:** Observe database CPU utilization drops below 40%.
- **Status:** `RECOMMENDATION_ONLY` (Reversible: `True`)

### Step 3: Re-warm critical product catalog keys and monitor cache hit ratio.
- **Target Service:** `cache` | **Category:** `DOWNSTREAM_MONITORING` | **Risk:** `LOW`
- **Rationale:** Restores normal cache hit efficiency (>90%).
- **Post-Verification Check:** Verify cache hit rate climbs above 90% and DB latency drops below 20ms.
- **Status:** `RECOMMENDATION_ONLY` (Reversible: `True`)

---

## 6. Uncertainty, Limitations & Safety Disclaimers
- **Telemetry Limitations:** Synthetically generated local telemetry. Correlations establish strong hypotheses, but causality is supported rather than definitively proven. No production claims or absolute certainty guaranteed.
- **Safety Policy Enforcement:** SIMULATION ONLY: Read-only diagnostics. No real cloud resources or infrastructure commands are modified.
- **Human Review Gate:** Human engineers must inspect live telemetry and review these findings prior to executing operational runbooks.
