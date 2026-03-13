#!/usr/bin/env python3
"""
Python equivalent of the list_all_changes() ksh function.

Parses a TACT baseline changes_report file and groups file changes
(CHANGED / ADDED / DELETED) by committer, printing a formatted summary.

Usage:
    python3 list_all_changes.py <BASELINE>
    python3 list_all_changes.py  # uses $CONTEXT_CM_BASELINE to locate the file
"""

import os
import re
import sys
from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional


# ---------------------------------------------------------------------------
# ANSI colour helpers (mirrors the cecho / cechon pattern in the ksh script)
# ---------------------------------------------------------------------------
RESET = "\033[0m"

def bold_white(s: str) -> str:
    return f"\033[1;37m{s}{RESET}"

def bold_yellow(s: str) -> str:
    return f"\033[1;33m{s}{RESET}"

def bold_cyan(s: str) -> str:
    return f"\033[1;36m{s}{RESET}"

def bold_red(s: str) -> str:
    return f"\033[1;31m{s}{RESET}"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------
ADMIN_COMMITTERS = {"ifpsadm", "eldadm", "tactadm"}
TOOL_COMMON = "TOOL.COMMON"

@dataclass
class FileChange:
    kind: str            # CHANGED | ADDED | DELETED
    filepath: str
    diff_cmd: str = ""   # only for CHANGED
    view: str = ""       # branch the change came from


# ---------------------------------------------------------------------------
# Parsing
# ---------------------------------------------------------------------------
# Matches the "changed …  #emacs:(ediff-files …)" line
RE_CHANGED = re.compile(r"^\s+changed\s+.*#emacs:", re.IGNORECASE)
# Matches "added <path>" or "deleted <path>"
RE_ADDED   = re.compile(r"^\s+added\s+(\S+)",   re.IGNORECASE)
RE_DELETED = re.compile(r"^\s+deleted\s+(\S+)", re.IGNORECASE)
# The "← Merged from branch: …" continuation line
RE_MERGED  = re.compile(r"<-\s+Merged from branch:\s+(\S+)")


def _extract_filepath_from_ediff(diff_cmd: str) -> str:
    """Pull the *first* filename argument (old versioned path) from an ediff-files call."""
    parts = re.findall(r'"([^"]+)"', diff_cmd)
    return parts[0] if parts else ""


def parse_changes_report(path: str) -> dict[str, list[FileChange]]:
    """
    Returns {committer: [FileChange, …]} – skipping admin and TOOL.COMMON
    entries exactly as the ksh function does.
    """
    committer_changes: dict[str, list[FileChange]] = defaultdict(list)

    current_kind:      Optional[str] = None
    current_filepath:  str = ""
    current_diff_cmd:  str = ""
    change_detected:   bool = False

    with open(path, encoding="utf-8", errors="replace") as fh:
        for raw_line in fh:
            line         = raw_line.rstrip("\n")
            stripped     = line.lstrip()

            # ---- CHANGED -----------------------------------------------
            if RE_CHANGED.match(line):
                sep = "#emacs:"
                diff_part = line[line.index(sep) + len(sep):]
                current_diff_cmd  = diff_part.strip()
                current_filepath  = _extract_filepath_from_ediff(current_diff_cmd)
                current_kind      = "CHANGED"
                change_detected   = True
                continue

            # ---- ADDED -------------------------------------------------
            m = RE_ADDED.match(line)
            if m:
                current_filepath = m.group(1)
                current_diff_cmd = ""
                current_kind     = "ADDED"
                change_detected  = True
                continue

            # ---- DELETED -----------------------------------------------
            m = RE_DELETED.match(line)
            if m:
                current_filepath = m.group(1)
                current_diff_cmd = ""
                current_kind     = "DELETED"
                change_detected  = True
                continue

            # ---- Merged-from line (attribution) ------------------------
            if "<- Merged from branch:" in stripped and change_detected:
                m = RE_MERGED.search(line)
                if not m:
                    continue
                view = m.group(1)                      # e.g. /main/X.Y.Z.committer.branch/N
                # Extract committer: second-to-last dot-separated token of
                # the path component after /main/
                after_main = view.split("/main/", 1)[-1]  # X.Y.Z.committer.branch/N
                branch_part = after_main.split("/")[0]     # X.Y.Z.committer.branch
                tokens = branch_part.split(".")
                committer = tokens[-2] if len(tokens) >= 2 else ""

                # Apply the same filters as the ksh version
                skip = (
                    committer in ADMIN_COMMITTERS
                    or TOOL_COMMON in line
                    or not change_detected
                )
                if not skip:
                    committer_changes[committer].append(
                        FileChange(
                            kind=current_kind,
                            filepath=current_filepath,
                            diff_cmd=current_diff_cmd,
                            view=view,
                        )
                    )
                    change_detected = False  # only reset once the real committer is found

    return dict(committer_changes)


# ---------------------------------------------------------------------------
# Display helpers
# ---------------------------------------------------------------------------

def _display_file(change: FileChange) -> None:
    kind_label = {
        "CHANGED": bold_white("CHANGED"),
        "ADDED":   bold_cyan("ADDED"),
        "DELETED": bold_red("DELETED"),
    }.get(change.kind, change.kind)
    print(f"FILE {kind_label}: {change.filepath}")


def print_changes(committer_changes: dict[str, list[FileChange]]) -> None:
    for committer, changes in sorted(committer_changes.items()):
        header = (
            f"{'=' * 37} Files committed by user "
            f"{bold_white(committer)} {'=' * 37}"
        )
        print(header)

        for chg in changes:
            _display_file(chg)



# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def locate_report(baseline: Optional[str] = None) -> str:
    if baseline is None:
        baseline = os.environ.get("CONTEXT_CM_BASELINE", "")
    if not baseline:
        sys.exit(
            "ERROR: pass a changes_report file as argument, "
            "or set $CONTEXT_CM_BASELINE."
        )
    return (
        f"/cm/ot/TACT/baseline_reports/"
        f"TACT.TACT_CONFIG.{baseline}.changes_report"
    )


def list_all_changes(report_path: str) -> None:
    committer_changes = parse_changes_report(report_path)
    print_changes(committer_changes)

if __name__ == "__main__":
    if len(sys.argv) == 2:
        report = locate_report(sys.argv[1])   # treat arg as baseline number
        list_all_changes(report)
    else:
        print("Please give baseline e.g. 29.0.0.79")
