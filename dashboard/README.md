# Luck or Leak

A dashboard for the TAMU Datathon 2026 Dashboard Royale challenge, about the fictional Gilded Ace casino.

A static page: `index.html`, `story.js`, `story.css` and `data.js` (generated). No build step and no server.

## Open it
Double-click `index.html`, or serve the folder (`python -m http.server` from this folder, then open http://localhost:8000).
Charts load Chart.js from cdnjs, so an internet connection is needed.

## Story intro and two views
- **Opening the page always starts with the story:** a 7-scene animated story explains the problem (casino → manager's plan → luck, location or leak → three clues on the real floor map → our advice). Then it asks how the viewer likes their numbers.
- **Simple view** (management): plain words, analogies, fewer columns.
- **Analyst view** (data/stats): formulas, luck z-scores, hit-rate z, a z-histogram vs. the normal curve, forecast error by weekday, and the full method.
- **Switch any time** with the Simple / Analyst toggle in the header. "▶ Story" replays the intro. The view choice is remembered in the browser, but the story still opens first each time.
- **Deep links skip the story** (e.g. `index.html#plan`). To force it, add `?story` or jump to a scene with `?scene=4`.
- Story numbers come from `data.js` through `window.GA` (see `story.js`). Animations switch off when the viewer's system asks for reduced motion.

## Rebuild the data
From the repository root:

```sh
python -m pip install duckdb pandas numpy
python analysis/build_dashboard_data.py
```

This reads the release tables in `data/` and rewrites `dashboard/data.js` (~1 MB). Every number on the page comes from that script.

## Publish (GitHub Pages)
Settings → Pages → deploy from branch `main`, folder `/ (root)`. The dashboard is then at
`https://<user>.github.io/<repo>/dashboard/`.

## Layout
| Section | Question | Main tables |
| --- | --- | --- |
| Overview | KPIs, actual vs expected win | machine_day |
| 1 · Machines | Luck z-score, bottom-10 verdicts, machine table | machine_day, game_math |
| 2 · Floor & demand | Floor map, zones, Back Forty traffic, events | floor_locations, zone_traffic_hourly, events |
| 3 · Downtime | Lost expected win, faults, tech waits | machine_hour, operations, shift_roster |
| 4 · Players | Net results, concentration, guest groups | player_period |
| 5 · Comps | May 1 redemption-rate cut, comp cost | loyalty_ledger, player_period |
| Forecast | Weekday/event model vs constant baseline (Jan–Apr train, May–Jun test) | property_day, events |
| 6 · Plan | Three priced actions + rejected options | action_catalog + evidence above |

Filters (period, zone, bank, guest group) apply to every section except the forecast (a fixed holdout) and the plan (July horizon).
