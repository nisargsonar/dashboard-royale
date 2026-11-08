Luck or Leak: Check Before You Replace
TAMU Datathon 2026 - Dashboard Royale

LIVE DASHBOARD (no install needed)
  https://nisargsonar.github.io/dashboard-royale/dashboard/
  Backup: https://luck-or-leak.vercel.app (blocked on some campus networks)
Claims and Evidence appendix + AI-use disclosure:
  https://nisargsonar.github.io/dashboard-royale/dashboard/appendix.html
Code: https://github.com/nisargsonar/dashboard-royale
Video: https://youtu.be/LdU8WF-UtjI

OPEN FROM THIS ZIP
  1. Unzip.
  2. Open dashboard/index.html in Chrome, Edge, Firefox or Safari.
     (Internet is needed for the chart library and fonts.)
  3. dashboard/appendix.html is the Claims and Evidence appendix.

CONTENTS
  dashboard/                  the interactive dashboard (index.html, story.js, story.css, data.js, appendix.html)
  analysis/build_dashboard_data.py   all data transformation steps (Python + DuckDB)
  submission/writeup.md       400-word write-up
  submission/video-script.md  video script
  submission/images/          screenshots

REBUILD THE DATA
  Put the challenge data/ folder next to analysis/, then:
  python -m pip install duckdb pandas numpy
  python analysis/build_dashboard_data.py
  This rewrites dashboard/data.js.

The Gilded Ace is a fictional casino with synthetic data.
