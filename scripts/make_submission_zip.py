"""Build the submission bundle from the committed tree.

Takes exactly the files git has tracked at HEAD, so the bundle cannot contain
anything stale, untracked or ignored. Raw data is never tracked and therefore
never included.

Four working documents are excluded by default. They are our own notes on how
to run the project rather than part of it, and the submission is the project:

    docs/handover_prompt.md            notes for resuming work on the project
    docs/handoff_member_b.md           onboarding notes for the second member
    docs/presentation_guide.md         speaking notes for the viva
    docs/report_completion_checklist.md  our pre-submission checklist

The methodology record is kept: preregistration, decision log, deviations,
inference log, methods plan, dataset inventory and run registry are evidence
for how the analysis was conducted and belong in the submission.

    python scripts/make_submission_zip.py                  # trimmed (default)
    python scripts/make_submission_zip.py --with-notes     # everything tracked
"""
import argparse
import pathlib
import subprocess
import sys
import zipfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
PREFIX = "bbbd_mml/"

WORKING_NOTES = [
    "docs/handover_prompt.md",
    "docs/handoff_member_b.md",
    "docs/presentation_guide.md",
    "docs/report_completion_checklist.md",
]


def tracked_files():
    out = subprocess.check_output(["git", "ls-files"], cwd=ROOT, text=True)
    return [line for line in out.splitlines() if line]


def main():
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--with-notes", action="store_true",
                    help="include the four working documents excluded by default")
    ap.add_argument("-o", "--output", default="bbbd_mml_submission.zip")
    args = ap.parse_args()

    dirty = subprocess.check_output(["git", "status", "--porcelain"], cwd=ROOT, text=True)
    modified = [l for l in dirty.splitlines() if l and not l.startswith("??")]
    if modified:
        print("warning: tracked files differ from HEAD; the bundle uses the "
              "working tree, which is not what is committed:", file=sys.stderr)
        for line in modified:
            print("   ", line, file=sys.stderr)

    excluded = [] if args.with_notes else WORKING_NOTES
    files = [f for f in tracked_files() if f not in excluded]
    missing = [f for f in excluded if not (ROOT / f).exists()]
    if missing:
        print("note: excluded paths that no longer exist:", missing, file=sys.stderr)

    out = ROOT / args.output
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for rel in files:
            z.write(ROOT / rel, PREFIX + rel)

    total = sum(i.file_size for i in zipfile.ZipFile(out).infolist())
    print(f"wrote {out.name}: {len(files)} files, "
          f"{out.stat().st_size / 1e6:.2f} MB compressed, {total / 1e6:.1f} MB uncompressed")
    if excluded:
        print("excluded working documents:")
        for rel in excluded:
            print("   ", rel)


if __name__ == "__main__":
    main()
