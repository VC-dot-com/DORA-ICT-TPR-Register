"""
Performance benchmark for the concentration-risk scoring engine.

Measures the quantitative metrics reported in the Unit 6 evaluation:
  - Latency: time to score a whole portfolio, at increasing sizes
  - Throughput: providers scored per second
  - Memory footprint: peak memory used while scoring

Synthetic data only. Run:  python benchmark.py
"""
import time
import random
import tracemalloc
from app.scoring import score_portfolio

WEIGHTS = {"criticality": 0.50, "concentration": 0.30, "substitutability": 0.20}
SUPPORTS = ["Critical", "Important", "None"]


def make_portfolio(n, seed=42):
    """Build a synthetic portfolio of n providers."""
    random.seed(seed)
    return [
        {
            "name": f"Provider{i:04d}",
            "supports": random.choice(SUPPORTS),
            "annual_value": random.randint(10_000, 1_000_000),
            "substitutability": random.randint(1, 5),
        }
        for i in range(n)
    ]


def bench_latency(n, repeats=50):
    """Average and best time to score a portfolio of n providers."""
    portfolio = make_portfolio(n)
    score_portfolio(portfolio, WEIGHTS)  # warm-up
    total = 0.0
    best = float("inf")
    for _ in range(repeats):
        start = time.perf_counter()
        score_portfolio(portfolio, WEIGHTS)
        elapsed = time.perf_counter() - start
        total += elapsed
        best = min(best, elapsed)
    return total / repeats, best


def bench_memory(n):
    """Peak memory used while scoring a portfolio of n providers."""
    portfolio = make_portfolio(n)
    tracemalloc.start()
    score_portfolio(portfolio, WEIGHTS)
    _, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return peak


def main():
    print("=" * 68)
    print(" Concentration-risk scoring engine: performance benchmark")
    print(" Synthetic data. Latency in milliseconds, memory in kilobytes.")
    print("=" * 68)
    print(f"{'Providers':>10} | {'Avg latency':>12} | {'Throughput':>16} | {'Peak memory':>12}")
    print(f"{'':>10} | {'(ms)':>12} | {'(providers/s)':>16} | {'(KB)':>12}")
    print("-" * 68)
    for n in (6, 50, 100, 500, 1000):
        avg, _ = bench_latency(n)
        peak_kb = bench_memory(n) / 1024
        throughput = n / avg if avg > 0 else 0
        print(f"{n:>10} | {avg*1000:>12.3f} | {throughput:>16,.0f} | {peak_kb:>12.1f}")
    print("-" * 68)
    avg500, _ = bench_latency(500)
    verdict = "PASS" if avg500 < 2.0 else "FAIL"
    print(f" NFR check: 500 providers must score within 2000 ms.")
    print(f" Measured: {avg500*1000:.1f} ms  ->  {verdict}")
    print("=" * 68)


if __name__ == "__main__":
    main()
