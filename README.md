# nyc-restaurant-inspections

A Claude skill that looks up NYC restaurant health inspection results (letter grades,
scores, violations, closures) live from the city's
[DOHMH Restaurant Inspection Results](https://data.cityofnewyork.us/Health/DOHMH-New-York-City-Restaurant-Inspection-Results/43nn-pn8j)
dataset on NYC Open Data. No API key or third-party service needed.

## Install

- **Claude Code:** copy this folder to `~/.claude/skills/nyc-restaurant-inspections/`.
- **claude.ai / Claude Desktop / mobile:** zip this folder and upload it under
  Settings → Customize → Skills. Enable code execution and add `data.cityofnewyork.us`
  under Settings → Capabilities → Allowed websites.

## Standalone use

```bash
python3 scripts/inspections.py search --name balthazar --boro Manhattan
python3 scripts/inspections.py history --camis 40574871 --inspections 5
```
