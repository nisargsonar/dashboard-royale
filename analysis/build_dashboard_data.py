"""Build dashboard/data.js from the release tables.

Run from the repository root:
    python analysis/build_dashboard_data.py

Every number on the dashboard comes from this script. Money is in dollars.
Ratios are always computed from sums (never averages of daily ratios).
Off-floor machine-days (active = false) are excluded everywhere.
"""
import json
import os

import duckdb
import numpy as np
import pandas as pd

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, "data")
OUT = os.path.join(ROOT, "dashboard", "data.js")

TABLES = {
    "md": "2_machine_decision/machine_day",
    "gm": "2_machine_decision/game_math",
    "mach": "2_machine_decision/machines",
    "loc": "2_machine_decision/floor_locations",
    "ww": "2_machine_decision/floor_walkways",
    "ops": "2_machine_decision/operations",
    "cal": "2_machine_decision/calendar_day",
    "ac": "2_machine_decision/action_catalog",
    "pdv": "1_prepared_views/prepared_daily_view",
    "pd": "1_prepared_views/property_day",
    "pp": "1_prepared_views/player_period",
    "led": "3_guests/loyalty_ledger",
    "ev": "4_context/events",
    "zt": "4_context/zone_traffic_hourly",
    "city": "4_context/real_sources/city_visitation_monthly",
    "bstate": "4_context/real_sources/benchmark_state_monthly",
    "mh": "5_optional/machine_hour",
    "roster": "5_optional/shift_roster",
}

con = duckdb.connect()
for name, path in TABLES.items():
    con.sql(f"CREATE VIEW {name} AS SELECT * FROM '{DATA}/{path}.parquet'")


def df(sql):
    return con.sql(sql).df()


def cols(frame, digits=None):
    """Column-oriented dict (smaller than row records)."""
    out = {}
    for c in frame.columns:
        s = frame[c]
        if pd.api.types.is_datetime64_any_dtype(s):
            out[c] = [None if pd.isna(v) else v.strftime("%Y-%m-%d") for v in s]
        elif pd.api.types.is_float_dtype(s):
            d = (digits or {}).get(c, 2)
            out[c] = [None if pd.isna(v) else round(float(v), d) for v in s]
        elif pd.api.types.is_integer_dtype(s):
            out[c] = [int(v) for v in s]
        else:
            out[c] = [None if (v is None or (isinstance(v, float) and np.isnan(v))) else (str(v) if not isinstance(v, (bool, np.bool_)) else bool(v)) for v in s]
    return out


# ---------------------------------------------------------------- lookups
con.sql("""
CREATE TABLE slot AS
SELECT s.location_id, s.bank_id, s.zone_id, z.name AS zone_name
FROM loc s JOIN loc z ON z.location_id = s.zone_id AND z.node_type = 'zone'
WHERE s.node_type = 'slot'
""")

# Expected coin-in rate per machine x local hour, used to price downtime.
con.sql("""
CREATE TABLE theo_hold AS
SELECT machine_id, SUM(theo_cents) / SUM(coin_in_cents) AS th
FROM md WHERE active GROUP BY 1
""")
con.sql("""
CREATE TABLE rate AS
SELECT machine_id, local_hour,
       SUM(coin_in_cents) / NULLIF(SUM(available_seconds), 0) AS cin_per_s
FROM mh WHERE active GROUP BY 1, 2
""")
con.sql("""
CREATE TABLE lost_day AS
SELECT h.machine_id, h.gaming_date,
       SUM(3600 - h.available_seconds) / 3600.0 AS down_h,
       SUM((3600 - h.available_seconds) * COALESCE(r.cin_per_s, 0) * t.th) / 100.0 AS lost_theo
FROM mh h JOIN rate r USING (machine_id, local_hour) JOIN theo_hold t USING (machine_id)
WHERE h.active AND h.available_seconds < 3600
GROUP BY 1, 2
""")

# Machine-day enriched with bank/zone (location at day start) and game math.
con.sql("""
CREATE TABLE mdx AS
SELECT md.*, s.bank_id, s.zone_id, s.zone_name, strftime(md.gaming_date, '%Y-%m') AS month,
       gm.payout_multiplier_variance AS pvar, gm.hit_probability AS hitp,
       COALESCE(l.down_h, 0) AS down_h, COALESCE(l.lost_theo, 0) AS lost_theo,
       f.faults
FROM md
JOIN gm USING (config_id)
JOIN slot s USING (location_id)
LEFT JOIN lost_day l USING (machine_id, gaming_date)
LEFT JOIN (SELECT machine_id, gaming_date, faults_opened AS faults FROM pdv) f USING (machine_id, gaming_date)
WHERE md.active
""")

# ---------------------------------------------------------------- bank x day
bank_day = df("""
SELECT gaming_date AS d, bank_id AS b,
       SUM(coin_in_cents) / 100.0 AS cin,
       SUM(house_win_cents) / 100.0 AS hw,
       SUM(theo_cents) / 100.0 AS theo,
       SUM(available_seconds) / 3600.0 AS av,
       SUM(scheduled_seconds) / 3600.0 AS sc,
       SUM(occupied_seconds) / 3600.0 AS oc,
       SUM(faults) AS f,
       SUM(down_h) AS dh,
       SUM(lost_theo) AS lt
FROM mdx GROUP BY 1, 2 ORDER BY 1, 2
""")
bank_day["f"] = bank_day["f"].fillna(0).astype(int)

banks = df("""
SELECT b.location_id AS bank, b.zone_id AS zone, z.name AS zone_name, b.x_m AS x, b.y_m AS y, b.capacity AS cap
FROM loc b JOIN loc z ON z.location_id = b.zone_id
WHERE b.node_type = 'bank' ORDER BY 1
""")
zones = df("""
SELECT location_id AS zone, name, x_m AS x, y_m AS y FROM loc WHERE node_type = 'zone' ORDER BY name
""")

# ---------------------------------------------------------------- machine x month x bank
mm = df("""
SELECT machine_id AS m, month AS mo, bank_id AS b,
       COUNT(*) AS days,
       SUM(coin_in_cents) / 100.0 AS cin,
       SUM(house_win_cents) / 100.0 AS hw,
       SUM(theo_cents) / 100.0 AS theo,
       SUM(sum_bet_squared * pvar) / 10000.0 AS var,
       SUM(available_seconds) / 3600.0 AS av,
       SUM(scheduled_seconds) / 3600.0 AS sc,
       SUM(occupied_seconds) / 3600.0 AS oc,
       SUM(paid_spins) AS sp,
       SUM(payout_positive_spins) AS ps,
       SUM(lost_theo) AS lt
FROM mdx GROUP BY 1, 2, 3 ORDER BY 1, 2, 3
""")
machines = df("""
SELECT m.machine_id AS m, m.manufacturer AS mfr, m.theme, gm.volatility_class AS vol,
       gm.configured_rtp::DOUBLE AS rtp, gm.hit_probability::DOUBLE AS hitp,
       gm.payout_multiplier_variance::DOUBLE AS pvar, gm.max_multiplier::DOUBLE AS maxm,
       m.install_date, m.retire_date, m.lease_class AS lease
FROM mach m
JOIN (SELECT machine_id, arg_max(config_id, gaming_date) AS config_id FROM md WHERE active GROUP BY 1) c
  ON c.machine_id = m.machine_id
JOIN gm ON gm.config_id = c.config_id
ORDER BY 1
""")

# The manager's list: 10 lowest total house win, Jan 1 - Jun 30.
bottom10 = df("""
SELECT machine_id FROM md WHERE active GROUP BY 1 ORDER BY SUM(house_win_cents) LIMIT 10
""")["machine_id"].tolist()

# ---------------------------------------------------------------- days, events, context
days = df("""
SELECT p.gaming_date AS d, p.local_weekday AS wd, p.events_active AS ev,
       p.pos_cash_usd::DOUBLE AS pos, p.comp_cost_usd::DOUBLE AS comp,
       p.coin_in_usd::DOUBLE AS cin
FROM pd p ORDER BY 1
""")
events = df("""
SELECT event_id AS id, name, event_type AS type, start_date AS s, end_date AS e, announced_date AS ann, local_scope AS scope
FROM ev ORDER BY start_date
""")
walkways = df("""
SELECT walkway_id AS id, zone_a, zone_b,
       (closed_from_utc AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles')::DATE AS s,
       (closed_to_utc AT TIME ZONE 'UTC' AT TIME ZONE 'America/Los_Angeles')::DATE AS e,
       closure_reason AS reason, length_m AS len
FROM ww ORDER BY 1
""")

# Zone traffic: entries per working sensor-day (counts crossings, not people;
# offline hours are excluded rather than treated as zero).
zone_day = df("""
SELECT c.gaming_date AS d, z.zone_id AS z,
       SUM(z.entries_count) AS ent,
       SUM(z.coverage_minutes) AS cov
FROM zt z JOIN cal c ON z.hour_start_utc >= c.gaming_day_start_utc AND z.hour_start_utc < c.gaming_day_end_utc
WHERE z.entries_count IS NOT NULL
GROUP BY 1, 2 ORDER BY 1, 2
""")

city = df("""
SELECT month AS mo, visitor_volume::DOUBLE AS visitors, visitor_yoy_ratio::DOUBLE AS yoy,
       convention_attendance::DOUBLE AS conv, hotel_occupancy_ratio::DOUBLE AS occ
FROM city ORDER BY 1
""")
bench = df("""
SELECT month AS mo, handle_usd::DOUBLE AS handle, agr_usd::DOUBLE AS agr, agr_usd / handle_usd AS hold
FROM bstate ORDER BY 1
""")

# ---------------------------------------------------------------- downtime
con.sql("""
CREATE TABLE faults AS
SELECT o.operation_id, o.machine_id, m.manufacturer AS mfr, s.zone_id AS zone, s.bank_id AS bank,
       c.gaming_date, strftime(c.gaming_date, '%Y-%m') AS month,
       hour(o.opened_at_local) AS hr,
       CASE WHEN hour(o.opened_at_local) BETWEEN 6 AND 13 THEN 'day'
            WHEN hour(o.opened_at_local) BETWEEN 14 AND 21 THEN 'swing' ELSE 'grave' END AS shift,
       epoch(o.work_started_at_utc - o.opened_at_utc) / 3600.0 AS wait_h,
       epoch(o.available_at_utc - o.work_started_at_utc) / 3600.0 AS fix_h,
       epoch(o.available_at_utc - o.opened_at_utc) / 3600.0 AS down_h,
       o.direct_cost_cents / 100.0 AS cost
FROM ops o
JOIN mach m USING (machine_id)
JOIN cal c ON o.opened_at_utc >= c.gaming_day_start_utc AND o.opened_at_utc < c.gaming_day_end_utc
LEFT JOIN slot s ON s.location_id = o.location_id
WHERE o.event_type = 'fault_repair'
""")
techs = df("""
SELECT gaming_date, shift, SUM(actual_headcount) AS act, SUM(planned_headcount) AS pl
FROM roster WHERE role = 'slot_tech' GROUP BY 1, 2
""")
con.register("techs_df", techs)
fault_rows = df("""
SELECT f.month AS mo, f.mfr, f.zone AS z, f.bank AS b, f.shift, COALESCE(t.act, 0) AS techs,
       COUNT(*) AS n, SUM(wait_h) AS wait, SUM(fix_h) AS fix, SUM(f.down_h) AS dh
FROM faults f LEFT JOIN techs_df t ON t.gaming_date = f.gaming_date AND t.shift = f.shift
GROUP BY ALL ORDER BY 1
""")
tech_month = df("""
SELECT strftime(gaming_date, '%Y-%m') AS mo, shift,
       AVG(act) AS act, AVG(pl) AS pl, SUM(CASE WHEN act = 0 THEN 1 ELSE 0 END) AS zero_days
FROM techs_df GROUP BY 1, 2 ORDER BY 1, 2
""")
shift_value = df("""
SELECT CASE WHEN local_hour BETWEEN 6 AND 13 THEN 'day' WHEN local_hour BETWEEN 14 AND 21 THEN 'swing' ELSE 'grave' END AS shift,
       SUM(coin_in_cents * t.th) / 100.0 / (SUM(available_seconds) / 3600.0) AS theo_per_av_h
FROM mh JOIN theo_hold t USING (machine_id) WHERE active GROUP BY 1
""")

# ---------------------------------------------------------------- players
pp = df("""
SELECT player_id, period_month AS mo, home_region AS region, opening_tier AS tier,
       COALESCE(age_band, 'Unknown') AS age,
       tracked_coin_in_usd::DOUBLE AS cin, tracked_payout_usd::DOUBLE AS payout,
       tracked_net_usd::DOUBLE AS net, theo_usd::DOUBLE AS theo,
       comp_cost_usd::DOUBLE AS comp, comp_face_value_usd::DOUBLE AS face,
       tracked_contribution_usd::DOUBLE AS contrib, observed_visits AS visits,
       points_earned AS pe, points_redeemed AS pr, comps_redeemed AS cr
FROM pp
""")
player_groups = (
    pp.groupby(["mo", "region", "tier", "age"])
    .agg(pm=("player_id", "size"), cin=("cin", "sum"), payout=("payout", "sum"), net=("net", "sum"),
         theo=("theo", "sum"), comp=("comp", "sum"), face=("face", "sum"), contrib=("contrib", "sum"),
         visits=("visits", "sum"), pe=("pe", "sum"), pr=("pr", "sum"), cr=("cr", "sum"))
    .reset_index()
)

# Concentration needs player-level sums, so precompute it for every
# contiguous month range x guest group (the dashboard's filter options).
months = sorted(pp["mo"].unique())
groups = [("all", "All")]
for dim in ["region", "tier", "age"]:
    for v in sorted(pp[dim].unique()):
        groups.append((dim, v))
conc = {}
for i in range(len(months)):
    for j in range(i, len(months)):
        sl = pp[(pp["mo"] >= months[i]) & (pp["mo"] <= months[j])]
        per = sl.groupby("player_id").agg(net=("net", "sum"), cin=("cin", "sum"),
                                          region=("region", "first"), tier=("tier", "first"), age=("age", "first"))
        per = per[per["cin"] > 0]
        for dim, v in groups:
            g = per if dim == "all" else per[per[dim] == v]
            if len(g) == 0:
                continue
            nets = np.sort(g["net"].to_numpy())  # most negative (biggest losers) first
            n = len(nets)
            losses = -nets[nets < 0].sum()
            cut = [int(np.ceil(n * 0.01)), int(np.ceil(n * 0.10)), int(np.ceil(n * 0.50))]
            parts = [nets[:cut[0]].sum(), nets[cut[0]:cut[1]].sum(), nets[cut[1]:cut[2]].sum(), nets[cut[2]:].sum()]
            conc[f"{months[i]}|{months[j]}|{dim}|{v}"] = {
                "n": n,
                "ahead": round(float((nets > 0).mean()), 4),
                "losses": round(float(losses), 0),
                "net": round(float(nets.sum()), 0),
                "parts": [round(float(p), 0) for p in parts],
            }

# ---------------------------------------------------------------- comps
redeem_week = df("""
SELECT date_trunc('week', event_at_utc)::DATE AS wk, tier_before AS tier,
       SUM(-points_delta) * 100.0 / SUM(face_value_cents) AS pts_per_usd,
       SUM(economic_cost_cents) / 100.0 AS cost, COUNT(*) AS n
FROM led WHERE event_type = 'redeem' AND event_at_utc < '2025-06-30'
GROUP BY 1, 2 ORDER BY 1, 2
""")
change = df("""
SELECT
  SUM(economic_cost_cents) FILTER (WHERE event_at_utc <  '2025-05-01 13:00') / SUM(-points_delta) FILTER (WHERE event_at_utc <  '2025-05-01 13:00') / 100.0 AS cost_per_pt_before,
  SUM(economic_cost_cents) FILTER (WHERE event_at_utc >= '2025-05-02 13:00') / SUM(-points_delta) FILTER (WHERE event_at_utc >= '2025-05-02 13:00') / 100.0 AS cost_per_pt_after
FROM led WHERE event_type = 'redeem'
""").iloc[0]
points = df("""
SELECT SUM(points_delta) FILTER (WHERE event_type = 'award') AS earned,
       -SUM(points_delta) FILTER (WHERE event_type = 'redeem') AS redeemed
FROM led
""").iloc[0]

# ---------------------------------------------------------------- forecast (time-based holdout)
# Four models, all fitted only on data before the forecast date:
#   p_const : constant training mean (baseline)
#   p_dow   : mean for that weekday
#   p_dowev : weekday mean on non-event days x event multiplier
#   p_reg   : linear regression (OLS) on weekday dummies + event flag + linear trend
# Events count as inputs only if announced on or before the forecast date (no leakage).
# No lagged actuals are used, because a frozen multi-day forecast cannot see test-period results.
fc = days[["d", "wd", "ev", "cin"]].copy()
fc["d"] = pd.to_datetime(fc["d"])
fc["t"] = (fc["d"] - fc["d"].min()).dt.days.astype(float)
WD = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
MODELS = ["p_const", "p_dow", "p_dowev", "p_reg"]


def event_flags(asof):
    dates = set()
    for _, e in events.iterrows():
        if pd.Timestamp(e["ann"]) > asof:
            continue
        for d in pd.date_range(e["s"], e["e"]):
            dates.add(d)
    return fc["d"].isin(dates)


def design(frame, is_ev):
    X = [np.ones(len(frame))]
    X += [(frame["wd"] == w).astype(float).to_numpy() for w in WD[1:]]
    X += [is_ev.astype(float).to_numpy(), frame["t"].to_numpy()]
    return np.column_stack(X)


def fit_predict(train_end, test_start, test_end):
    """Fit on days <= train_end, predict days in [test_start, test_end]."""
    asof = pd.Timestamp(train_end)
    is_ev = event_flags(asof)
    tr = (fc["d"] <= asof).to_numpy()
    te = ((fc["d"] >= pd.Timestamp(test_start)) & (fc["d"] <= pd.Timestamp(test_end))).to_numpy()
    T, E = fc[tr], is_ev[tr]
    out = pd.DataFrame(index=fc.index[te])
    out["p_const"] = T["cin"].mean()
    out["p_dow"] = fc.loc[te, "wd"].map(T.groupby("wd")["cin"].mean())
    dow_ne = T[~E].groupby("wd")["cin"].mean()
    ev_rows = T[E]
    mult = float((ev_rows["cin"] / ev_rows["wd"].map(dow_ne)).mean()) if len(ev_rows) else 1.0
    out["p_dowev"] = fc.loc[te, "wd"].map(dow_ne) * np.where(is_ev[te], mult, 1.0)
    beta, *_ = np.linalg.lstsq(design(T, E), T["cin"].to_numpy(), rcond=None)
    out["p_reg"] = design(fc[te], is_ev[te]) @ beta
    return out, mult, is_ev, beta


# main holdout: forecast frozen on Apr 30, tested on May 1 - Jun 30
pred, ev_mult, is_ev_main, beta_main = fit_predict("2025-04-30", "2025-05-01", "2025-06-30")
for k in MODELS:
    fc[k] = np.nan
    fc.loc[pred.index, k] = pred[k]
fc["is_ev"] = is_ev_main
fc["split"] = np.where(fc["d"] >= "2025-05-01", "test", "train")
test = fc[fc["split"] == "test"]
mae = {k: float(np.mean(np.abs(test["cin"] - test[k]))) for k in MODELS}
bias = {k: float(np.mean(test[k] - test["cin"])) for k in MODELS}
# The plots show baseline predictions over the test period only; fill train rows for constant-style plotting
forecast = fc[["d", "cin", "p_const", "p_dow", "p_dowev", "p_reg", "split", "is_ev"]]

# rolling-origin backtest: expanding window, one month ahead
backtest = []
for tm in ["2025-03", "2025-04", "2025-05", "2025-06"]:
    start = pd.Timestamp(tm + "-01")
    end = start + pd.offsets.MonthEnd(0)
    train_end = start - pd.Timedelta(days=1)
    p_, _, _, _ = fit_predict(train_end, start, end)
    y = fc.loc[p_.index, "cin"]
    backtest.append({"test_month": tm, "train_end": train_end.strftime("%Y-%m-%d"), "days": int(len(y)),
                     **{k: float(np.mean(np.abs(y - p_[k]))) for k in MODELS}})
# Model choice is made on the two folds that end before the freeze date (Mar, Apr), never on May-Jun.
pre = [b for b in backtest if b["test_month"] < "2025-05"]
selection = {k: float(np.mean([b[k] for b in pre])) for k in MODELS}
chosen = min(selection, key=selection.get)
print("backtest", [{k: (round(v) if isinstance(v, float) else v) for k, v in b.items()} for b in backtest])
print("selection (Mar-Apr folds)", {k: round(v) for k, v in selection.items()}, "->", chosen)

# ---------------------------------------------------------------- evidence for the action plan
ev_num = {}
m1158 = df("""
SELECT SUM(theo_cents - house_win_cents) / 100.0 AS short, COUNT(*) AS days,
       SUM(payout_positive_spins)::DOUBLE / SUM(paid_spins) AS hit, any_value(gm.hit_probability)::DOUBLE AS spec,
       SUM(house_win_cents)::DOUBLE / SUM(coin_in_cents) AS hold, any_value(1 - gm.configured_rtp)::DOUBLE AS spec_hold
FROM md JOIN gm USING (config_id) WHERE machine_id = 'M-1158' AND active
""").iloc[0]
ev_num["m1158"] = {k: float(v) for k, v in m1158.items()}
b40 = df("""
SELECT CASE WHEN gaming_date < '2025-03-03' THEN 'pre' WHEN gaming_date < '2025-04-07' THEN 'closed' ELSE 'post' END AS per,
       SUM(theo_cents) / 100.0 / (SUM(available_seconds) / 3600.0) AS theo_per_av_h,
       SUM(theo_cents) / 100.0 / COUNT(DISTINCT gaming_date) AS theo_per_day
FROM mdx WHERE zone_id = 'Z-B40' GROUP BY 1
""").set_index("per")
rest = df("""
SELECT CASE WHEN gaming_date < '2025-03-03' THEN 'pre' WHEN gaming_date < '2025-04-07' THEN 'closed' ELSE 'post' END AS per,
       SUM(theo_cents) / 100.0 / (SUM(available_seconds) / 3600.0) AS theo_per_av_h
FROM mdx WHERE zone_id <> 'Z-B40' GROUP BY 1
""").set_index("per")
ev_num["b40"] = {
    "pre": float(b40.loc["pre", "theo_per_av_h"]), "closed": float(b40.loc["closed", "theo_per_av_h"]),
    "post": float(b40.loc["post", "theo_per_av_h"]), "post_theo_per_day": float(b40.loc["post", "theo_per_day"]),
    "rest_pre": float(rest.loc["pre", "theo_per_av_h"]), "rest_post": float(rest.loc["post", "theo_per_av_h"]),
}
rl = df("""
SELECT m.manufacturer AS mfr, SUM(lost_theo) / 6 AS lost_per_month, COUNT(DISTINCT machine_id) AS n
FROM mdx JOIN mach m USING (machine_id) GROUP BY 1
""")
ev_num["lost_by_mfr_month"] = dict(zip(rl["mfr"], rl["lost_per_month"].round(0)))
ev_num["theo_hold_floor"] = float(df("SELECT SUM(theo_cents)/SUM(coin_in_cents) AS t FROM mdx").iloc[0]["t"])
ev_num["shift_value"] = dict(zip(shift_value["shift"], shift_value["theo_per_av_h"].round(2)))
gw = df("""
SELECT f.shift, COALESCE(t.act,0) AS techs, COUNT(*) AS n, AVG(wait_h) AS wait
FROM faults f LEFT JOIN techs_df t ON t.gaming_date = f.gaming_date AND t.shift = f.shift GROUP BY 1, 2
""")
ev_num["wait_by_shift_techs"] = gw.round(3).to_dict(orient="records")
ev_num["faults_per_month_by_shift"] = df("SELECT shift, COUNT(*)/6.0 AS n FROM faults GROUP BY 1").set_index("shift")["n"].round(1).to_dict()

# ---------------------------------------------------------------- write
actions = df("""
SELECT action_type_id AS id, name, unit, unit_cost_cents / 100.0 AS unit_cost,
       recurring_cost_cents_per_day / 100.0 AS per_day, lead_days, downtime_minutes, quantity_limit, incompatibility_group AS grp
FROM ac
""")

payload = {
    "meta": {
        "built_from": "data release 0.9.0-draft",
        "window": ["2025-01-01", "2025-06-30"],
        "months": months,
    },
    "banks": cols(banks, {"x": 1, "y": 1}),
    "zones": cols(zones, {"x": 1, "y": 1}),
    "bankDay": cols(bank_day, {"cin": 0, "hw": 0, "theo": 1, "av": 2, "sc": 2, "oc": 2, "dh": 2, "lt": 1}),
    "machines": cols(machines, {"rtp": 4, "hitp": 6, "pvar": 4, "maxm": 1}),
    "mm": cols(mm, {"cin": 0, "hw": 0, "theo": 1, "var": 0, "av": 2, "sc": 2, "oc": 2, "lt": 1}),
    "bottom10": bottom10,
    "days": cols(days, {"pos": 0, "comp": 0, "cin": 0}),
    "events": cols(events),
    "walkways": cols(walkways),
    "zoneDay": cols(zone_day),
    "city": cols(city, {"visitors": 0, "yoy": 4, "conv": 0, "occ": 4}),
    "bench": cols(bench, {"handle": 0, "agr": 0, "hold": 5}),
    "faults": cols(fault_rows, {"wait": 2, "fix": 2, "dh": 2}),
    "techMonth": cols(tech_month, {"act": 2, "pl": 2}),
    "players": cols(player_groups, {"cin": 0, "payout": 0, "net": 0, "theo": 0, "comp": 0, "face": 0, "contrib": 0}),
    "conc": conc,
    "redeemWeek": cols(redeem_week, {"pts_per_usd": 2, "cost": 0}),
    "comp": {
        "cost_per_pt_before": float(change["cost_per_pt_before"]),
        "cost_per_pt_after": float(change["cost_per_pt_after"]),
        "earned": int(points["earned"]),
        "redeemed": int(points["redeemed"]),
        "change_date": "2025-05-01",
    },
    "forecast": {
        "rows": cols(forecast, {"cin": 0, "p_const": 0, "p_dow": 0, "p_dowev": 0, "p_reg": 0}),
        "mae": mae, "bias": bias, "ev_mult": ev_mult,
        "backtest": backtest, "selection": selection, "chosen": chosen,
        "reg_coef": dict(zip(["intercept"] + ["wd_" + w for w in WD[1:]] + ["event", "trend_per_day"], [round(float(b), 1) for b in beta_main])),
        "train": ["2025-01-01", "2025-04-30"], "test": ["2025-05-01", "2025-06-30"],
    },
    "evidence": ev_num,
    "actions": cols(actions),
}

os.makedirs(os.path.dirname(OUT), exist_ok=True)
with open(OUT, "w") as fh:
    fh.write("// Generated by analysis/build_dashboard_data.py. Do not edit by hand.\n")
    fh.write("window.DATA = ")
    json.dump(payload, fh, separators=(",", ":"), default=lambda o: o.item() if hasattr(o, "item") else str(o))
    fh.write(";\n")
print(f"wrote {OUT} ({os.path.getsize(OUT) / 1e6:.2f} MB)")
print("MAE (May-Jun holdout)", {k: round(v) for k, v in mae.items()})
print("evidence", json.dumps(ev_num, default=str)[:1500])
