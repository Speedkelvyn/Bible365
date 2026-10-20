import datetime as dt
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import bible365 as B


def test_plan_has_365_days_with_four_readings():
    plan = B.load_plan()
    assert len(plan) == 365
    assert plan[0] == {"day": 1, "ot": "Genesis 1", "nt": "Matthew 1", "ps": "Psalm 1", "pr": "Proverbs 1"}
    assert all(p["ot"] and p["nt"] and p["ps"] and p["pr"] for p in plan)


def test_start_date_mapping():
    start = dt.date(2026, 1, 1)
    assert B.day_from_start(start, dt.date(2026, 1, 1)) == 1
    assert B.day_from_start(start, dt.date(2026, 2, 1)) == 32
    assert B.day_from_start(start, dt.date(2025, 12, 1)) == 1  # before start: clamp to day 1
    assert B.day_from_start(start, dt.date(2027, 6, 1)) == 365  # after the year: clamp to 365
    assert B.day_to_date(32, start) == dt.date(2026, 2, 1)


def test_pace_matches_page_rule():
    start = dt.date(2026, 1, 1)
    assert B.pace(set(range(1, 11)), start, dt.date(2026, 1, 10))["status"] == "On Pace"
    assert B.pace({1, 2}, start, dt.date(2026, 1, 10))["status"] == "8 Behind"
    assert B.pace(set(), None)["status"] == "Ready"


def test_next_open_wraps():
    assert B.next_open({1, 2, 3}, 1) == 4
    assert B.next_open(set(range(5, 366)), 10) == 1
    assert B.next_open(set(range(1, 366)), 1) is None


def test_progress_round_trip(tmp_path):
    p = B.Progress(tmp_path / "p.json")
    p.start, p.completed, p.notes = dt.date(2026, 1, 1), {1, 5}, {5: "note"}
    p.save()
    q = B.Progress(tmp_path / "p.json")
    assert (q.start, q.completed, q.notes) == (p.start, p.completed, p.notes)


def test_exports(tmp_path):
    prog = B.Progress(tmp_path / "p.json")
    prog.start = dt.date(2026, 1, 1)
    plan = B.load_plan()
    B.export(plan, prog, tmp_path / "plan.csv", "NIV")
    B.export(plan, prog, tmp_path / "plan.ics", "NIV")
    assert (tmp_path / "plan.csv").read_text().count("\n") == 366
    assert (tmp_path / "plan.ics").read_text().count("BEGIN:VEVENT") == 365
