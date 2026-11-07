#!/usr/bin/env python3
"""
Generate three-layer dashboard design from Day22 article.

This script creates the dashboard structure described in Day22, validating:
1. Each layer has clear readers and questions
2. RED and USE are not confused
3. AI-specific signals connect back to user outcome
"""

from app.dashboard import (
    DashboardChart,
    DashboardLayer,
    ThreeLayerDashboard,
)


def create_user_layer() -> DashboardLayer:
    """
    User Layer: Business outcome metrics (Good Outcome Ratio, Latency SLO, Error Budget).

    Readers: Product, On-call, Customer Success
    """
    return DashboardLayer(
        name="User",
        purpose=(
            "Did the user get a good outcome? "
            "Tracks SLI (Service Level Indicators) and error budget burn."
        ),
        readers=["Product Managers", "On-call Engineer", "Customer Success"],
        charts=[
            DashboardChart(
                name="Good Outcome Ratio",
                metric_type="Golden Signals",
                question="What percentage of workflows returned a satisfactory outcome?",
                red_flag_action=(
                    "Good outcome ratio < SLO → page on-call; "
                    "check Service layer (which component failed?)"
                ),
                examples=[
                    "P(user satisfied) > 95%",
                    "P(answer is correct) > 90%",
                    "P(workflow completed) > 98%",
                ],
            ),
            DashboardChart(
                name="Latency SLO (P99)",
                metric_type="Golden Signals",
                question="Are workflows meeting the latency target?",
                red_flag_action=(
                    "P99 latency > SLO threshold → check Service layer (RED) "
                    "to find slow component (retrieval? LLM? tool?)"
                ),
                examples=[
                    "P99 < 5s for /ask API",
                    "TTFT (time to first token) < 1s",
                ],
            ),
            DashboardChart(
                name="Error Budget Burn Rate",
                metric_type="Golden Signals",
                question="How fast are we burning the error budget?",
                red_flag_action=(
                    "Burn rate > allowable → reduce feature velocity; "
                    "focus on reliability; review Resource layer for saturation"
                ),
                examples=[
                    "Monthly budget: 0.5% errors → ~21.6k allowed errors",
                    "Current burn: 0.3% per day → on pace to exceed budget by day 8",
                ],
            ),
        ],
    )


def create_service_layer() -> DashboardLayer:
    """
    Service Layer: RED method for /ask, retrieval, and tool components.

    Readers: Backend engineer, On-call, Platform team
    """
    return DashboardLayer(
        name="Service",
        purpose=(
            "Which component is slow or failing? "
            "Uses RED (Rate, Errors, Duration) to isolate workflow issues."
        ),
        readers=["Backend Engineer", "On-call Engineer", "Platform Team"],
        charts=[
            DashboardChart(
                name="RED: /ask API",
                metric_type="RED",
                question="Is the main entry-point healthy? (Rate, Errors, Duration)",
                red_flag_action=(
                    "Error rate > baseline → check downstream (LLM quota? Retrieval timeout?); "
                    "high duration → identify slowest stage (context building? LLM inference?)"
                ),
                examples=[
                    "rate(http_requests_total{endpoint='/ask'}[5m])",
                    "rate(http_requests_total{endpoint='/ask', status='5xx'}[5m])",
                    "histogram_quantile(0.99, request_duration_seconds{endpoint='/ask'})",
                ],
            ),
            DashboardChart(
                name="RED: Retrieval",
                metric_type="RED",
                question="Is retrieval (embedding + vector search) working?",
                red_flag_action=(
                    "Retrieval latency spike → check Resource layer (DB connection pool saturation?); "
                    "retrieval errors → check external service (embedding API quota?)"
                ),
                examples=[
                    "P95 retrieval_duration_ms",
                    "retrieval_failures_total per minute",
                ],
            ),
            DashboardChart(
                name="RED: Tool Failure & Execution",
                metric_type="RED",
                question="Are tool invocations reliable and fast?",
                red_flag_action=(
                    "Tool timeout rate up → Resource layer queue delay high; "
                    "tool error rate up → external service degradation"
                ),
                examples=[
                    "P99 tool_execution_duration_ms",
                    "tool_failures_total by tool name",
                ],
            ),
            DashboardChart(
                name="AI-Specific: Queue Delay",
                metric_type="RED",
                question="How long are jobs waiting in the queue before execution?",
                red_flag_action=(
                    "Queue delay > 10s → Resource layer is bottleneck; "
                    "scale workers or reduce incoming traffic"
                ),
                examples=[
                    "P95 queue_delay_ms",
                    "queue_length current value",
                ],
            ),
            DashboardChart(
                name="AI-Specific: TTFT (Time To First Token)",
                metric_type="RED",
                question="How fast does the LLM start streaming output?",
                red_flag_action=(
                    "TTFT > 2s → LLM service degradation or high load; "
                    "check Resource layer (GPU queue?) or external LLM provider status"
                ),
                examples=[
                    "P95 ttft_ms",
                    "histogram: ttft distribution",
                ],
            ),
            DashboardChart(
                name="AI-Specific: Evaluation Outcome",
                metric_type="RED",
                question="What fraction of answers passed evaluation (e.g., retrieval correctness)?",
                red_flag_action=(
                    "Evaluation pass rate down → retrieval quality degraded; "
                    "check if retrieval index is stale or if prompt was changed"
                ),
                examples=[
                    "P(retrieval_correct) by query type",
                    "P(answer_matches_ground_truth)",
                ],
            ),
        ],
    )


def create_resource_layer() -> DashboardLayer:
    """
    Resource Layer: USE method for workers, GPU queue, and connection pools.

    Readers: Infrastructure engineer, On-call, Platform SRE
    """
    return DashboardLayer(
        name="Resource",
        purpose=(
            "Can the infrastructure handle the load? "
            "Uses USE (Utilization, Saturation, Errors) to diagnose bottlenecks."
        ),
        readers=["Infrastructure Engineer", "On-call SRE", "Platform Team"],
        charts=[
            DashboardChart(
                name="USE: Worker (API/Service)",
                metric_type="USE",
                question=(
                    "Are worker processes at capacity? "
                    "(CPU/memory util, request queue depth, GC time)"
                ),
                red_flag_action=(
                    "CPU utilization > 80% and saturation (queue depth > 0) → scale horizontally; "
                    "memory util > 85% → check for leaks or reduce batch size"
                ),
                examples=[
                    "cpu_usage_percent",
                    "memory_usage_bytes / memory_limit_bytes",
                    "process_requests_queued",
                ],
            ),
            DashboardChart(
                name="USE: GPU Queue",
                metric_type="USE",
                question="Is GPU capacity saturated? (queue length, queue delay, GPU util)",
                red_flag_action=(
                    "Queue length > threshold or queue delay > 5s → add GPUs or reduce batch size; "
                    "GPU util < 50% and queue delay > 1s → queue delay is from orchestration overhead, not contention"
                ),
                examples=[
                    "gpu_queue_length",
                    "gpu_utilization_percent",
                    "P95 gpu_queue_wait_ms",
                ],
            ),
            DashboardChart(
                name="USE: Database Connection Pool",
                metric_type="USE",
                question=(
                    "Is the connection pool saturated? "
                    "(active connections, waiting connections, pool errors)"
                ),
                red_flag_action=(
                    "Waiting connections > 0 → pool is exhausted; increase pool size or reduce connection lifetime; "
                    "connection errors → database is down or unhealthy (check Resource layer DB metrics)"
                ),
                examples=[
                    "db_connections_active / db_connections_max",
                    "db_connections_waiting",
                    "db_connection_errors_total",
                ],
            ),
            DashboardChart(
                name="USE: Database",
                metric_type="USE",
                question=(
                    "Is the database at capacity? "
                    "(queries per second, slow query ratio, replication lag, disk utilization)"
                ),
                red_flag_action=(
                    "Query latency spike → slow query log; "
                    "replication lag > 1s → primary writes faster than replica can catch up (writes failing?); "
                    "disk util > 90% → provisioning issue"
                ),
                examples=[
                    "P99 query_duration_ms",
                    "slow_queries_total",
                    "replication_lag_seconds",
                ],
            ),
            DashboardChart(
                name="USE: Redis Cache",
                metric_type="USE",
                question=(
                    "Is the cache healthy? "
                    "(hit ratio, eviction rate, memory util, command latency)"
                ),
                red_flag_action=(
                    "Hit ratio < 80% → cache misconfiguration (TTL too short?) or working set too large; "
                    "eviction rate high → memory limit reached; "
                    "command latency spike → server busy or network issue"
                ),
                examples=[
                    "redis_hits / (redis_hits + redis_misses)",
                    "redis_evicted_keys_total",
                    "redis_used_memory / redis_max_memory",
                ],
            ),
        ],
    )


def main():
    """Generate and validate the three-layer dashboard."""

    dashboard = ThreeLayerDashboard(
        title="AI Workflow Observability: Three-Layer Dashboard",
        layers=[
            create_user_layer(),
            create_service_layer(),
            create_resource_layer(),
        ],
    )

    # Validation
    print("Validating dashboard design...")
    print()

    try:
        dashboard.validate_all_layers_present()
        print("✓ All three layers (User, Service, Resource) are present")
    except ValueError as e:
        print(f"✗ Validation error: {e}")
        return 1

    for layer in dashboard.layers:
        try:
            layer.validate_no_method_confusion()
            print(f"✓ {layer.name} layer uses correct method (RED ≠ USE)")
        except ValueError as e:
            print(f"✗ {layer.name} layer error: {e}")
            return 1

    try:
        dashboard.validate_ai_signals_to_outcome()
        print("✓ AI-specific signals (queue delay, TTFT, tool failure, evaluation) are present")
    except ValueError as e:
        print(f"✗ AI signals validation: {e}")
        return 1

    print()
    print("All validations passed!")
    print()

    # Generate summary
    print(dashboard.summary())

    # Checklist from Day22 article
    print()
    print("## 驗收 (Verification Checklist from Day22)")
    print()
    print("- [x] 每層有明確讀者與問題 (Each layer has clear readers and questions)")
    print("- [x] RED 與 USE 沒有套錯對象 (RED and USE are not confused)")
    print("- [x] AI 特有訊號能回到 user outcome (AI signals connect back to user outcome)")
    print("- [x] 草圖不等同已建置或驗證 dashboard (Sketch is not an implemented dashboard)")
    print()

    return 0


if __name__ == "__main__":
    exit(main())
