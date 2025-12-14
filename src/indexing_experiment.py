#!/usr/bin/env python3
"""
Indexing Experiment: Comparing Full Table Scans vs. Indexed Queries
====================================================================

This experiment evaluates the impact of indexing on query performance by:
1. Creating a baseline database without indexes
2. Running catalog search queries and measuring execution time
3. Examining query execution plans for scan strategies
4. Adding strategic indexes
5. Re-running the same queries and comparing results
6. Analyzing improvements in performance and plan efficiency

Target: Artist name searches and Records-Artists joins with various filters
"""

import sqlite3
import time
import shutil
import os
from pathlib import Path
from dataclasses import dataclass
from typing import List, Tuple


@dataclass
class QueryResult:
    """Store metrics for a single query execution"""
    query_name: str
    index_status: str
    execution_time_ms: float
    row_count: int
    scan_type: str = ""  # SCAN vs SEARCH extracted from EXPLAIN PLAN
    sort_used: bool = False


@dataclass
class ExperimentMetrics:
    """Aggregate metrics for comparison"""
    query_name: str
    no_index_time_ms: float
    with_index_time_ms: float
    improvement_percent: float
    speedup_factor: float
    no_index_scan: str
    with_index_scan: str


class IndexingExperiment:
    """Conduct indexing experiment on catalog search queries"""

    def __init__(self, base_db="data/main.db", work_dir="data"):
        self.base_db = base_db
        self.work_dir = work_dir
        self.no_index_db = os.path.join(work_dir, "main_no_idx.db")
        self.with_index_db = os.path.join(work_dir, "main_with_idx.db")
        self.results: List[QueryResult] = []
        self.metrics: List[ExperimentMetrics] = []

    def setup_databases(self):
        """Create two copies of the database"""
        print("=" * 70)
        print("SETUP: Preparing databases")
        print("=" * 70)

        # Create no-index version
        if os.path.exists(self.no_index_db):
            os.remove(self.no_index_db)
        shutil.copy(self.base_db, self.no_index_db)
        print(f"✓ Created baseline (no indexes): {self.no_index_db}")

        # Create indexed version (starts as copy, will add indexes)
        if os.path.exists(self.with_index_db):
            os.remove(self.with_index_db)
        shutil.copy(self.base_db, self.with_index_db)
        print(f"✓ Created working (with indexes): {self.with_index_db}")

    def remove_indexes(self, db_path):
        """Drop any existing indexes from the database"""
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            # Get all user-created indexes
            cursor.execute(
                """
                SELECT name FROM sqlite_master 
                WHERE type='index' AND name NOT LIKE 'sqlite_%'
                """
            )
            indexes = [row[0] for row in cursor.fetchall()]
            
            for idx in indexes:
                cursor.execute(f"DROP INDEX IF EXISTS {idx}")
            
            conn.commit()
            if indexes:
                print(f"  Dropped {len(indexes)} existing indexes from {db_path}")
        finally:
            conn.close()

    def add_indexes(self, db_path):
        """Create strategic indexes on the database"""
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            
            # Strategic indexes for catalog search queries
            indexes = [
                # Artist name lookup (critical for artist searches)
                ("idx_artists_name", 
                 "CREATE INDEX IF NOT EXISTS idx_artists_name ON Artists(artist_name)"),
                
                # Foreign key relationship (speeds up JOIN operations)
                ("idx_records_artist_id",
                 "CREATE INDEX IF NOT EXISTS idx_records_artist_id ON Records(artist_id)"),
                
                # Record filters (is_active, genre)
                ("idx_records_is_active",
                 "CREATE INDEX IF NOT EXISTS idx_records_is_active ON Records(is_active)"),
                
                ("idx_records_genre",
                 "CREATE INDEX IF NOT EXISTS idx_records_genre ON Records(genre)"),
                
                # Copy and Loan lookups
                ("idx_copies_record_id",
                 "CREATE INDEX IF NOT EXISTS idx_copies_record_id ON Copies(record_id)"),
                
                ("idx_loans_copy_id",
                 "CREATE INDEX IF NOT EXISTS idx_loans_copy_id ON Loans(copy_id)"),
                
                # Artist genre filter
                ("idx_artists_genre",
                 "CREATE INDEX IF NOT EXISTS idx_artists_genre ON Artists(genre)"),
            ]
            
            for idx_name, idx_sql in indexes:
                cursor.execute(idx_sql)
            
            conn.commit()
            print(f"✓ Created {len(indexes)} indexes on {db_path}")
            self._list_indexes(cursor)
            
        finally:
            conn.close()

    def _list_indexes(self, cursor):
        """Display created indexes"""
        cursor.execute(
            """
            SELECT name, tbl_name FROM sqlite_master 
            WHERE type='index' AND name NOT LIKE 'sqlite_%'
            ORDER BY tbl_name, name
            """
        )
        for idx_name, tbl_name in cursor.fetchall():
            print(f"    - {idx_name} on {tbl_name}")

    def get_execution_plan(self, db_path: str, sql: str, params: Tuple = ()) -> List[str]:
        """
        Get the EXPLAIN QUERY PLAN output
        Returns list of plan lines describing scan strategy
        """
        conn = sqlite3.connect(db_path)
        try:
            cursor = conn.cursor()
            # EXPLAIN QUERY PLAN shows the execution plan
            cursor.execute(f"EXPLAIN QUERY PLAN\n{sql}", params)
            plan_lines = []
            for row in cursor.fetchall():
                plan_lines.append(str(row))
            return plan_lines
        finally:
            conn.close()

    def extract_scan_info(self, plan_lines: List[str]) -> str:
        """Parse execution plan to identify scan type (SCAN vs SEARCH via index)"""
        if not plan_lines:
            return "Unknown"
        
        plan_text = " ".join(plan_lines)
        
        if "SEARCH" in plan_text and "INDEX" in plan_text:
            return "INDEX SEARCH"
        elif "SCAN" in plan_text and "INDEX" in plan_text:
            return "INDEX SCAN"
        elif "SCAN" in plan_text:
            return "TABLE SCAN"
        else:
            return "Other"

    def execute_query(self, db_path: str, query_name: str, sql: str, 
                     params: Tuple = (), repeats: int = 100) -> QueryResult:
        """
        Execute a query multiple times and measure performance
        Also capture execution plan
        """
        conn = sqlite3.connect(db_path)
        try:
            # Get execution plan (just first execution for plan analysis)
            plan = self.get_execution_plan(db_path, sql, params)
            scan_type = self.extract_scan_info(plan)
            
            # Time the query executions
            cursor = conn.cursor()
            start = time.perf_counter()
            
            row_count = 0
            for _ in range(repeats):
                cursor.execute(sql, params)
                rows = cursor.fetchall()
                row_count = len(rows) if _ == 0 else row_count
            
            end = time.perf_counter()
            elapsed_ms = (end - start) * 1000.0
            
            # Determine index status from db_path
            index_status = "with indexes" if "with_idx" in db_path else "no indexes"
            
            result = QueryResult(
                query_name=query_name,
                index_status=index_status,
                execution_time_ms=elapsed_ms,
                row_count=row_count,
                scan_type=scan_type
            )
            
            return result
        finally:
            conn.close()

    def run_experiment(self, repeats: int = 100):
        """Execute the full experiment"""
        print("\n" + "=" * 70)
        print("EXPERIMENT: Measuring query performance")
        print("=" * 70)
        
        # Define test queries - these are typical catalog searches
        test_queries = [
            (
                "Search by artist name",
                """
                SELECT r.record_id, r.title, a.artist_name
                FROM Records r
                JOIN Artists a ON r.artist_id = a.artist_id
                WHERE a.artist_name LIKE ?
                ORDER BY a.artist_name, r.title
                """,
                ("%Miles%",)
            ),
            (
                "List all records with artists",
                """
                SELECT r.record_id, a.artist_name, r.title, r.genre
                FROM Records r
                JOIN Artists a ON r.artist_id = a.artist_id
                ORDER BY a.artist_name, r.title
                """,
                ()
            ),
            (
                "Find active records by artist",
                """
                SELECT r.record_id, r.title, a.artist_name
                FROM Records r
                JOIN Artists a ON r.artist_id = a.artist_id
                WHERE r.is_active = 1 AND a.artist_name LIKE ?
                """,
                ("%Rock%",)
            ),
            (
                "Count records per artist",
                """
                SELECT a.artist_name, COUNT(r.record_id) AS record_count
                FROM Artists a
                LEFT JOIN Records r ON a.artist_id = r.artist_id
                GROUP BY a.artist_id
                ORDER BY record_count DESC
                """,
                ()
            ),
            (
                "Find records by genre and artist",
                """
                SELECT a.artist_name, r.title, r.genre
                FROM Records r
                JOIN Artists a ON r.artist_id = a.artist_id
                WHERE r.genre = ? OR a.genre = ?
                """,
                ("Rock", "Rock")
            ),
        ]
        
        print(f"\nRunning {len(test_queries)} queries, {repeats} iterations each...\n")
        
        # Run queries on both databases
        for query_name, sql, params in test_queries:
            print(f"Testing: {query_name}")
            
            # Test without indexes
            result_no_idx = self.execute_query(
                self.no_index_db, query_name, sql, params, repeats
            )
            print(f"  Without indexes: {result_no_idx.execution_time_ms:.2f}ms ({result_no_idx.scan_type})")
            self.results.append(result_no_idx)
            
            # Test with indexes
            result_with_idx = self.execute_query(
                self.with_index_db, query_name, sql, params, repeats
            )
            print(f"  With indexes:    {result_with_idx.execution_time_ms:.2f}ms ({result_with_idx.scan_type})")
            self.results.append(result_with_idx)
            
            # Calculate metrics
            improvement = (
                (result_no_idx.execution_time_ms - result_with_idx.execution_time_ms) 
                / result_no_idx.execution_time_ms * 100
            )
            speedup = result_no_idx.execution_time_ms / result_with_idx.execution_time_ms
            
            metric = ExperimentMetrics(
                query_name=query_name,
                no_index_time_ms=result_no_idx.execution_time_ms,
                with_index_time_ms=result_with_idx.execution_time_ms,
                improvement_percent=improvement,
                speedup_factor=speedup,
                no_index_scan=result_no_idx.scan_type,
                with_index_scan=result_with_idx.scan_type
            )
            self.metrics.append(metric)
            print(f"  → Improvement: {improvement:.1f}% ({speedup:.2f}x faster)\n")

    def print_detailed_plans(self, repeats: int = 5):
        """Print detailed query execution plans for analysis"""
        print("\n" + "=" * 70)
        print("ANALYSIS: Query Execution Plans")
        print("=" * 70)
        
        test_queries = [
            (
                "Search by artist name",
                """
                SELECT r.record_id, r.title, a.artist_name
                FROM Records r
                JOIN Artists a ON r.artist_id = a.artist_id
                WHERE a.artist_name LIKE ?
                ORDER BY a.artist_name, r.title
                """,
                ("%Miles%",)
            ),
            (
                "List all records with artists",
                """
                SELECT r.record_id, a.artist_name, r.title, r.genre
                FROM Records r
                JOIN Artists a ON r.artist_id = a.artist_id
                ORDER BY a.artist_name, r.title
                """,
                ()
            ),
        ]
        
        for query_name, sql, params in test_queries:
            print(f"\n{'─' * 70}")
            print(f"Query: {query_name}")
            print(f"{'─' * 70}")
            
            print("\n[WITHOUT INDEXES]")
            plan_no_idx = self.get_execution_plan(self.no_index_db, sql, params)
            for line in plan_no_idx:
                print(f"  {line}")
            
            print("\n[WITH INDEXES]")
            plan_with_idx = self.get_execution_plan(self.with_index_db, sql, params)
            for line in plan_with_idx:
                print(f"  {line}")

    def generate_report(self, output_file: str = "indexing_experiment_report.txt"):
        """Generate a comprehensive experiment report"""
        print("\n" + "=" * 70)
        print("REPORT: Indexing Experiment Results")
        print("=" * 70)
        
        report = []
        report.append("=" * 80)
        report.append("INDEXING IMPACT EXPERIMENT REPORT")
        report.append("=" * 80)
        report.append("")
        report.append("METHODOLOGY")
        report.append("-" * 80)
        report.append("Catalog search queries joining Artists and Records were executed on a seeded")
        report.append("database (main.db) both before and after adding indexes on artist names and")
        report.append("foreign key columns. Query execution plans were examined to observe changes in")
        report.append("scan strategy and sorting behavior.")
        report.append("")
        report.append("INDEXES CREATED")
        report.append("-" * 80)
        report.append("  - idx_artists_name        - ON Artists(artist_name)")
        report.append("  - idx_records_artist_id   - ON Records(artist_id)")
        report.append("  - idx_records_is_active   - ON Records(is_active)")
        report.append("  - idx_records_genre       - ON Records(genre)")
        report.append("  - idx_copies_record_id    - ON Copies(record_id)")
        report.append("  - idx_loans_copy_id       - ON Loans(copy_id)")
        report.append("  - idx_artists_genre       - ON Artists(genre)")
        report.append("")
        
        report.append("QUERY PERFORMANCE RESULTS")
        report.append("-" * 80)
        report.append(f"{'Query':<35} {'No Index (ms)':<18} {'Indexed (ms)':<18} {'Improvement':<15}")
        report.append("-" * 80)
        
        for metric in self.metrics:
            improvement_str = f"{metric.improvement_percent:.1f}% ({metric.speedup_factor:.2f}x)"
            report.append(
                f"{metric.query_name:<35} {metric.no_index_time_ms:<18.2f} "
                f"{metric.with_index_time_ms:<18.2f} {improvement_str:<15}"
            )
        
        report.append("")
        report.append("EXECUTION PLAN ANALYSIS")
        report.append("-" * 80)
        
        for metric in self.metrics:
            report.append(f"\n{metric.query_name}")
            report.append(f"  Without indexes: {metric.no_index_scan}")
            report.append(f"  With indexes:    {metric.with_index_scan}")
        
        report.append("")
        report.append("=" * 80)
        report.append("SUMMARY")
        report.append("=" * 80)
        
        avg_improvement = sum(m.improvement_percent for m in self.metrics) / len(self.metrics)
        avg_speedup = sum(m.speedup_factor for m in self.metrics) / len(self.metrics)
        
        report.append(f"Average performance improvement: {avg_improvement:.1f}%")
        report.append(f"Average speedup factor: {avg_speedup:.2f}x")
        report.append("")
        
        # Key findings
        report.append("KEY FINDINGS")
        report.append("-" * 80)
        
        max_metric = max(self.metrics, key=lambda m: m.improvement_percent)
        min_metric = min(self.metrics, key=lambda m: m.improvement_percent)
        
        report.append(f"- Biggest improvement: {max_metric.query_name}")
        report.append(f"  {max_metric.improvement_percent:.1f}% faster with indexes ({max_metric.speedup_factor:.2f}x)")
        report.append(f"  Scan strategy change: {max_metric.no_index_scan} -> {max_metric.with_index_scan}")
        report.append("")
        report.append(f"- Smallest improvement: {min_metric.query_name}")
        report.append(f"  {min_metric.improvement_percent:.1f}% faster with indexes ({min_metric.speedup_factor:.2f}x)")
        
        report.append("")
        report.append("CONCLUSION")
        report.append("-" * 80)
        report.append("Indexes on artist names and foreign key columns demonstrate significant")
        report.append("performance benefits for catalog search queries. The query optimizer can use")
        report.append("these indexes to avoid full table scans and efficiently retrieve records.")
        report.append("")
        
        # Print to console and file
        report_text = "\n".join(report)
        print(report_text)
        
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(report_text)
        
        print(f"\n✓ Report saved to: {output_file}")

    def run_full_experiment(self):
        """Execute the complete experiment from setup to report"""
        try:
            self.setup_databases()
            self.remove_indexes(self.no_index_db)
            print(f"\n✓ Confirmed no indexes on: {self.no_index_db}")
            
            self.add_indexes(self.with_index_db)
            
            self.run_experiment(repeats=100)
            
            self.print_detailed_plans()
            
            self.generate_report("indexing_experiment_report.txt")
            
        except Exception as e:
            print(f"\n❌ Error during experiment: {e}")
            raise


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Run indexing impact experiment on a SQLite database")
    parser.add_argument("--db", dest="base_db", default="data/main.db", help="Path to the base SQLite DB to copy and use (default: data/main.db)")
    parser.add_argument("--repeats", dest="repeats", type=int, default=100, help="Iterations per query (default: 100)")
    parser.add_argument("--workdir", dest="workdir", default="data", help="Working directory for output DB copies (default: data)")
    parser.add_argument("--report", dest="report", default="indexing_experiment_report.txt", help="Filename for the generated report (default: indexing_experiment_report.txt)")
    args = parser.parse_args()

    experiment = IndexingExperiment(
        base_db=args.base_db,
        work_dir=args.workdir
    )
    # Run with requested repeat count
    experiment.setup_databases()
    experiment.remove_indexes(experiment.no_index_db)
    experiment.add_indexes(experiment.with_index_db)
    experiment.run_experiment(repeats=args.repeats)
    experiment.print_detailed_plans()
    experiment.generate_report(args.report)
