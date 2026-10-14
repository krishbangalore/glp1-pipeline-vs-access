"""
DEPRECATED — do not use.

This file previously generated a synthetic dataset using Python's random module.
It has been replaced by data_pull.py, which fetches real trial data from the
ClinicalTrials.gov v2 API (clinicaltrials.gov/api/v2/studies).

To build the dataset:
    python data_pull.py    # downloads real trials from CT.gov API (~2-4 min)
    python build_db.py     # loads CSVs into SQLite + adds FDA shortage/enforcement tables
    python analysis.py     # runs SQL queries, saves data/processed/
    python visualize.py    # creates figures/

See README.md for full setup instructions.
"""

raise SystemExit(
    "generate_data.py is deprecated. Run 'python data_pull.py' instead "
    "to download real trial data from ClinicalTrials.gov."
)
