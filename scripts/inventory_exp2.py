"""List candidate Experiment 2 inputs and outputs without loading signals."""

import argparse
import csv
import os
from pathlib import Path
import re


EXP2 = re.compile(r"(?<![a-z0-9])exp(?:eriment)?[ _-]*0?2(?![0-9])", re.I)
TABLE = re.compile(r"feature|target|quiz|validation|exclusion|diagnostic|qc|questionnaire", re.I)
SKIP = {".git", ".venv", "venv", "node_modules", "__pycache__"}


def inventory(root):
    def on_error(error):
        print(f"Could not read: {error}")

    for folder, dirs, files in os.walk(root, onerror=on_error):
        dirs[:] = sorted(d for d in dirs if d not in SKIP)
        for name in dirs:
            if EXP2.search(name):
                print(f"Experiment 2 directory: {Path(folder) / name}")
        for name in sorted(files):
            path = Path(folder) / name
            suffix = path.suffix.lower()
            exp2 = bool(EXP2.search(str(path)))
            if suffix == ".zip" and exp2:
                print(f"Archive: {path}")
            elif suffix in {".csv", ".tsv", ".parquet"} and TABLE.search(name):
                if exp2 or suffix in {".csv", ".parquet"}:
                    print(f"{'Experiment 2 path' if exp2 else 'Check experiment'}: {path}")
                    if suffix in {".csv", ".tsv"}:
                        try:
                            with path.open(encoding="utf-8-sig", newline="") as stream:
                                header = next(csv.reader(stream, delimiter="\t" if suffix == ".tsv" else ","), [])
                            print(f"  Columns: {', '.join(header) or '(empty file)'}")
                        except (OSError, UnicodeError, csv.Error) as error:
                            print(f"  Could not read header: {error}")
            elif exp2 and name == "run_meta.json":
                print(f"Run metadata: {path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("roots", nargs="+", type=Path, help="Data or output directories to inspect")
    args = parser.parse_args()
    for root in args.roots:
        if not root.is_dir():
            parser.error(f"Not a directory: {root}")
        inventory(root.resolve())
