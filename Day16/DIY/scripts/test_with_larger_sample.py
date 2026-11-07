"""
Day16 DIY - Extended test with larger sample size (100 requests).

This demonstrates percentile behavior with a more statistically
meaningful sample size: 95 fast + 5 slow requests.
"""
import asyncio
import httpx
import json
from datetime import datetime
from typing import List


async def test_with_larger_sample(
    num_fast: int = 95,
    num_slow: int = 5,
    slow_delay_ms: int = 2000,
    base_url: str = "http://localhost:8000",
) -> None:
    """
    Make 100 requests: 95 fast, 5 slow at even intervals.

    Args:
        num_fast: Number of fast requests
        num_slow: Number of slow requests to inject
        slow_delay_ms: Delay (ms) per slow request
        base_url: Base URL of the FastAPI server
    """
    latencies: List[dict] = []
    total_requests = num_fast + num_slow
    slow_interval = num_fast // num_slow  # Distribute slow requests evenly

    print("="*70)
    print("Day16 DIY - Tail Latency Analysis (100 requests)")
    print("="*70)
    print(f"Starting at: {datetime.now().isoformat()}")
    print(f"Plan: {num_fast} fast + {num_slow} slow ({slow_delay_ms}ms each)")
    print(f"Slow request interval: every {slow_interval} requests")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        print("Sending requests...")
        slow_count = 0

        for i in range(total_requests):
            # Determine if this should be a slow request
            is_slow = (slow_count < num_slow) and ((i + 1) % slow_interval == 0)

            try:
                start = asyncio.get_event_loop().time()

                params = {"question": f"policy-{i}"}
                if is_slow:
                    params["test_delay_ms"] = slow_delay_ms
                    slow_count += 1

                response = await client.post(
                    f"{base_url}/ask",
                    params=params,
                )
                elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

                if response.status_code == 200:
                    latencies.append({
                        "request_num": i + 1,
                        "is_slow": is_slow,
                        "latency_ms": elapsed_ms,
                    })

                    # Print slow requests and progress
                    if is_slow:
                        print(f"  Request {i+1:3d}: {elapsed_ms:7.2f} ms [SLOW #{slow_count}]")
                    elif (i + 1) % 20 == 0:
                        print(f"  Request {i+1:3d}: {elapsed_ms:7.2f} ms ✓")
                else:
                    print(f"  Request {i+1:3d}: Failed with status {response.status_code}")
            except Exception as e:
                print(f"  Request {i+1:3d}: Error - {e}")

    if not latencies:
        print("❌ No successful requests recorded.")
        return

    print()
    print("="*70)
    print("LATENCY ANALYSIS")
    print("="*70)

    # Extract latency values
    latency_values = [r["latency_ms"] for r in latencies]

    # Calculate statistics
    mean_latency = sum(latency_values) / len(latency_values)
    min_latency = min(latency_values)
    max_latency = max(latency_values)

    def percentile(data: List[float], p: float) -> float:
        """Calculate percentile using linear interpolation."""
        if not data:
            return 0.0
        sorted_data = sorted(data)
        index = (p / 100) * (len(sorted_data) - 1)
        lower_idx = int(index)
        upper_idx = lower_idx + 1

        if upper_idx >= len(sorted_data):
            return float(sorted_data[-1])

        weight = index - lower_idx
        return sorted_data[lower_idx] * (1 - weight) + sorted_data[upper_idx] * weight

    p50 = percentile(latency_values, 50)
    p95 = percentile(latency_values, 95)
    p99 = percentile(latency_values, 99)

    # Count slow vs fast
    slow_count_actual = sum(1 for r in latencies if r["is_slow"])
    fast_count = len(latencies) - slow_count_actual
    slow_percentage = (slow_count_actual / len(latencies)) * 100 if latencies else 0

    print()
    print("REQUEST SUMMARY")
    print("-"*70)
    print(f"Total requests:        {len(latencies)}")
    print(f"Fast requests:         {fast_count} ({100-slow_percentage:.1f}%)")
    print(f"Slow requests:         {slow_count_actual} ({slow_percentage:.1f}%)")
    print()

    print("LATENCY STATISTICS (milliseconds)")
    print("-"*70)
    print(f"Mean:                  {mean_latency:10.2f} ms")
    print(f"P50 (median):          {p50:10.2f} ms  (50% of requests ≤ this)")
    print(f"P95:                   {p95:10.2f} ms  (95% of requests ≤ this)")
    print(f"P99:                   {p99:10.2f} ms  (99% of requests ≤ this)")
    print(f"Min:                   {min_latency:10.2f} ms")
    print(f"Max:                   {max_latency:10.2f} ms")
    print()

    print("KEY INSIGHTS")
    print("-"*70)
    print(f"✓ Mean ({mean_latency:.0f}ms) vs P95 ({p95:.0f}ms) vs P99 ({p99:.0f}ms)")
    print(f"✓ P95 tells us: 95% of requests complete in ≤ {p95:.0f}ms")
    print(f"✓ P99 tells us: 99% of requests complete in ≤ {p99:.0f}ms")

    fast_latency = min(v for r in latencies if not r["is_slow"] for v in [r["latency_ms"]])
    slow_latency = max(v for r in latencies if r["is_slow"] for v in [r["latency_ms"]])
    print(f"✓ {100-slow_percentage:.0f}% experience ~{fast_latency:.0f}ms")
    print(f"✓ {slow_percentage:.0f}% experience ~{slow_latency:.0f}ms")
    print(f"✓ Mean {mean_latency:.0f}ms hides the tail reality")
    print()

    print("PERCENTILE INTERPRETATION")
    print("-"*70)
    print("Question: What latency should we target in our SLO?")
    print(f"• If we use Mean ({mean_latency:.0f}ms): 5% of users feel it's much slower ❌")
    print(f"• If we use P95 ({p95:.0f}ms): Only ~5% worse than target ✓")
    print(f"• If we use P99 ({p99:.0f}ms): Covers even the slowest users ✓✓")
    print()

    print("VERIFICATION CHECKLIST")
    print("-"*70)
    checks = [
        ("Data includes ~5% slow requests", slow_percentage >= 4.0 and slow_percentage <= 6.0),
        ("Mean is significantly lower than tail", mean_latency < p95),
        ("P95 clearly shows increased latency", p95 > mean_latency),
        ("P99 reaches into the slow region", p99 > p95 * 2),
        ("Can distinguish fast vs slow requests", fast_count > 0 and slow_count_actual > 0),
    ]

    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")

    print()
    print("="*70)
    print(f"Test completed at: {datetime.now().isoformat()}")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_with_larger_sample(num_fast=95, num_slow=5, slow_delay_ms=2000))
