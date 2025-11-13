#!/usr/bin/env python3
"""
Performance testing script for Agora API.
Tests response times and concurrent load handling.
"""
import asyncio
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List, Tuple

import requests
from rich.console import Console
from rich.table import Table

console = Console()

API_URL = "http://localhost:8000"

# Test queries
TEST_QUERIES = [
    "What is class struggle?",
    "What is democracy?",
    "How should I deal with failure?",
    "What is freedom?",
    "What makes a good life?",
]


def send_query(query: str) -> Tuple[int, float]:
    """Send a single query and measure response time."""
    start = time.time()
    try:
        response = requests.post(
            f"{API_URL}/api/query",
            json={
                "query": query,
                "max_authors": 3,
                "relevance_threshold": 0.7
            },
            timeout=30
        )
        duration = time.time() - start
        return response.status_code, duration
    except Exception as e:
        duration = time.time() - start
        console.print(f"[red]Error: {e}[/red]")
        return 0, duration


def load_test(
    concurrent_requests: int = 10,
    queries: List[str] = None
) -> dict:
    """
    Run load test with concurrent requests.
    
    Args:
        concurrent_requests: Number of concurrent requests
        queries: List of queries to test (cycles through them)
    
    Returns:
        Test results dictionary
    """
    if queries is None:
        queries = TEST_QUERIES
    
    console.print(f"
[bold]Running load test with {concurrent_requests} concurrent requests...[/bold]")
    
    # Prepare query list (cycle queries if needed)
    test_queries = []
    for i in range(concurrent_requests):
        test_queries.append(queries[i % len(queries)])
    
    # Execute concurrent requests
    start_time = time.time()
    
    with ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = [
            executor.submit(send_query, query)
            for query in test_queries
        ]
        results = [f.result() for f in futures]
    
    total_time = time.time() - start_time
    
    # Analyze results
    successful = sum(1 for status, _ in results if status == 200)
    failed = concurrent_requests - successful
    durations = [duration for _, duration in results if duration > 0]
    
    if durations:
        avg_time = statistics.mean(durations)
        median_time = statistics.median(durations)
        p95_time = sorted(durations)[int(len(durations) * 0.95)] if len(durations) > 1 else durations[0]
        p99_time = sorted(durations)[int(len(durations) * 0.99)] if len(durations) > 1 else durations[0]
        min_time = min(durations)
        max_time = max(durations)
    else:
        avg_time = median_time = p95_time = p99_time = min_time = max_time = 0
    
    return {
        "concurrent_requests": concurrent_requests,
        "successful": successful,
        "failed": failed,
        "total_time": total_time,
        "avg_time": avg_time,
        "median_time": median_time,
        "p95_time": p95_time,
        "p99_time": p99_time,
        "min_time": min_time,
        "max_time": max_time,
        "requests_per_second": concurrent_requests / total_time if total_time > 0 else 0
    }


def display_results(results: dict):
    """Display test results in a table."""
    table = Table(title="Performance Test Results")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right", style="green")
    
    table.add_row("Concurrent Requests", str(results["concurrent_requests"]))
    table.add_row("Successful", str(results["successful"]))
    table.add_row("Failed", str(results["failed"]))
    table.add_row("Total Time", f"{results['total_time']:.2f}s")
    table.add_row("Requests/sec", f"{results['requests_per_second']:.2f}")
    table.add_row("", "")
    table.add_row("Avg Response Time", f"{results['avg_time']:.2f}s")
    table.add_row("Median Response Time", f"{results['median_time']:.2f}s")
    table.add_row("P95 Response Time", f"{results['p95_time']:.2f}s")
    table.add_row("P99 Response Time", f"{results['p99_time']:.2f}s")
    table.add_row("Min Response Time", f"{results['min_time']:.2f}s")
    table.add_row("Max Response Time", f"{results['max_time']:.2f}s")
    
    console.print(table)


def main():
    """Run performance tests."""
    console.print("[bold blue]Agora Performance Testing[/bold blue]")
    console.print("=" * 60)
    
    # Check if API is available
    try:
        response = requests.get(f"{API_URL}/api/health", timeout=5)
        if response.status_code != 200:
            console.print("[red]API health check failed![/red]")
            return 1
        console.print("[green]✓ API is healthy[/green]")
    except Exception as e:
        console.print(f"[red]Cannot connect to API: {e}[/red]")
        console.print(f"Make sure the API is running at {API_URL}")
        return 1
    
    # Run tests with increasing concurrency
    test_levels = [1, 5, 10, 20, 50]
    
    all_results = []
    for level in test_levels:
        results = load_test(level)
        all_results.append(results)
        display_results(results)
        
        # Brief pause between tests
        time.sleep(2)
    
    # Summary
    console.print("
[bold]Summary:[/bold]")
    
    criteria = [
        ("Handles 10 concurrent requests", all_results[2]["successful"] >= 9),
        ("Average response time < 5s", all_results[0]["avg_time"] < 5),
        ("P95 response time < 10s", all_results[0]["p95_time"] < 10),
        ("No failures under light load", all_results[0]["failed"] == 0),
    ]
    
    for criterion, passed in criteria:
        status = "[green]✓[/green]" if passed else "[red]✗[/red]"
        console.print(f"  {status} {criterion}")
    
    console.print()
    
    return 0 if all(passed for _, passed in criteria) else 1


if __name__ == "__main__":
    import sys
    sys.exit(main())
