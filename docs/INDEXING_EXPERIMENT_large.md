# Indexing Impact Experiment (Large Dataset)

This is the same methodology guide adapted for the large dataset run. Use it to reproduce and understand the experiment with `data/main_V2.db`.

## Quick Run

```bash
# Large dataset
python3 src/indexing_experiment.py --db data/main_V2.db --repeats 200 --report indexing_experiment_report_large.txt
```

## Outputs
- indexing_experiment_report_large.txt — performance + plan comparison for the large dataset
- docs/EXPERIMENT_ANALYSIS_large.md — analysis tailored to the large run (see below)

## Notes
- Triggers (`sql/triggers.sql`) are shared and should be applied after seeding.
- Indexes are created by the experiment script for the "with indexes" database copy.
