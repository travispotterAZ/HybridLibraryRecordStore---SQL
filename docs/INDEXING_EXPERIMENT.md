# Indexing Impact Experiment Guide

## Overview
This experiment measures the performance impact of database indexes on catalog search queries by comparing execution times and query plans before and after adding strategic indexes.

## Methodology

**Hypothesis**: Indexes on artist names and foreign key columns will reduce query execution time by avoiding full table scans and enabling more efficient join operations.

**Approach**:
1. Create two copies of the database (seeded with data)
2. Keep one copy without indexes (baseline)
3. Add strategic indexes to the second copy
4. Execute identical catalog search queries on both databases
5. Measure execution time for each query (100 iterations)
6. Examine EXPLAIN QUERY PLAN output to observe scan strategy changes
7. Generate comparative report with findings

## Files

### Experiment Script
- **`src/indexing_experiment.py`** - Main experiment conductor
  - Sets up parallel databases (with/without indexes)
  - Executes queries and measures performance
  - Analyzes query execution plans
  - Generates detailed report

### SQL Resources  
- **`sql/create_indexes.sql`** - SQL commands for all indexes created
  - Documents strategic indexes applied
  - Includes rationale for each index

## Running the Experiment

### Prerequisites
- `data/main.db` must exist and be seeded with test data
- Python 3.7+ with `sqlite3` module (included in standard library)

### Quick Start

```bash
cd src
python3 indexing_experiment.py
```

### Output
The script will produce:
1. **Console output** - Real-time progress and results
2. **indexing_experiment_report.txt** - Detailed comparative report
3. **Database files**:
   - `data/main_no_idx.db` - Baseline without indexes
   - `data/main_with_idx.db` - With all strategic indexes

## Experiment Design

### Test Queries
The experiment runs 5 representative catalog search queries:

1. **Search by artist name** (LIKE pattern)
   - Tests: Artist name index effectiveness
   - Typical workload: User searching for specific artist

2. **List all records with artists** (Large JOIN + ORDER BY)
   - Tests: Foreign key index efficiency
   - Typical workload: Browsing full catalog

3. **Find active records by artist** (JOIN + filtering + sorting)
   - Tests: Multi-column effectiveness
   - Typical workload: Filtered search results

4. **Count records per artist** (Aggregation + GROUP BY)
   - Tests: Index utilization in aggregates
   - Typical workload: Analytics queries

5. **Find records by genre and artist** (Multiple filter conditions)
   - Tests: Complex WHERE clause optimization
   - Typical workload: Advanced search with multiple criteria

### Strategic Indexes Created

| Index | Table | Column(s) | Purpose |
|-------|-------|-----------|---------|
| `idx_artists_name` | Artists | artist_name | Enable fast name lookups |
| `idx_artists_genre` | Artists | genre | Filter by artist genre |
| `idx_records_artist_id` | Records | artist_id | Optimize JOIN to Artists |
| `idx_records_is_active` | Records | is_active | Filter active records |
| `idx_records_genre` | Records | genre | Filter by record genre |
| `idx_copies_record_id` | Copies | record_id | Inventory lookups |
| `idx_loans_copy_id` | Loans | copy_id | Availability checks |
| `idx_records_artist_is_active` | Records | artist_id, is_active | Compound: JOIN + filter |
| `idx_copies_status` | Copies | record_id, status | Compound: Inventory + status |

## Understanding Results

### Performance Metrics
- **Execution Time (ms)**: Total time for 100 query iterations
- **Improvement %**: `(no_index_time - indexed_time) / no_index_time × 100`
- **Speedup Factor**: `no_index_time / indexed_time`

### Execution Plan Analysis
The `EXPLAIN QUERY PLAN` output shows:

#### Without Indexes
- **TABLE SCAN**: Reads every row in a table
- **SCAN**: Full scan through index (less selective)

#### With Indexes
- **INDEX SEARCH**: Uses index to locate specific rows (fast)
- **INDEX SCAN**: Scans through index (still filtered)
- **SEARCH**: Efficient point lookup

### Key Indicators

**Good index impact signs**:
- Change from TABLE SCAN to INDEX SEARCH
- Reduced row examination count
- Elimination of separate sort operations
- Significant time improvements (>20% typical, >50% for large tables)

**Minimal index impact**:
- Small result sets (query already fast)
- Index can't improve query predicates
- Sort order already matches natural table order

## Example Interpretation

```
Query: Search by artist name
  Without indexes: 156.42ms (TABLE SCAN)
  With indexes:     18.75ms (INDEX SEARCH)
  → Improvement: 88.0% (8.33x faster)
```

**Analysis**: 
- Without indexes: Full scan of Records table (~1M rows) then Artists join
- With indexes: Direct lookup in `idx_artists_name` finds artist, then indexed `idx_records_artist_id` retrieves associated records
- Result: **8.3x speedup** from avoiding full table scans

## Customization

### Adjust Test Data
Edit `indexing_experiment.py` line ~160 to change:
- LIKE patterns: `"%Miles%"`, `"%Rock%"`
- Iteration count (repeats parameter)
- Test queries themselves

### Analyze Different Indexes
To experiment with different indexes:

1. Modify `add_indexes()` method to create different indexes
2. Re-run experiment
3. Compare results

Example - test a compound index:
```python
"CREATE INDEX idx_composite ON Records(artist_id, title) "
```

### Increase Sample Size
For more statistical confidence, increase iterations:
```python
self.run_experiment(repeats=500)  # default 100
```

## Report Sections

1. **Methodology** - Experimental approach and design
2. **Indexes Created** - All indexes applied to test database
3. **Performance Results** - Timing comparison table
4. **Execution Plan Analysis** - Query plan changes
5. **Summary** - Average improvements and key findings
6. **Key Findings** - Most and least improved queries
7. **Conclusion** - Overall impact assessment

## Troubleshooting

### "main.db not found"
Ensure you've seeded the database:
```bash
python3 src/register_user.py     # Create users
python3 src/seed_loans.py        # Populate with records/artists
```

### "No improvement observed"
Possible causes:
- Small dataset (indexes help more with large tables)
- Already optimized queries
- Indexes not selective enough for query predicates

Try:
- Verify index creation: `sqlite3 data/main_with_idx.db ".indices"`
- Check index usage: Review EXPLAIN QUERY PLAN output
- Increase dataset size for more dramatic differences

### Unexpected slow results with indexes
Possible causes:
- Index creation overhead (one-time cost)
- Query optimizer chooses table scan anyway (query parser issue)
- Very small table (overhead > benefit)

## Advanced Analysis

### Manual Index Review
```bash
sqlite3 data/main_with_idx.db
sqlite> .indices
sqlite> EXPLAIN QUERY PLAN SELECT ...;
```

### Disk Space Impact
```bash
ls -lh data/main*.db
```

Indexes add disk space but provide query speed benefits.

### Index Selectivity
```sql
-- Check how selective an index is
SELECT COUNT(DISTINCT artist_name) as distinct_names,
       COUNT(*) as total_rows
FROM Artists;
```

High selectivity = better index benefit

## References

- [SQLite EXPLAIN QUERY PLAN](https://www.sqlite.org/eqp.html)
- [SQLite Index Performance](https://www.sqlite.org/queryplanner.html)
- [CREATE INDEX Documentation](https://www.sqlite.org/lang_createindex.html)

---

**Report Location**: `indexing_experiment_report.txt` (generated after running)
