# Daily Word · Bible in a Year

A one-year Bible reading plan in a single web page. Each day pairs an Old Testament, New Testament, Psalm and Proverbs reading, so the whole Bible is covered in 365 days with variety every day.

**Live app:** https://speedkelvyn.github.io/Bible365/

## Features
- **Calendar-mapped plan:** pick a start date and every reading lines up with a real day
- **Pace tracking:** see whether you are ahead, on track or behind
- **Mark complete:** progress is saved in your browser
- **Open full reading:** each passage links straight to Bible Gateway
- **Daily prayer and journal notes** alongside the readings

## Run it
Open `index.html` in any browser. No install, no account; data stays on your device (localStorage).

## Python version
`bible365.py` runs the same plan from the command line (it reads the plan from `index.html`, so the two never drift apart):

```bash
python bible365.py start 2026-01-01   # set Day 1
python bible365.py today              # today's four readings, link and prayer
python bible365.py done               # mark today complete
python bible365.py pace               # on pace or behind?
python bible365.py export plan.ics    # whole year as calendar events (or plan.csv)
```

Standard library only. Tests: `python -m pytest tests`.

## Built with
HTML, CSS and vanilla JavaScript in a single file, hosted on GitHub Pages.
