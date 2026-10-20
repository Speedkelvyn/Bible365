"""bible365.py: the Python version of Daily Word · Bible in a Year.

Same 365-day plan as the web page (it reads the plan straight from index.html, so the
two never drift apart), with the same start-date mapping, pace tracking, completion
marks, notes and daily prayer. Progress is saved to a small JSON file.

    python bible365.py today                    # today's readings (or day 1 if no start date)
    python bible365.py start 2026-01-01         # set the start date ("start today" also works)
    python bible365.py day 120                  # show any day
    python bible365.py done                     # mark today's reading complete (or: done 42)
    python bible365.py undo 42                  # unmark a day
    python bible365.py note "Joseph forgives"   # save a note for today (or: note 42 "text")
    python bible365.py pace                     # are you on pace?
    python bible365.py next                     # first day not yet completed
    python bible365.py export plan.csv          # whole plan (with your dates) as CSV
    python bible365.py export plan.ics          # calendar file: one all-day event per reading

Options: --progress FILE (default bible365_progress.json next to this script), --version NIV.
"""
from __future__ import annotations

import argparse
import csv
import datetime as dt
import json
import pathlib
import re
import sys
import urllib.parse

HERE = pathlib.Path(__file__).resolve().parent
TOTAL_DAYS = 365
_PLAN_RE = re.compile(r"\{\s*day:\s*(\d+),\s*ot:\s*'([^']*)',\s*nt:\s*'([^']*)',\s*ps:\s*'([^']*)',\s*pr:\s*'([^']*)'\s*\}")


# --------------------------------------------------------------------------- plan


def load_plan(html_path: pathlib.Path = HERE / "index.html") -> list[dict]:
    """Read the 365-day reading plan from the web page."""
    text = html_path.read_text(encoding="utf-8")
    plan = [dict(day=int(d), ot=ot, nt=nt, ps=ps, pr=pr) for d, ot, nt, ps, pr in _PLAN_RE.findall(text)]
    if len(plan) != TOTAL_DAYS or [p["day"] for p in plan] != list(range(1, TOTAL_DAYS + 1)):
        raise ValueError(f"expected days 1–{TOTAL_DAYS} in {html_path.name}, found {len(plan)}")
    return plan


def clamp_day(day: int) -> int:
    return max(1, min(TOTAL_DAYS, int(day or 1)))


def day_from_start(start: dt.date, today: dt.date | None = None) -> int:
    """Which plan day today is, counting the start date as Day 1 (clamped to 1–365)."""
    today = today or dt.date.today()
    return clamp_day((today - start).days + 1)


def day_to_date(day: int, start: dt.date | None) -> dt.date | None:
    return start + dt.timedelta(days=day - 1) if start else None


def gateway_url(reading: dict, version: str = "NIV") -> str:
    """Bible Gateway link that opens all four passages at once (as the page's 'Open full reading')."""
    q = urllib.parse.urlencode({"search": f"{reading['ot']}; {reading['nt']}; {reading['ps']}; {reading['pr']}", "version": version})
    return f"https://www.biblegateway.com/passage/?{q}"


def prayer(reading: dict) -> str:
    return (f"Father, as I read {reading['ot']}, {reading['nt']}, {reading['ps']}, and {reading['pr']}, "
            "help me understand Your truth, worship You sincerely, walk in wisdom, and remain faithful "
            "through this one-year journey. Amen.")


def pace(completed: set[int], start: dt.date | None, today: dt.date | None = None) -> dict:
    """On pace when days completed ≥ the day the calendar points to (same rule as the page)."""
    if not start:
        return {"status": "Ready", "message": "Set your start date to see whether you are on pace."}
    expected = day_from_start(start, today)
    done = len(completed)
    if done >= expected:
        return {"status": "On Pace", "expected": expected, "done": done,
                "message": f"You have completed {done} days, and your calendar currently points to Day {expected}."}
    gap = expected - done
    return {"status": f"{gap} Behind", "expected": expected, "done": done,
            "message": f"You are {gap} day{'' if gap == 1 else 's'} behind. Keep the daily rhythm and keep moving."}


def next_open(completed: set[int], current: int) -> int | None:
    """First incomplete day from `current` onward, wrapping to the start; None if all done."""
    for d in list(range(current, TOTAL_DAYS + 1)) + list(range(1, current)):
        if d not in completed:
            return d
    return None


# --------------------------------------------------------------------------- progress file


class Progress:
    def __init__(self, path: pathlib.Path):
        self.path = path
        data = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
        self.start: dt.date | None = dt.date.fromisoformat(data["start_date"]) if data.get("start_date") else None
        self.completed: set[int] = {int(d) for d in data.get("completed", [])}
        self.notes: dict[int, str] = {int(k): v for k, v in data.get("notes", {}).items()}

    def save(self) -> None:
        self.path.write_text(json.dumps({
            "start_date": self.start.isoformat() if self.start else None,
            "completed": sorted(self.completed),
            "notes": {str(k): v for k, v in sorted(self.notes.items()) if v},
        }, indent=2), encoding="utf-8")

    def today(self) -> int:
        return day_from_start(self.start) if self.start else 1


# --------------------------------------------------------------------------- output


def show_day(plan: list[dict], prog: Progress, day: int, version: str) -> None:
    r = plan[clamp_day(day) - 1]
    when = day_to_date(r["day"], prog.start)
    status = "✓ completed" if r["day"] in prog.completed else "○ not yet read"
    print(f"\nDay {r['day']} of {TOTAL_DAYS}" + (f" · {when:%A, %b %d}" if when else "") + f"   {status}")
    print("─" * 52)
    for label, key in (("Old Testament", "ot"), ("New Testament", "nt"), ("Psalm", "ps"), ("Proverbs", "pr")):
        print(f"  {label:<14} {r[key]}")
    print(f"\n  Read online: {gateway_url(r, version)}")
    print(f"\n  Prayer: {prayer(r)}")
    if prog.notes.get(r["day"]):
        print(f"\n  Your note: {prog.notes[r['day']]}")
    print(f"\n  Pace: {pace(prog.completed, prog.start)['message']}\n")


def export(plan: list[dict], prog: Progress, out: pathlib.Path, version: str) -> None:
    if out.suffix.lower() == ".ics":
        if not prog.start:
            raise SystemExit("Set a start date first (python bible365.py start YYYY-MM-DD) so readings land on dates.")
        lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Bible365//Daily Word//EN", "CALSCALE:GREGORIAN"]
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        for r in plan:
            d = day_to_date(r["day"], prog.start)
            lines += ["BEGIN:VEVENT", f"UID:bible365-day{r['day']}-{prog.start:%Y%m%d}@speedkelvyn.github.io",
                      f"DTSTAMP:{stamp}", f"DTSTART;VALUE=DATE:{d:%Y%m%d}", f"DTEND;VALUE=DATE:{d + dt.timedelta(days=1):%Y%m%d}",
                      f"SUMMARY:Bible Day {r['day']}: {r['ot']}\\, {r['nt']}\\, {r['ps']}\\, {r['pr']}",
                      f"URL:{gateway_url(r, version)}", "END:VEVENT"]
        lines.append("END:VCALENDAR")
        out.write_text("\r\n".join(lines) + "\r\n", encoding="utf-8")
    else:
        with out.open("w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["day", "date", "old_testament", "new_testament", "psalm", "proverbs", "completed", "note", "link"])
            for r in plan:
                d = day_to_date(r["day"], prog.start)
                w.writerow([r["day"], d.isoformat() if d else "", r["ot"], r["nt"], r["ps"], r["pr"],
                            "yes" if r["day"] in prog.completed else "", prog.notes.get(r["day"], ""), gateway_url(r, version)])
    print(f"Wrote {out} ({TOTAL_DAYS} days)")


# --------------------------------------------------------------------------- CLI


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("command", nargs="?", default="today",
                    choices=["today", "day", "start", "done", "undo", "note", "pace", "next", "export"])
    ap.add_argument("args", nargs="*")
    ap.add_argument("--progress", type=pathlib.Path, default=HERE / "bible365_progress.json")
    ap.add_argument("--version", default="NIV", help="Bible Gateway translation (default NIV)")
    a = ap.parse_args(argv)

    plan = load_plan()
    prog = Progress(a.progress)
    day_arg = lambda i=0: clamp_day(int(a.args[i])) if len(a.args) > i and a.args[i].isdigit() else prog.today()

    if a.command == "today":
        show_day(plan, prog, prog.today(), a.version)
    elif a.command == "day":
        show_day(plan, prog, day_arg(), a.version)
    elif a.command == "start":
        val = a.args[0] if a.args else "today"
        prog.start = dt.date.today() if val == "today" else dt.date.fromisoformat(val)
        prog.save()
        print(f"Day 1 begins on {prog.start:%A, %b %d, %Y}. Today maps to Day {prog.today()}.")
    elif a.command in ("done", "undo"):
        d = day_arg()
        (prog.completed.add if a.command == "done" else prog.completed.discard)(d)
        prog.save()
        print(f"Day {d} marked {'complete' if a.command == 'done' else 'incomplete'}. {pace(prog.completed, prog.start)['message']}")
    elif a.command == "note":
        if a.args and a.args[0].isdigit():
            d, text = int(a.args[0]), " ".join(a.args[1:])
        else:
            d, text = prog.today(), " ".join(a.args)
        prog.notes[clamp_day(d)] = text
        prog.save()
        print(f"Note saved for Day {clamp_day(d)}.")
    elif a.command == "pace":
        p = pace(prog.completed, prog.start)
        print(f"{p['status']}: {p['message']}  ({len(prog.completed)}/{TOTAL_DAYS} days complete)")
    elif a.command == "next":
        d = next_open(prog.completed, prog.today())
        if d is None:
            print("All days completed. Well done.")
        else:
            show_day(plan, prog, d, a.version)
    elif a.command == "export":
        export(plan, prog, pathlib.Path(a.args[0] if a.args else "bible365_plan.csv"), a.version)
    return 0


if __name__ == "__main__":
    sys.exit(main())
