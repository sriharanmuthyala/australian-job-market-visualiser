#!/usr/bin/env python3
"""
Turn the Jobs and Skills Australia employment projections workbook into data.json
for the treemap viewer.

Accepts either the original spreadsheet or a JSON dump of it:

    python build_data.py "Employment Projections - May 2025 to May 2035.xlsx"
    python build_data.py employment_projections_may_2025_to_may_2035.json
    python build_data.py <file> --inspect        # show sheets and headers, write nothing

The workbook is at https://www.jobsandskills.gov.au/data/employment-projections

Table 6 is the one that matters: employment projections by occupation unit group,
ANZSCO 4-digit level. Column headings move between annual releases, so columns are
matched by keyword rather than by position.
"""

import argparse
import json
import re
import sys
from datetime import date

MAJOR_GROUPS = {
    "1": "Managers",
    "2": "Professionals",
    "3": "Technicians and Trades Workers",
    "4": "Community and Personal Service Workers",
    "5": "Clerical and Administrative Workers",
    "6": "Sales Workers",
    "7": "Machinery Operators and Drivers",
    "8": "Labourers",
    "9": "Labourers",
}

# field -> (keywords that must all appear, keywords that must not)
MATCHERS = {
    "level":       (["occupation", "level"], []),
    "nfd":         (["nfd"], []),
    "code":        (["code"], []),
    "name":        (["occupation"], ["level", "code", "nfd"]),
    "skill_level": (["skill", "level"], ["occupation level"]),
    "emp_2025":    (["2025"], ["change", "%"]),
    "emp_2030":    (["2030"], ["change", "%"]),
    "emp_2035":    (["2035"], ["change", "%"]),
    "growth_5y":   (["5-year", "%"], ["10-year"]),
    "growth_10y":  (["10-year", "%"], []),
}


def norm(v):
    return re.sub(r"\s+", " ", str(v if v is not None else "")).strip().lower()


def num(v):
    if v is None or v == "" or v == "-":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        return float(v)
    s = re.sub(r"[^0-9.\-]", "", str(v))
    try:
        return float(s)
    except ValueError:
        return None


# ---------------------------------------------------------------- loading

def sheets_from_json(path):
    doc = json.load(open(path, encoding="utf-8"))
    if isinstance(doc, dict) and "sheets" in doc:
        return [(s.get("name", "?"), s.get("rows", [])) for s in doc["sheets"]]
    if isinstance(doc, dict):
        return [(k, v) for k, v in doc.items() if isinstance(v, list)]
    sys.exit("Unrecognised JSON layout. Expected {'sheets': [{'name', 'rows'}]}.")


def sheets_from_xlsx(path):
    try:
        from openpyxl import load_workbook
    except ImportError:
        sys.exit("pip install openpyxl")
    wb = load_workbook(path, data_only=True, read_only=True)
    return [(ws.title, [list(r) for r in ws.iter_rows(values_only=True)]) for ws in wb.worksheets]


def load(path):
    return sheets_from_json(path) if path.lower().endswith(".json") else sheets_from_xlsx(path)


# ---------------------------------------------------------------- headers

def ffill(row):
    """Carry a merged header cell sideways across the columns it spans."""
    out, last = [], ""
    for c in row:
        t = norm(c)
        if t:
            last = t
        out.append(last)
    return out


def header_at(rows, i):
    """Combine a header row with the row beneath it."""
    top = ffill(rows[i])
    bottom = [norm(c) for c in rows[i + 1]] if i + 1 < len(rows) else []
    width = max(len(top), len(bottom))
    top += [""] * (width - len(top))
    bottom += [""] * (width - len(bottom))
    return [f"{a} {b}".strip() for a, b in zip(top, bottom)]


def find_header(rows, scan=25):
    for i in range(min(scan, len(rows))):
        cells = [norm(c) for c in rows[i]]
        if any("code" in c for c in cells) and sum(1 for c in cells if c) >= 3:
            return i, header_at(rows, i)
    return None, None


def map_columns(headers):
    cols = {}
    for field, (must, mustnt) in MATCHERS.items():
        for i, h in enumerate(headers):
            if h and all(k in h for k in must) and not any(k in h for k in mustnt):
                cols.setdefault(field, i)
    return cols


def pick_sheet(sheets, wanted=None):
    if wanted:
        for name, rows in sheets:
            if wanted.lower() in name.lower():
                return name, rows
        sys.exit(f"No sheet matching '{wanted}'.")
    scored = []
    for name, rows in sheets:
        n = name.lower()
        score = ("unit group" in n) * 4 + ("occupation" in n) * 2 + (len(rows) > 100)
        scored.append((score, len(rows), name, rows))
    scored.sort(key=lambda t: (t[0], t[1]), reverse=True)
    return scored[0][2], scored[0][3]


# ---------------------------------------------------------------- build

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("src", nargs="?", help=".xlsx workbook or .json dump of it")
    ap.add_argument("--sheet")
    ap.add_argument("--out", default="data.json")
    ap.add_argument("--inspect", action="store_true")
    ap.add_argument("--keep-nfd", action="store_true",
                    help="keep 'not further defined' residual rows (off by default)")
    args = ap.parse_args()
    if not args.src:
        ap.error("pass the workbook or its JSON dump")

    sheets = load(args.src)

    if args.inspect:
        for name, rows in sheets:
            i, headers = find_header(rows)
            print(f"\n=== {name}  ({len(rows)} rows)")
            if headers:
                print(f"    header row {i}:")
                for j, h in enumerate(headers):
                    if h:
                        print(f"      [{j}] {h}")
        return

    name, rows = pick_sheet(sheets, args.sheet)
    hi, headers = find_header(rows)
    if not headers:
        sys.exit(f"No header row found in '{name}'. Run --inspect and pass --sheet.")
    cols = map_columns(headers)
    print(f"sheet: {name}   header row: {hi}")
    for f in MATCHERS:
        if f in cols:
            print(f"  {f:<12} <- [{cols[f]}] {headers[cols[f]]}")
    for req in ("code", "name", "emp_2025"):
        if req not in cols:
            sys.exit(f"Couldn't find a column for '{req}'. Run --inspect.")

    def cell(row, f):
        i = cols.get(f)
        return row[i] if i is not None and i < len(row) else None

    out, seen, skipped_nfd = [], set(), 0
    for row in rows[hi + 2:]:
        if not isinstance(row, list):
            continue
        code = str(cell(row, "code") or "").strip()
        code = re.sub(r"\.0$", "", code)
        if not code.isdigit() or len(code) != 4:
            continue                                  # majors, sub-majors, notes, totals

        lvl = num(cell(row, "level"))
        if lvl is not None and lvl != 4:
            continue
        if not args.keep_nfd and str(cell(row, "nfd") or "").strip().upper() == "Y":
            skipped_nfd += 1                          # 'not further defined' residuals
            continue
        if code in seen:
            continue

        nm = str(cell(row, "name") or "").strip()
        emp25 = num(cell(row, "emp_2025"))
        if not nm or not emp25:
            continue

        emp30, emp35 = num(cell(row, "emp_2030")), num(cell(row, "emp_2035"))
        g5, g10 = num(cell(row, "growth_5y")), num(cell(row, "growth_10y"))
        # Percentages arrive as fractions (0.0766) in this release, but have been
        # published as whole numbers (7.66) before now.
        pct = lambda v: None if v is None else (v * 100 if abs(v) <= 2 else v)
        g5, g10 = pct(g5), pct(g10)
        if g5 is None and emp30:
            g5 = (emp30 - emp25) / emp25 * 100
        if g10 is None and emp35:
            g10 = (emp35 - emp25) / emp25 * 100

        k = 1000 if emp25 < 5000 else 1                # employment is in thousands

        # Skill level can list several, e.g. "3, 4", when the unit group spans them.
        raw_skill = str(cell(row, "skill_level") or "").strip()
        digits = re.findall(r"\d", raw_skill)

        seen.add(code)
        out.append({
            "code": code,
            "name": nm,
            "major": code[0],
            "major_name": MAJOR_GROUPS.get(code[0], "Other"),
            "skill_level": int(digits[0]) if digits else None,
            "skill_levels": raw_skill if len(digits) > 1 else None,
            "emp_2025": round(emp25 * k),
            "emp_2030": round(emp30 * k) if emp30 else None,
            "emp_2035": round(emp35 * k) if emp35 else None,
            "growth_5y": round(g5, 1) if g5 is not None else None,
            "growth_10y": round(g10, 1) if g10 is not None else None,
            "pay_weekly": None,
            "shortage": None,
            "ai_exposure": None,
        })

    if not out:
        sys.exit("No occupation rows matched. Run --inspect to check the sheet.")

    doc = {
        "meta": {
            "source": "Jobs and Skills Australia, Employment Projections May 2025 – May 2035",
            "baseline": "May 2025",
            "classification": "ANZSCO 4-digit unit groups",
            "sheet": name,
            "generated": date.today().isoformat(),
        },
        "occupations": sorted(out, key=lambda d: -d["emp_2025"]),
    }
    json.dump(doc, open(args.out, "w"), indent=1)
    total = sum(d["emp_2025"] for d in out)
    print(f"\nwrote {args.out}: {len(out)} occupations, {total:,} people employed")
    if skipped_nfd:
        print(f"skipped {skipped_nfd} 'not further defined' rows (--keep-nfd to include)")


if __name__ == "__main__":
    main()
