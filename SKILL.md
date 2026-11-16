---
name: nyc-restaurant-inspections
description: Look up NYC restaurant health inspection results — letter grades (A/B/C), scores, violations, critical violations, and DOHMH closures — straight from the city's official NYC Open Data dataset. Use this whenever someone asks about a New York City restaurant, bar, café, bakery, or food cart's health grade, inspection history, violations, rodent/roach findings, or whether it was shut down, or wants to find or compare restaurants by inspection record in a neighborhood, street, ZIP code, borough, or cuisine — even if they just say "is X clean?" or "should I eat at X in Brooklyn?".
---

# NYC Restaurant Inspections

Data source: DOHMH New York City Restaurant Inspection Results on NYC Open Data
(dataset `43nn-pn8j`, updated daily). It's a public API with no key, and queries go
straight to `data.cityofnewyork.us` — no third-party services.

## Workflow

The helper script is `scripts/inspections.py` in this skill's directory (Python 3,
standard library only). Run it with `python3 <skill-dir>/scripts/inspections.py`.

1. **Find the restaurant** to get its CAMIS id (the city's unique restaurant id):
   ```bash
   python3 scripts/inspections.py search --name "joe's pizza" --street carmine
   python3 scripts/inspections.py search --name balthazar --boro Manhattan
   python3 scripts/inspections.py search --zip 11211 --cuisine thai
   ```
   Filters combine with AND. `--name`, `--street`, `--cuisine` are case-insensitive
   substring matches; `--zip` and `--boro` are exact. Names are stored in caps with
   inconsistent punctuation (`JOE'S PIZZA` vs `JOES PIZZA`), so if nothing matches,
   retry with a shorter, distinctive fragment.

2. **If several match**, use the address or neighborhood the user gave to pick one.
   Chains have many locations, so if it's still ambiguous, list the candidates and ask
   rather than guessing — reporting the wrong location's violations would be misleading.

3. **Get the history**:
   ```bash
   python3 scripts/inspections.py history --camis 40574871 --inspections 5
   ```
   Add `--json` to either command for structured output (handy for comparisons).

## If the script can't reach the API

On claude.ai (web, desktop, mobile), code runs in a sandbox that may block outbound
network access. If the script fails with a network error, fetch the API URL directly
with whatever web-fetch tool is available instead, e.g.:

- Search: `https://data.cityofnewyork.us/resource/43nn-pn8j.json?$select=camis,dba,building,street,boro,zipcode,max(inspection_date)&$where=upper(dba) like '%25BALTHAZAR%25'&$group=camis,dba,building,street,boro,zipcode&$limit=25`
- History: `https://data.cityofnewyork.us/resource/43nn-pn8j.json?camis=40574871&$order=inspection_date DESC&$limit=200`

(URL-encode spaces and `%`.) Each row is one violation, so group rows by
`inspection_date` to reconstruct inspections. If neither works, tell the user the
sandbox needs network access to `data.cityofnewyork.us` (see Settings → Capabilities).

## Reading results

- **Score**: lower is better. A = 0–13, B = 14–27, C = 28+.
- **Grade codes**: `A`/`B`/`C` letter grades; `N` not yet graded; `Z` grade pending
  (being contested); `P` pending after reopening from a closure. An initial inspection
  scoring 14+ gets no grade until re-inspection, so the current grade is the most
  recent A/B/C.
- **Action** flags closures ("Establishment Closed by DOHMH", "re-opened"). Always
  mention a closure — it's the single most important fact for a diner.
- **Critical** violations are the ones most likely to cause foodborne illness; lead
  with them over minor ones.
- An inspection date of 1900-01-01 means a new establishment not yet inspected.

Lead your answer with the current grade and its date, then notable recent issues
(closures, critical violations, score trend). Don't list every violation unless asked —
the descriptions are long and most are minor.

## Other queries

For questions the script doesn't cover (e.g. "which Manhattan restaurants were closed
this month?"), query the API directly with SoQL (`$select`, `$where`, `$group`,
`$order`, `$limit`):
```bash
curl -s -G "https://data.cityofnewyork.us/resource/43nn-pn8j.json" \
  --data-urlencode "\$select=camis,dba,street,inspection_date,action" \
  --data-urlencode "\$where=boro='Manhattan' AND action like '%Closed by DOHMH%' AND inspection_date > '<date 30 days ago>'" \
  --data-urlencode "\$group=camis,dba,street,inspection_date,action"
```
Columns: camis, dba, boro, building, street, zipcode, phone, cuisine_description,
inspection_date, action, violation_code, violation_description, critical_flag, score,
grade, grade_date, record_date, inspection_type, latitude, longitude.
