# Performance Tests (k6)

Load, stress, and spike tests for the Platform Pipeline Demo API.

## Scripts

| Script | Purpose | Duration |
|--------|---------|----------|
| `load-test.js` | Standard load test (10-25 VUs) | ~3.5 min |
| `stress-test.js` | Breakpoint test (up to 100 VUs) | ~3.5 min |
| `spike-test.js` | Sudden traffic spike (up to 80 VUs) | ~1.5 min |

## Running Locally

```bash
# With Spring Boot running on localhost:8080
k6 run perf-tests/scripts/load-test.js
k6 run perf-tests/scripts/stress-test.js
k6 run perf-tests/scripts/spike-test.js
```

## Thresholds

- **Load test**: p95 < 500ms, error rate < 5%
- **Stress test**: p95 < 1500ms, error rate < 15%
- **Spike test**: p95 < 2000ms, error rate < 10%

## Results

JSON summaries are written to `perf-tests/results/` and excluded from git.
