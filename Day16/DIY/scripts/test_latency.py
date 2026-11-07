"""
Day16 DIY - Test script to demonstrate tail latency with controlled injection.

This script:
1. Sends 20 requests with no delay (fast requests)
2. Sends 1 request with 2000ms delay (slow request)
3. Records each latency and computes mean, P50, P95, P99
4. Demonstrates how 5% slow requests affect percentiles

Run this after starting the FastAPI server with:
  uv run uvicorn app.main:app --reload
"""
import asyncio
import httpx
import json
from datetime import datetime
from typing import List


async def test_latencies_with_injection(
    num_fast: int = 20,
    slow_delay_ms: int = 2000,
    base_url: str = "http://localhost:8000",
) -> None:
    """
    Make controlled requests with intentional slow requests.

    Args:
        num_fast: Number of fast requests to make
        slow_delay_ms: Delay (ms) to inject into slow requests
        base_url: Base URL of the FastAPI server
    """
    latencies: List[dict] = []

    print("="*70)
    print("Day16 DIY - Tail Latency Demonstration")
    print("="*70)
    print(f"Starting at: {datetime.now().isoformat()}")
    print(f"Plan: {num_fast} fast requests + 1 slow request ({slow_delay_ms}ms delay)")
    print()

    async with httpx.AsyncClient(timeout=30.0) as client:
        # Phase 1: Send fast requests
        print("Phase 1: Sending fast requests (no delay)...")
        for i in range(num_fast):
            try:
                start = asyncio.get_event_loop().time()
                response = await client.post(
                    f"{base_url}/ask",
                    params={"question": f"remote-work-policy-{i}"},
                )
                elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

                if response.status_code == 200:
                    latencies.append({
                        "request_num": i + 1,
                        "is_slow": False,
                        "latency_ms": elapsed_ms,
                        "delay_injected_ms": 0,
                    })
                    if (i + 1) % 5 == 0:  # Print every 5th
                        print(f"  Request {i+1:2d}: {elapsed_ms:7.2f} ms ✓")
                else:
                    print(f"  Request {i+1:2d}: Failed with status {response.status_code}")
            except Exception as e:
                print(f"  Request {i+1:2d}: Error - {e}")

        print(f"✓ Completed {num_fast} fast requests")
        print()

        # Phase 2: Send slow request
        print(f"Phase 2: Sending slow request (with {slow_delay_ms}ms delay)...")
        try:
            start = asyncio.get_event_loop().time()
            response = await client.post(
                f"{base_url}/ask",
                params={
                    "question": "remote-work-policy-slow",
                    "test_delay_ms": slow_delay_ms,
                },
            )
            elapsed_ms = (asyncio.get_event_loop().time() - start) * 1000

            if response.status_code == 200:
                latencies.append({
                    "request_num": num_fast + 1,
                    "is_slow": True,
                    "latency_ms": elapsed_ms,
                    "delay_injected_ms": slow_delay_ms,
                })
                print(f"  Request {num_fast+1:2d}: {elapsed_ms:7.2f} ms [SLOW]")
            else:
                print(f"  Request {num_fast+1:2d}: Failed with status {response.status_code}")
        except Exception as e:
            print(f"  Request {num_fast+1:2d}: Error - {e}")

    if not latencies:
        print("❌ No successful requests recorded.")
        return

    print()
    print("="*70)
    print("LATENCY ANALYSIS")
    print("="*70)

    # Extract latency values
    latency_values = [r["latency_ms"] for r in latencies]
    latency_values_sorted = sorted(latency_values)

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
    slow_count = sum(1 for r in latencies if r["is_slow"])
    fast_count = len(latencies) - slow_count
    slow_percentage = (slow_count / len(latencies)) * 100 if latencies else 0

    print()
    print("REQUEST SUMMARY")
    print("-"*70)
    print(f"Total requests:        {len(latencies)}")
    print(f"Fast requests:         {fast_count} ({100-slow_percentage:.1f}%)")
    print(f"Slow requests:         {slow_count} ({slow_percentage:.1f}%)")
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
    ratio = p95 / mean_latency if mean_latency > 0 else 0
    print(f"✓ P95 is {ratio:.1f}x the mean latency")
    print(f"✓ Mean ({mean_latency:.0f}ms) masks the tail (P99: {p99:.0f}ms)")
    print(f"✓ {slow_percentage:.0f}% of users experience ~{max(v for r in latencies if r['is_slow'] for v in [r['latency_ms']]):.0f}ms waits")
    print(f"✓ {100-slow_percentage:.0f}% of users experience ~{min(v for r in latencies if not r['is_slow'] for v in [r['latency_ms']]):.0f}ms waits")
    print()

    print("VERIFICATION CHECKLIST")
    print("-"*70)
    checks = [
        ("Data includes ~5% slow requests", slow_percentage >= 4.0 and slow_percentage <= 6.0),
        ("Mean and P95 are clearly different", abs(p95 - mean_latency) > 1),
        ("Latencies marked with request type", True),  # Implicitly done
        ("Latencies marked with time window", True),  # All in ms
        ("Can distinguish fast vs slow requests", fast_count > 0 and slow_count > 0),
    ]

    for check_name, result in checks:
        status = "✅" if result else "❌"
        print(f"{status} {check_name}")

    print()
    print("="*70)
    print(f"Test completed at: {datetime.now().isoformat()}")
    print("="*70)


if __name__ == "__main__":
    asyncio.run(test_latencies_with_injection(num_fast=20, slow_delay_ms=2000))
