"""
Demonstrate the three query problems using the three pillar signals independently.

① Metrics: "timeout 有沒有變多?" (Did timeout incidents increase?)
② Logs: "哪個 dependency?" (Which dependency is timing out?)
③ Traces: "這筆 request 花在哪?" (Where did this request spend time?)
"""

from prometheus_client import REGISTRY
from app.metrics import timeout_incidents, answer_requests


class MetricsQueries:
    """Query 1: Use only METRICS to answer 'Did timeout increase?'"""

    @staticmethod
    def get_timeout_rate():
        """
        Answer: timeout 有沒有變多?

        Solution: Look at the ratio of 'upstream_timeout' outcome
        vs total requests in the metrics.
        """
        total_timeout = 0
        total_requests = 0

        for metric_family in REGISTRY.collect():
            if metric_family.name == "dependency_timeout_incidents":
                for sample in metric_family.samples:
                    if not sample.name.endswith("_created"):  # Skip _created
                        total_timeout += int(sample.value)
            elif metric_family.name == "answer_requests":
                for sample in metric_family.samples:
                    if not sample.name.endswith("_created"):  # Skip _created
                        total_requests += int(sample.value)

        if total_requests == 0:
            return 0.0

        return total_timeout / total_requests

    @staticmethod
    def report():
        """Print metrics query result."""
        rate = MetricsQueries.get_timeout_rate()
        print("\n=== Query ① METRICS: 'Did timeout incidents increase?' ===")
        print(f"Timeout rate: {rate:.1%}")
        print("✓ Use METRICS when you need quick alerting on trends (every second)")
        print("✓ Low-cardinality labels (dependency) allow efficient aggregation")
        print("✗ Metrics alone don't tell you which request or span caused it")


class LogsQueries:
    """Query 2: Use only LOGS to answer 'Which dependency is timing out?'"""

    # In real scenario, this would query Loki with LogQL:
    # {service="api"} | json | event="dependency_timeout"
    # | stats count() by dependency

    @staticmethod
    def report():
        """Print logs query result (conceptual)."""
        print("\n=== Query ② LOGS: 'Which dependency timed out?' ===")
        print("LogQL query:")
        print('  {service="api"} | json')
        print('  | event="dependency_timeout"')
        print('  | stats count() by dependency')
        print("")
        print("Log fields available for filtering:")
        print("  - request_id: trace correlation")
        print("  - event: dependency_timeout")
        print("  - error_class: TimeoutError")
        print("  - dependency: retriever | model | tool")
        print("  - retry_count: how many retries attempted")
        print("")
        print("✓ Use LOGS when you need to correlate cross-machine failures")
        print("✓ Structured JSON fields (event, dependency) enable fast filtering")
        print("✗ Logs alone don't show request latency breakdown (need traces)")


class TracesQueries:
    """Query 3: Use only TRACES to answer 'Where did this request spend time?'"""

    @staticmethod
    def report():
        """Print traces query result (conceptual)."""
        print("\n=== Query ③ TRACES: 'Where did this request spend time?' ===")
        print("Tempo query by request_id:")
        print('  search(request_id="demo-42")')
        print("")
        print("Expected trace structure:")
        print("  ask (root span)")
        print("    └─ dependency_retrieve (child span)")
        print("         duration: 100ms")
        print("")
        print("Trace attributes for correlation:")
        print("  - request_id: matches logs, enables end-to-end tracing")
        print("  - dependency: which subsystem the span measures")
        print("")
        print("✓ Use TRACES when debugging a single slow request")
        print("✓ Span hierarchy shows critical path (which step took longest)")
        print("✗ Traces alone can't show if a 100ms latency is normal or anomalous")


def print_query_summary():
    """Print summary of the three-pillar query pattern."""
    print("\n" + "=" * 70)
    print("THREE PILLARS OF OBSERVABILITY: SAME REQUEST, THREE VIEWS")
    print("=" * 70)

    MetricsQueries.report()
    LogsQueries.report()
    TracesQueries.report()

    print("\n=== KEY INSIGHT ===")
    print("None of the three can replace the others:")
    print("")
    print("1. METRICS alone: You see 'service is down' but not 'which customer'")
    print("   (Shakespeare Search: metrics said 'HTTP 500 rate=100%' but didn't say why)")
    print("")
    print("2. LOGS alone: You search 'TimeoutError' in terabytes of logs, slow debugging")
    print("   (Meta: 100GB/sec logs, need structured fields to query quickly)")
    print("")
    print("3. TRACES alone: You see one request's breakdown, but don't know if it's widespread")
    print("   (Is this slow request a one-off or affects all users?)")
    print("")
    print("All three together: metrics alert → logs narrow scope → traces diagnose root cause")
    print("=" * 70 + "\n")
