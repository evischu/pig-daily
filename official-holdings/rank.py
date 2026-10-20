"""三個排行榜、集中持股統計，以及與前一日快照的名次比較。"""
import json
from collections import defaultdict

from config import COMMITTEE_INDUSTRIES, CONCENTRATION_MIN, LOT, SNAPSHOTS, TOP_N

BOARDS = {
    "value": ("估計市值", lambda h: h["value"]),
    "lots": ("持有張數", lambda h: h["lots"]),
    "stake": ("股權比例", lambda h: h["stake"] or 0),
}


def enrich(holdings, market):
    out, missing = [], set()
    for h in holdings:
        q = market.get(h["code"])
        if not q:
            missing.add(h["code"])
            continue
        issued = q.get("issued")
        out.append({
            **h,
            "name": q["name"], "market": q.get("market", ""),
            "industry": q.get("industry") or "其他",
            "close": q["close"], "prev_close": q.get("prev_close") or q["close"],
            "lots": h["shares"] / LOT,
            "value": h["shares"] * q["close"],
            "stake": h["shares"] / issued * 100 if issued else None,
            "related": q.get("industry") in COMMITTEE_INDUSTRIES.get(h["committee"], ()),
        })
    return out, sorted(missing)


def concentration(rows):
    by_code = defaultdict(list)
    for r in rows:
        by_code[r["code"]].append(r)
    out = []
    for code, rs in by_code.items():
        if len(rs) < CONCENTRATION_MIN:
            continue
        rs.sort(key=lambda r: -r["value"])
        out.append({
            "code": code, "name": rs[0]["name"], "industry": rs[0]["industry"],
            "close": rs[0]["close"], "prev_close": rs[0]["prev_close"],
            "holders": len(rs),
            "lots": sum(r["lots"] for r in rs),
            "value": sum(r["value"] for r in rs),
            "related": sum(r["related"] for r in rs),
            "officials": [{"official": r["official"], "committee": r["committee"],
                           "lots": r["lots"], "related": r["related"]} for r in rs],
        })
    out.sort(key=lambda c: (-c["holders"], -c["value"]))
    return out


def key(r):
    return f'{r["official"]}|{r["code"]}'


def load_prev_snapshot(date):
    prev = sorted(p for p in SNAPSHOTS.glob("*.json") if p.stem < date)
    if not prev:
        return None, None
    return prev[-1].stem, json.load(open(prev[-1], encoding="utf-8"))


def build(rows, date):
    holders = {c["code"]: c["holders"] for c in concentration(rows)}
    prev_date, prev = load_prev_snapshot(date)
    boards, snapshot = {}, {}
    for bid, (label, metric) in BOARDS.items():
        top = sorted(rows, key=lambda r: -metric(r))[:TOP_N]
        prev_rank = (prev or {}).get(bid, {})
        entries = []
        for i, r in enumerate(top, 1):
            p = prev_rank.get(key(r))
            entries.append({**r, "rank": i, "prev_rank": p,
                            "is_new": prev is not None and p is None,
                            "co_holders": holders.get(r["code"], 0)})
        today_keys = {key(e) for e in entries}
        by_key = {key(r): r for r in rows}
        dropped = [{**by_key[k], "prev_rank": pr} if k in by_key else
                   {"official": k.split("|")[0], "code": k.split("|")[1], "name": "", "prev_rank": pr}
                   for k, pr in prev_rank.items() if k not in today_keys]
        dropped.sort(key=lambda d: d["prev_rank"])
        boards[bid] = {"label": label, "entries": entries, "dropped": dropped}
        snapshot[bid] = {key(e): e["rank"] for e in entries}
    return boards, snapshot, prev_date


def save_snapshot(date, snapshot):
    SNAPSHOTS.mkdir(parents=True, exist_ok=True)
    json.dump(snapshot, open(SNAPSHOTS / f"{date}.json", "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
