# Governance Dashboard Specification

**Purpose:** Define the governance dashboard for visualizing Rocky's cognitive contract compliance.

---

## Overview

The governance dashboard converts governance from engineering-only into system-level insight. It aggregates violation data from test-time and runtime sources to provide:

- Compliance metrics
- Violation trends
- Test vs runtime comparison
- Tool health monitoring
- Quick wins identification

---

## Dashboard Views

### 1. Overview Dashboard

**Purpose:** High-level compliance status at a glance

**Widgets:**
1. **Compliance Gauge**
   - Large circular gauge showing compliance percentage (0-100%)
   - Color: Green (95%+), Yellow (80-95%), Red (<80%)
   - Status badge: Compliant / Warning / Non-Compliant

2. **Violation Summary Cards**
   - Total violations (last 24h)
   - Critical violations
   - High violations
   - Days since last violation

3. **Trend Chart**
   - Violation count over time (last 7 days)
   - Dual-axis: Count + Compliance %

4. **Top Violations Table**
   - Top 5 violations by impact
   - Columns: Type, Severity, Frequency, Last Seen

**Query:**
```ts
{
  timeRange: '7d',
  groupBy: 'severity',
}
```

---

### 2. Violations Dashboard

**Purpose:** Deep dive into violation patterns

**Widgets:**
1. **Violation Breakdown**
   - Pie chart: By category
   - Bar chart: By severity
   - Stacked area: By source (test vs runtime)

2. **Violation Timeline**
   - Timeline view of all violations
   - Filterable by severity, category, source
   - Click to view details

3. **Violation Details Table**
   - Full violation list
   - Sortable columns
   - Filterable by all dimensions
   - Export to CSV

**Query:**
```ts
{
  timeRange: '30d',
  groupBy: 'category',
}
```

---

### 3. Test vs Runtime Comparison

**Purpose:** Validate contract accuracy

**Widgets:**
1. **Consistency Score**
   - Large metric: Consistency score (0-100%)
   - Breakdown: Overlap, test-only, runtime-only

2. **Comparison Charts**
   - Side-by-side: Test violations vs Runtime violations
   - By category
   - By severity

3. **Gap Analysis**
   - Test-only violations (not seen at runtime)
   - Runtime-only violations (not caught by tests)
   - Recommendations for contract updates

**Query:**
```ts
{
  timeRange: '7d',
  source: ['test', 'runtime'],
}
```

---

### 4. Tool Health Dashboard

**Purpose:** Monitor individual tool compliance

**Widgets:**
1. **Tool Health Table**
   - All tools with health metrics
   - Columns: Tool, Invocations, Violations, Violation Rate, Status
   - Sortable, filterable

2. **Tool Trend Charts**
   - Per-tool violation trends
   - Select tool to view details

3. **Most Problematic Tools**
   - Top 10 tools by violation rate
   - Quick action: View details, Generate fix ticket

**Query:**
```ts
{
  timeRange: '7d',
  groupBy: 'tool',
}
```

---

### 5. Quick Wins Dashboard

**Purpose:** Identify high-impact, low-effort fixes

**Widgets:**
1. **Quick Wins List**
   - Violations sorted by impact/effort ratio
   - Columns: Violation, Impact, Effort, Affected Count, Fix Action

2. **Effort vs Impact Matrix**
   - 2x2 matrix: Low/High Effort × Low/High Impact
   - Violations plotted by position
   - Focus on High Impact / Low Effort quadrant

**Query:**
```ts
{
  timeRange: '30d',
  severity: ['high', 'critical'],
}
```

---

## Data Sources

### Test-Time Violations

**Sources:**
- `tests/artifacts/cognitive-contract/cognitive-contract-report-*.json`
- CI/CD reports
- Pre-commit hook outputs

**Loading:**
```ts
// Load from test artifacts
const reports = await loadTestReports(timeRange);
const violations = reports.flatMap(r => r.violations);
```

### Runtime Violations

**Sources:**
- Runtime violation events (from `RuntimeEnforcementService`)
- Analytics/telemetry
- Database (if persisted)

**Loading:**
```ts
// Load from runtime events
const violations = await loadRuntimeViolations(timeRange);
```

---

## Query API

### Generate Dashboard

```ts
const dashboard = await governanceDashboardService.generateDashboard({
  timeRange: '7d',
  severity: ['high', 'critical'],
  category: ['TOOL_AUTHORITY'],
  source: ['test', 'runtime'],
});
```

### Get Compliance Metrics

```ts
const compliance = dashboard.compliance;
// {
//   percentage: 95.2,
//   status: 'compliant',
//   trend: 'improving',
//   violationRate: 0.5,
//   ...
// }
```

### Get Violation Trends

```ts
const trends = dashboard.trends.violationCount;
// [
//   { timestamp: '...', date: '2025-12-12', count: 5, ... },
//   ...
// ]
```

### Compare Test vs Runtime

```ts
const comparison = dashboard.testRuntimeComparison;
// {
//   consistencyScore: 85,
//   overlap: { count: 12, percentage: 60, ... },
//   testOnly: { count: 3, violations: [...] },
//   runtimeOnly: { count: 5, violations: [...] },
// }
```

---

## Visualization Recommendations

### Charts

1. **Compliance Gauge**
   - Use `recharts` or `victory` for circular gauge
   - Color gradient: Red → Yellow → Green

2. **Trend Charts**
   - Use `recharts` LineChart or AreaChart
   - Dual-axis for count + percentage

3. **Breakdown Charts**
   - Use `recharts` PieChart or BarChart
   - Interactive tooltips

4. **Timeline**
   - Use custom timeline component or `react-calendar-timeline`
   - Color-code by severity

### Tables

- Use `@tanstack/react-table` for sortable/filterable tables
- Export to CSV functionality
- Pagination for large datasets

---

## Performance Considerations

### Data Aggregation

- Pre-aggregate violations by time bucket
- Cache dashboard data (5-minute TTL)
- Lazy-load detailed views

### Query Optimization

- Limit time range for initial load
- Load trends incrementally
- Virtualize long lists

---

## Integration Points

### React Component

```tsx
import { governanceDashboardService } from '@/services/rocky/GovernanceDashboardService';

function GovernanceDashboard() {
  const [dashboard, setDashboard] = useState<GovernanceDashboardData | null>(null);
  const [query, setQuery] = useState<DashboardQuery>({ timeRange: '7d' });

  useEffect(() => {
    governanceDashboardService.generateDashboard(query).then(setDashboard);
  }, [query]);

  // Render dashboard widgets
}
```

### API Endpoint (Future)

```ts
// GET /api/governance/dashboard?timeRange=7d&severity=high
app.get('/api/governance/dashboard', async (req, res) => {
  const query = req.query as DashboardQuery;
  const dashboard = await governanceDashboardService.generateDashboard(query);
  res.json(dashboard);
});
```

---

## Success Metrics

### Dashboard Adoption

- Daily active users
- Time spent viewing dashboard
- Widget interaction rate

### Actionability

- Violations fixed after dashboard review
- Quick wins completed
- Contract updates based on insights

---

## Next Steps

1. ✅ Dashboard schema defined
2. ✅ Dashboard service implemented
3. ⏳ Build React dashboard component
4. ⏳ Integrate with violation data sources
5. ⏳ Add real-time updates (WebSocket/SSE)
6. ⏳ Add export functionality

---

**End of Specification**





