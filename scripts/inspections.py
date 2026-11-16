#!/usr/bin/env python3
"""Query NYC DOHMH restaurant inspection results (NYC Open Data, dataset 43nn-pn8j).

Usage:
  inspections.py search --name "joe's pizza" [--zip 10014] [--boro Manhattan] [--street carmine]
  inspections.py history --camis 50012345 [--inspections 5]

Each row in the dataset is one violation; rows are grouped here into inspections.
No API key is needed. Set SOCRATA_APP_TOKEN to raise rate limits.
"""
import argparse
import json
import os
import sys
import urllib.parse
import urllib.request
from collections import OrderedDict

ENDPOINT = "https://data.cityofnewyork.us/resource/43nn-pn8j.json"
BOROS = {"manhattan", "brooklyn", "queens", "bronx", "staten island"}


def soql_str(value):
    return "'" + value.replace("'", "''") + "'"


def fetch(params):
    url = ENDPOINT + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url)
    token = os.environ.get("SOCRATA_APP_TOKEN")
    if token:
        req.add_header("X-App-Token", token)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.load(resp)
    except urllib.error.HTTPError as e:
        sys.exit(f"API error {e.code}: {e.read().decode(errors='replace')[:500]}")
    except urllib.error.URLError as e:
        sys.exit(f"Network error: {e.reason}")


def day(ts):
    return (ts or "")[:10]


def address(r):
    parts = [r.get("building", ""), (r.get("street") or "").title()]
    loc = ", ".join(p for p in [" ".join(p for p in parts if p), r.get("boro"), r.get("zipcode")] if p)
    return loc


def search(args):
    clauses = []
    if args.name:
        clauses.append(f"upper(dba) like {soql_str('%' + args.name.upper() + '%')}")
    if args.zip:
        clauses.append(f"zipcode = {soql_str(args.zip)}")
    if args.boro:
        if args.boro.lower() not in BOROS:
            sys.exit(f"--boro must be one of: {', '.join(sorted(BOROS))}")
        clauses.append(f"upper(boro) = {soql_str(args.boro.upper())}")
    if args.street:
        clauses.append(f"upper(street) like {soql_str('%' + args.street.upper() + '%')}")
    if args.cuisine:
        clauses.append(f"upper(cuisine_description) like {soql_str('%' + args.cuisine.upper() + '%')}")
    if not clauses:
        sys.exit("Give at least one of --name, --zip, --boro, --street, --cuisine")

    group = "camis,dba,building,street,boro,zipcode,cuisine_description"
    rows = fetch({
        "$select": group + ",max(inspection_date) as last_inspection",
        "$where": " AND ".join(clauses),
        "$group": group,
        "$order": "last_inspection DESC",
        "$limit": args.limit,
    })
    if args.json:
        print(json.dumps(rows, indent=2))
        return
    if not rows:
        print("No matching restaurants.")
        return
    print(f"{len(rows)} match(es){' (limit reached)' if len(rows) == args.limit else ''}:\n")
    for r in rows:
        last = day(r.get("last_inspection"))
        last = "not yet inspected" if last.startswith("1900") else f"last inspected {last}"
        print(f"- {r.get('dba')} | CAMIS {r.get('camis')} | {address(r)} | "
              f"{r.get('cuisine_description', '')} | {last}")


def history(args):
    rows = fetch({
        "$where": f"camis = {soql_str(args.camis)}",
        "$order": "inspection_date DESC",
        "$limit": 2000,
    })
    if not rows:
        print(f"No records for CAMIS {args.camis}.")
        return

    inspections = OrderedDict()
    for r in rows:
        key = (day(r.get("inspection_date")), r.get("inspection_type", ""))
        insp = inspections.setdefault(key, {
            "date": key[0],
            "type": key[1],
            "action": r.get("action"),
            "score": r.get("score"),
            "grade": r.get("grade"),
            "grade_date": day(r.get("grade_date")),
            "violations": [],
        })
        insp["score"] = insp["score"] or r.get("score")
        insp["grade"] = insp["grade"] or r.get("grade")
        if r.get("violation_code"):
            insp["violations"].append({
                "code": r.get("violation_code"),
                "critical": r.get("critical_flag"),
                "description": r.get("violation_description"),
            })
    selected = list(inspections.values())[: args.inspections]

    if args.json:
        print(json.dumps({"restaurant": {k: rows[0].get(k) for k in (
            "camis", "dba", "building", "street", "boro", "zipcode", "phone", "cuisine_description")},
            "inspections": selected}, indent=2))
        return

    r = rows[0]
    print(f"{r.get('dba')} (CAMIS {r.get('camis')})")
    print(f"{address(r)} | {r.get('cuisine_description', '')} | phone {r.get('phone', 'n/a')}")
    graded = next((i for i in inspections.values() if i["grade"] in ("A", "B", "C")), None)
    if graded:
        print(f"Current letter grade: {graded['grade']} (graded {graded['grade_date'] or graded['date']})")
    print(f"\nShowing {len(selected)} of {len(inspections)} inspections:\n")
    for i in selected:
        if i["date"].startswith("1900"):
            print("- Not yet inspected (new establishment)")
            continue
        print(f"- {i['date']} | {i['type'] or 'n/a'} | score {i['score'] or 'n/a'} | "
              f"grade {i['grade'] or '-'}")
        if i["action"]:
            print(f"    Action: {i['action']}")
        for v in i["violations"]:
            flag = "CRITICAL" if (v["critical"] or "").lower() == "critical" else "minor"
            print(f"    [{v['code']} {flag}] {v['description']}")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="find restaurants and their CAMIS ids")
    s.add_argument("--name")
    s.add_argument("--zip")
    s.add_argument("--boro")
    s.add_argument("--street")
    s.add_argument("--cuisine")
    s.add_argument("--limit", type=int, default=25)
    s.add_argument("--json", action="store_true")
    s.set_defaults(func=search)

    h = sub.add_parser("history", help="inspection history for one CAMIS id")
    h.add_argument("--camis", required=True)
    h.add_argument("--inspections", type=int, default=5, help="how many recent inspections to show")
    h.add_argument("--json", action="store_true")
    h.set_defaults(func=history)

    args = p.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
