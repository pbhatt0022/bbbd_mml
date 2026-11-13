"""Register a batch script's output through `bbbd.runlog`.

README rule 3: a number may appear in the report only if it has a run ID. The Exp 2
batch scripts wrote plain CSVs, so their output could not be cited. This wraps them
without touching their processing logic.

Usage at the end of a script's main():

    from bbbd import batch_runlog
    batch_runlog.register(cfg, name="ecg_exp2", notebook="ecg_batch", member="B",
                          tables={"ecg_qc.csv": qc_df, "ecg_features.csv": feature_df},
                          summary={"n_processed": 120, "median_f1": 0.97})
"""
from __future__ import annotations

from . import runlog


def register(cfg: dict, name: str, notebook: str, tables: dict, summary: dict,
             member: str = "", note: str = "", seed: int | None = None) -> str:
    """Save tables and a summary under a fresh run ID. Returns the run ID.

    `tables` maps filename -> DataFrame; a name ending .parquet is written as Parquet.
    `summary` is written as JSON alongside them.
    """
    run = runlog.start_run(cfg, name=name, notebook=notebook, member=member,
                           seed=seed if seed is not None else cfg["seeds"]["global"])
    for filename, df in tables.items():
        if df is None or not len(df):
            continue
        runlog.save_table(run, df, filename)
    runlog.save_json(run, summary, f"{name}.json")
    runlog.finish_run(run, note=note or f"{notebook}: {name}")
    return run.run_id
