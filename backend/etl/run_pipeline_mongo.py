"""ELT sin PocketBase: CSV → Parquet → MongoDB → tablas maestras."""
import subprocess
import sys

STEPS = (
    "etl.csv_to_parquet",
    "etl.load_parquet_to_mongo",
    "etl.transform_fact_dimensions",
)

for step in STEPS:
    print(f"\n=== {step} ===")
    if subprocess.run([sys.executable, "-m", step]).returncode:
        sys.exit(1)
print("\nELT (MongoDB directo) completado.")
