"""
Generate rich, reproducible synthetic telemetry for InfraPilot AI scenarios.
Produces:
- data/metrics.csv
- data/logs.csv
- data/events.csv
"""
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent

np.random.seed(42)

def generate_scenario_a():
    """
    Scenario A (INC-1001): Database Latency Spike & Connection Pool Saturation
    Timeline:
    10:00-10:15: Baseline across all services.
    10:16: Database connections jump to ~94%, DB p95 latency jumps from 12ms to 1250ms.
    10:18: Order API p95 latency jumps from 42ms to 2400ms.
    10:20: Order API error rate jumps from 0.1% to 15.2%.
    Frontend experiences symptoms following Order API.
    Distractor: Payment service minor memory blip at 10:22 (harmless).
    """
    start_time = datetime(2026, 10, 13, 10, 0, 0)
    minutes = 31
    metrics_rows = []
    logs_rows = []
    events_rows = []

    # Events
    events_rows.append({
        "timestamp": "2026-10-13T02:00:00",
        "incident_id": "INC-1001",
        "service": "database",
        "event_type": "MAINTENANCE",
        "description": "Routine database index defragmentation completed successfully."
    })
    events_rows.append({
        "timestamp": "2026-10-13T10:16:30",
        "incident_id": "INC-1001",
        "service": "database",
        "event_type": "ALERT_FIRED",
        "description": "DBConnectionPoolSaturation: Active connections exceeded 90% threshold."
    })
    events_rows.append({
        "timestamp": "2026-10-13T10:19:00",
        "incident_id": "INC-1001",
        "service": "order_api",
        "event_type": "ALERT_FIRED",
        "description": "ServiceLatencyP95Critical: Order API latency breached 2000ms SLO."
    })

    for m in range(minutes):
        t = start_time + timedelta(minutes=m)
        t_str = t.strftime("%Y-%m-%dT%H:%M:%S")

        # Database metrics
        if m < 16:
            db_lat = 12.0 + np.random.normal(0, 1.5)
            db_err = 0.0 + max(0, np.random.normal(0, 0.02))
            db_cpu = 25.0 + np.random.normal(0, 3.0)
            db_conn = 28.0 + np.random.normal(0, 2.0)
        else:
            db_lat = 1200.0 + (m - 16) * 25.0 + np.random.normal(0, 40.0)
            db_err = 1.2 + np.random.normal(0, 0.2)
            db_cpu = 78.0 + np.random.normal(0, 4.0)
            db_conn = 94.0 + min(5.0, (m - 16) * 0.5) + np.random.normal(0, 1.0)
        
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "database", "metric_name": "p95_latency_ms", "value": round(max(5.0, db_lat), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "database", "metric_name": "error_rate_pct", "value": round(max(0.0, db_err), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "database", "metric_name": "cpu_pct", "value": round(min(100.0, max(5.0, db_cpu)), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "database", "metric_name": "db_connections_pct", "value": round(min(100.0, max(5.0, db_conn)), 2), "unit": "%"},
        ])

        # Order API metrics
        if m < 18:
            ord_lat = 42.0 + np.random.normal(0, 3.0)
            ord_err = 0.1 + max(0, np.random.normal(0, 0.05))
            ord_cpu = 30.0 + np.random.normal(0, 3.0)
        else:
            ord_lat = 2100.0 + (m - 18) * 35.0 + np.random.normal(0, 50.0)
            ord_err = 14.5 + min(6.0, (m - 18) * 0.8) + np.random.normal(0, 0.5)
            ord_cpu = 45.0 + np.random.normal(0, 4.0)
        
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "order_api", "metric_name": "p95_latency_ms", "value": round(max(10.0, ord_lat), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "order_api", "metric_name": "error_rate_pct", "value": round(max(0.0, ord_err), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "order_api", "metric_name": "cpu_pct", "value": round(min(100.0, max(5.0, ord_cpu)), 2), "unit": "%"},
        ])

        # Frontend metrics
        if m < 19:
            fe_lat = 65.0 + np.random.normal(0, 4.0)
            fe_err = 0.05 + max(0, np.random.normal(0, 0.02))
        else:
            fe_lat = 2250.0 + (m - 19) * 30.0 + np.random.normal(0, 45.0)
            fe_err = 13.8 + min(5.0, (m - 19) * 0.7) + np.random.normal(0, 0.4)
        
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "frontend", "metric_name": "p95_latency_ms", "value": round(max(15.0, fe_lat), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "frontend", "metric_name": "error_rate_pct", "value": round(max(0.0, fe_err), 2), "unit": "%"},
        ])

        # Payment Service metrics (Healthy with distractor memory bump at 10:22)
        pm_cpu = 35.0 + (18.0 if 22 <= m <= 25 else 0.0) + np.random.normal(0, 2.5)
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "payment_service", "metric_name": "p95_latency_ms", "value": round(max(10.0, 38.0 + np.random.normal(0, 2.0)), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "payment_service", "metric_name": "error_rate_pct", "value": round(max(0.0, 0.02 + np.random.normal(0, 0.01)), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "payment_service", "metric_name": "cpu_pct", "value": round(min(100.0, max(5.0, pm_cpu)), 2), "unit": "%"},
        ])

        # Cache metrics (Healthy)
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "cache", "metric_name": "cache_hit_rate_pct", "value": round(93.5 + np.random.normal(0, 1.0), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1001", "service": "cache", "metric_name": "cpu_pct", "value": round(15.0 + np.random.normal(0, 2.0), 2), "unit": "%"},
        ])

        # Logs
        if m < 16:
            if m % 5 == 0:
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1001", "service": "database", "level": "INFO", "message": "Connection pool health check OK: active=28/100, idle=72", "event_type": "HEALTH_CHECK"})
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1001", "service": "order_api", "level": "INFO", "message": "Order processing loop throughput nominal: 145 req/sec", "event_type": "THROUGHPUT"})
        else:
            # During incident
            if m in [16, 17, 18, 22, 26, 29]:
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1001", "service": "database", "level": "WARN", "message": f"Connection pool saturated: active={int(db_conn)}/100 connections in use", "event_type": "POOL_SATURATION"})
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1001", "service": "database", "level": "ERROR", "message": "Query execution timeout after 30000ms: SELECT * FROM orders WHERE user_id=?", "event_type": "QUERY_TIMEOUT"})
            if m >= 18 and m in [18, 20, 21, 24, 28]:
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1001", "service": "order_api", "level": "ERROR", "message": "HikariPool-1 - Connection is not available, request timed out after 5000ms talking to database", "event_type": "DB_CONNECTION_TIMEOUT"})
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1001", "service": "order_api", "level": "ERROR", "message": "Failed to complete checkout: 504 Gateway Timeout downstream dependency (database)", "event_type": "GATEWAY_TIMEOUT"})
            if m >= 20 and m in [20, 23, 27]:
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1001", "service": "frontend", "level": "ERROR", "message": "HTTP 504 received from /api/v1/orders/checkout", "event_type": "HTTP_504"})
            if m == 22:
                # Distractor log
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1001", "service": "payment_service", "level": "INFO", "message": "Minor garbage collection pause 120ms; transaction rate steady", "event_type": "GC_PAUSE"})
                # Untrusted log demonstration
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1001", "service": "order_api", "level": "WARN", "message": "Untrusted request payload logged: DROP TABLE orders; rm -rf / --no-preserve-root", "event_type": "PAYLOAD_LOG"})

    return metrics_rows, logs_rows, events_rows


def generate_scenario_b():
    """
    Scenario B (INC-1002): Deployment-Related API Errors
    Timeline:
    14:00-14:11: Baseline.
    14:12: Order API deployment event v2.4.1.
    14:13: Order API error rate surges from 0.1% to 28.5%.
    Database & cache remain completely healthy.
    Distractor: Slight cache hit fluctuation from 94% to 89%.
    """
    start_time = datetime(2026, 10, 13, 14, 0, 0)
    minutes = 31
    metrics_rows = []
    logs_rows = []
    events_rows = []

    events_rows.append({
        "timestamp": "2026-10-13T14:12:00",
        "incident_id": "INC-1002",
        "service": "order_api",
        "event_type": "DEPLOYMENT",
        "description": "Order API deployed release v2.4.1 (commit sha 78ab9ef) by CI/CD pipeline."
    })
    events_rows.append({
        "timestamp": "2026-10-13T14:14:15",
        "incident_id": "INC-1002",
        "service": "order_api",
        "event_type": "ALERT_FIRED",
        "description": "HighErrorRateBreach: Order API 5xx errors reached 28%."
    })

    for m in range(minutes):
        t = start_time + timedelta(minutes=m)
        t_str = t.strftime("%Y-%m-%dT%H:%M:%S")

        # Database is completely healthy throughout
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "database", "metric_name": "p95_latency_ms", "value": round(11.5 + np.random.normal(0, 1.0), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "database", "metric_name": "error_rate_pct", "value": round(max(0.0, 0.01 + np.random.normal(0, 0.01)), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "database", "metric_name": "cpu_pct", "value": round(22.0 + np.random.normal(0, 2.0), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "database", "metric_name": "db_connections_pct", "value": round(26.0 + np.random.normal(0, 2.0), 2), "unit": "%"},
        ])

        # Order API: Error rate spikes directly post deployment (m >= 13)
        if m < 13:
            ord_err = 0.15 + max(0, np.random.normal(0, 0.04))
            ord_lat = 44.0 + np.random.normal(0, 3.0)
        else:
            ord_err = 28.5 + np.random.normal(0, 1.2)
            ord_lat = 62.0 + np.random.normal(0, 4.0)  # slight latency increase due to error handling
        
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "order_api", "metric_name": "p95_latency_ms", "value": round(max(10.0, ord_lat), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "order_api", "metric_name": "error_rate_pct", "value": round(max(0.0, ord_err), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "order_api", "metric_name": "cpu_pct", "value": round(32.0 + np.random.normal(0, 3.0), 2), "unit": "%"},
        ])

        # Frontend mirrors the errors
        if m < 13:
            fe_err = 0.1 + max(0, np.random.normal(0, 0.03))
        else:
            fe_err = 26.0 + np.random.normal(0, 1.1)

        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "frontend", "metric_name": "p95_latency_ms", "value": round(68.0 + np.random.normal(0, 4.0), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "frontend", "metric_name": "error_rate_pct", "value": round(max(0.0, fe_err), 2), "unit": "%"},
        ])

        # Distractor Cache hit fluctuation
        cache_hit = (89.0 if 14 <= m <= 18 else 93.5) + np.random.normal(0, 0.8)
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "cache", "metric_name": "cache_hit_rate_pct", "value": round(cache_hit, 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1002", "service": "cache", "metric_name": "cpu_pct", "value": round(14.0 + np.random.normal(0, 1.5), 2), "unit": "%"},
        ])

        # Logs
        if m == 12:
            logs_rows.append({"timestamp": t_str, "incident_id": "INC-1002", "service": "order_api", "level": "INFO", "message": "Deployment v2.4.1 activated. Rolling restart of worker pods complete.", "event_type": "DEPLOY_COMPLETE"})
        elif m >= 13:
            if m in [13, 14, 15, 18, 22, 27]:
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1002", "service": "order_api", "level": "ERROR", "message": "NullPointerException at com.shop.order.OrderValidator.validateDiscountCode(OrderValidator.java:142)", "event_type": "APP_EXCEPTION"})
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1002", "service": "order_api", "level": "ERROR", "message": "HTTP 500 Internal Server Error returned for POST /api/v1/orders/checkout", "event_type": "HTTP_500"})
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1002", "service": "frontend", "level": "ERROR", "message": "Checkout submission failed: Order API returned 500 Internal Server Error", "event_type": "UPSTREAM_ERROR"})
        else:
            if m % 5 == 0:
                logs_rows.append({"timestamp": t_str, "incident_id": "INC-1002", "service": "order_api", "level": "INFO", "message": "Order service healthy, processing 138 req/s", "event_type": "HEARTBEAT"})

    return metrics_rows, logs_rows, events_rows


def generate_scenario_c():
    """
    Scenario C (INC-1003): Cache Degradation & Stampede
    Timeline:
    09:00-09:12: Baseline.
    09:14: Cache hit rate drops from 94% to 22% (cache eviction / cluster memory pressure).
    09:16: Database CPU surges from 22% to 88%, DB p95 latency rises to 480ms due to stampede.
    09:18: Order API p95 latency rises to 820ms.
    Distractor: Inventory service background sync at 09:15.
    """
    start_time = datetime(2026, 10, 13, 9, 0, 0)
    minutes = 31
    metrics_rows = []
    logs_rows = []
    events_rows = []

    events_rows.append({
        "timestamp": "2026-10-13T09:13:30",
        "incident_id": "INC-1003",
        "service": "cache",
        "event_type": "CONFIG_CHANGE",
        "description": "Cache cluster eviction policy modified to volatile-ttl without warming."
    })
    events_rows.append({
        "timestamp": "2026-10-13T09:14:45",
        "incident_id": "INC-1003",
        "service": "cache",
        "event_type": "ALERT_FIRED",
        "description": "CacheHitRatioDegradation: Cache hit rate dropped below 30% threshold."
    })
    events_rows.append({
        "timestamp": "2026-10-13T09:17:10",
        "incident_id": "INC-1003",
        "service": "database",
        "event_type": "ALERT_FIRED",
        "description": "HighCPUUtilization: Database CPU exceeded 85% due to read query surge."
    })

    for m in range(minutes):
        t = start_time + timedelta(minutes=m)
        t_str = t.strftime("%Y-%m-%dT%H:%M:%S")

        # Cache metrics
        if m < 14:
            c_hit = 94.2 + np.random.normal(0, 0.8)
            c_cpu = 18.0 + np.random.normal(0, 2.0)
        else:
            c_hit = 22.0 + np.random.normal(0, 2.5)
            c_cpu = 88.0 + np.random.normal(0, 3.0)
        
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "cache", "metric_name": "cache_hit_rate_pct", "value": round(max(0.0, min(100.0, c_hit)), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "cache", "metric_name": "cpu_pct", "value": round(min(100.0, max(5.0, c_cpu)), 2), "unit": "%"},
        ])

        # Database metrics: Affected by cache stampede starting at m=16
        if m < 16:
            db_cpu = 24.0 + np.random.normal(0, 2.5)
            db_lat = 13.0 + np.random.normal(0, 1.2)
        else:
            db_cpu = 86.0 + min(10.0, (m - 16) * 0.8) + np.random.normal(0, 2.5)
            db_lat = 480.0 + (m - 16) * 15.0 + np.random.normal(0, 20.0)
        
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "database", "metric_name": "p95_latency_ms", "value": round(max(5.0, db_lat), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "database", "metric_name": "cpu_pct", "value": round(min(100.0, max(5.0, db_cpu)), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "database", "metric_name": "error_rate_pct", "value": round(max(0.0, 0.1 + np.random.normal(0, 0.05)), 2), "unit": "%"},
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "database", "metric_name": "db_connections_pct", "value": round(55.0 + (30.0 if m >= 16 else 0.0) + np.random.normal(0, 2.0), 2), "unit": "%"},
        ])

        # Order API metrics: latency rises starting m=18
        if m < 18:
            ord_lat = 45.0 + np.random.normal(0, 3.0)
            ord_err = 0.1 + max(0, np.random.normal(0, 0.03))
        else:
            ord_lat = 820.0 + (m - 18) * 20.0 + np.random.normal(0, 30.0)
            ord_err = 4.5 + np.random.normal(0, 0.4)
        
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "order_api", "metric_name": "p95_latency_ms", "value": round(max(10.0, ord_lat), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "order_api", "metric_name": "error_rate_pct", "value": round(max(0.0, ord_err), 2), "unit": "%"},
        ])

        # Frontend metrics
        if m < 19:
            fe_lat = 68.0 + np.random.normal(0, 3.5)
        else:
            fe_lat = 950.0 + (m - 19) * 20.0 + np.random.normal(0, 30.0)

        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "frontend", "metric_name": "p95_latency_ms", "value": round(max(15.0, fe_lat), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1003", "service": "frontend", "metric_name": "error_rate_pct", "value": round(max(0.0, (4.2 if m >= 19 else 0.05) + np.random.normal(0, 0.3)), 2), "unit": "%"},
        ])

        # Logs
        if m >= 14 and m in [14, 15, 17, 21, 26]:
            logs_rows.append({"timestamp": t_str, "incident_id": "INC-1003", "service": "cache", "level": "WARN", "message": "High key eviction rate: 45000 keys/sec purged under memory limit", "event_type": "CACHE_EVICTION"})
            logs_rows.append({"timestamp": t_str, "incident_id": "INC-1003", "service": "order_api", "level": "WARN", "message": "Cache miss rate high for catalog items; querying database directly (cache stampede)", "event_type": "CACHE_MISS_FALLBACK"})
        if m >= 16 and m in [16, 19, 24]:
            logs_rows.append({"timestamp": t_str, "incident_id": "INC-1003", "service": "database", "level": "WARN", "message": "High concurrent read throughput: 12000 queries/sec on catalog_items table", "event_type": "HIGH_READ_LOAD"})
        if m == 15:
            # Distractor log
            logs_rows.append({"timestamp": t_str, "incident_id": "INC-1003", "service": "inventory_service", "level": "INFO", "message": "Periodic inventory stock synchronization completed in 420ms", "event_type": "SYNC_COMPLETE"})

    return metrics_rows, logs_rows, events_rows


def generate_scenario_d():
    """
    Scenario D (INC-1004): Conflicting or Missing Evidence (Escalation to Human Review)
    Timeline:
    16:00-16:10: Baseline.
    16:15: Sporadic 503s on frontend.
    Database metrics telemetry is missing/dropped.
    Order API metrics show nominal latency (200 OKs).
    Payment logs contain contradictory network blip messages.
    Critic should reject single confident hypothesis and escalate to Human Review.
    """
    start_time = datetime(2026, 10, 13, 16, 0, 0)
    minutes = 31
    metrics_rows = []
    logs_rows = []
    events_rows = []

    events_rows.append({
        "timestamp": "2026-10-13T16:12:00",
        "incident_id": "INC-1004",
        "service": "frontend",
        "event_type": "ALERT_FIRED",
        "description": "IntermittentErrorThreshold: Frontend sporadic 503 errors detected."
    })
    events_rows.append({
        "timestamp": "2026-10-13T16:14:00",
        "incident_id": "INC-1004",
        "service": "database",
        "event_type": "TELEMETRY_DROPOUT",
        "description": "Database telemetry agent lost communication with Prometheus collector."
    })

    for m in range(minutes):
        t = start_time + timedelta(minutes=m)
        t_str = t.strftime("%Y-%m-%dT%H:%M:%S")

        # Frontend metrics: sporadic error spikes but inconsistent
        fe_err = (4.5 if (m >= 15 and m % 2 == 0) else 0.2) + max(0, np.random.normal(0, 0.1))
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1004", "service": "frontend", "metric_name": "p95_latency_ms", "value": round(72.0 + np.random.normal(0, 5.0), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1004", "service": "frontend", "metric_name": "error_rate_pct", "value": round(max(0.0, fe_err), 2), "unit": "%"},
        ])

        # Order API reports completely normal latency & 0 error rate!
        metrics_rows.extend([
            {"timestamp": t_str, "incident_id": "INC-1004", "service": "order_api", "metric_name": "p95_latency_ms", "value": round(46.0 + np.random.normal(0, 3.0), 2), "unit": "ms"},
            {"timestamp": t_str, "incident_id": "INC-1004", "service": "order_api", "metric_name": "error_rate_pct", "value": round(max(0.0, 0.05 + np.random.normal(0, 0.02)), 2), "unit": "%"},
        ])

        # Database telemetry DROPS completely after m >= 12 (missing telemetry!)
        if m < 12:
            metrics_rows.extend([
                {"timestamp": t_str, "incident_id": "INC-1004", "service": "database", "metric_name": "p95_latency_ms", "value": round(12.0 + np.random.normal(0, 1.0), 2), "unit": "ms"},
                {"timestamp": t_str, "incident_id": "INC-1004", "service": "database", "metric_name": "error_rate_pct", "value": round(max(0.0, 0.02 + np.random.normal(0, 0.01)), 2), "unit": "%"},
                {"timestamp": t_str, "incident_id": "INC-1004", "service": "database", "metric_name": "db_connections_pct", "value": round(30.0 + np.random.normal(0, 2.0), 2), "unit": "%"},
            ])

        # Logs: Conflicting signals
        if m in [15, 18, 22]:
            logs_rows.append({"timestamp": t_str, "incident_id": "INC-1004", "service": "frontend", "level": "WARN", "message": "Upstream socket reset by peer during connection handshake", "event_type": "SOCKET_RESET"})
            logs_rows.append({"timestamp": t_str, "incident_id": "INC-1004", "service": "order_api", "level": "INFO", "message": "All ingress transactions processed with HTTP 200 OK", "event_type": "INGRESS_OK"})
            logs_rows.append({"timestamp": t_str, "incident_id": "INC-1004", "service": "payment_service", "level": "WARN", "message": "Inconclusive network latency check to payment third-party provider", "event_type": "PAYMENT_PROBE"})

    return metrics_rows, logs_rows, events_rows


def main():
    all_metrics = []
    all_logs = []
    all_events = []

    for gen_fn in [generate_scenario_a, generate_scenario_b, generate_scenario_c, generate_scenario_d]:
        m_rows, l_rows, e_rows = gen_fn()
        all_metrics.extend(m_rows)
        all_logs.extend(l_rows)
        all_events.extend(e_rows)

    df_metrics = pd.DataFrame(all_metrics)
    df_logs = pd.DataFrame(all_logs)
    df_events = pd.DataFrame(all_events)

    df_metrics.to_csv(DATA_DIR / "metrics.csv", index=False)
    df_logs.to_csv(DATA_DIR / "logs.csv", index=False)
    df_events.to_csv(DATA_DIR / "events.csv", index=False)

    print(f"Generated {len(df_metrics)} metric records, {len(df_logs)} log records, {len(df_events)} events across 4 scenarios.")

if __name__ == "__main__":
    main()
