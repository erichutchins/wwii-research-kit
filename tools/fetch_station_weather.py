"""Daily weather at a shore unit's stations: wartime observations where a weather station nearby
recorded them, and ERA5 reanalysis everywhere.

For each day a unit (or a part of it) was at a place, from records/<folder>/stations.csv (and
parts.csv, which names each part's parent and when it existed):

- **Observed** (NOAA's Integrated Surface Database, global-hourly): the nearest station within
  MAX_KM that has at least MIN_OBS observations that day. Many are the war's own airfield weather
  stations (Kobler Field on Saipan, Sopanitogha on Guadalcanal, Ie Shima off Okinawa). Daily
  maximum and minimum temperature, mean and highest wind, and how many observations reported
  precipitation falling (present-weather codes 50-99: drizzle, rain, showers, thunderstorms).
  The station and its distance from the place go in every row: a station 100 km away is the
  region's weather, not the camp's.
- **ERA5** (ECMWF reanalysis, 0.25°, via the Open-Meteo archive API): daily maximum and minimum
  temperature, precipitation and highest wind at the place itself. A model, not a report; on a
  small island the grid cell is mostly sea.

Days are local: ISD hours (UTC) are shifted by round(longitude / 15) hours, solar time rather
than the wartime zone; ERA5 days use Open-Meteo's `timezone=auto`. A row stays at a place until
the next row, less the days a transport (KM_PER_DAY) would need to reach the next place; days
in transit get no weather. Station lists and files are cached in sources/isd/, ERA5 in
sources/era5/.

  python3 tools/fetch_station_weather.py seabees      # -> records/seabees/weather.csv
"""
import csv
import io
import json
import math
import sys
import urllib.parse
import urllib.request
from datetime import date, datetime, timedelta

from records import CACHE, RECORDS, rel  # noqa: E402

ISD = CACHE / "isd"
ERA5 = CACHE / "era5"
HISTORY = "https://www.ncei.noaa.gov/pub/data/noaa/isd-history.csv"
FILES = "https://noaa-global-hourly-pds.s3.amazonaws.com/{year}/{id}.csv"
OPEN_METEO = "https://archive-api.open-meteo.com/v1/archive?"
MAX_KM = 150
MIN_OBS = 4
KM_PER_DAY = 550
KN_PER_MS = 1.943844


def km(a, b):
    la1, lo1, la2, lo2 = map(math.radians, (*a, *b))
    h = math.sin((la2 - la1) / 2) ** 2 + math.cos(la1) * math.cos(la2) * math.sin((lo2 - lo1) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


def get(url):
    with urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "wwii-research-kit"}), timeout=120) as r:
        return r.read()


def stations():
    path = ISD / "isd-history.csv"
    if not path.exists():
        ISD.mkdir(parents=True, exist_ok=True)
        path.write_bytes(get(HISTORY))
    out = []
    for r in csv.DictReader(path.open()):
        if r["LAT"] and r["LON"] and r["BEGIN"][:4] <= "1945" and r["END"][:4] >= "1939":
            out.append({"id": r["USAF"] + r["WBAN"], "name": r["STATION NAME"].strip(),
                        "at": (float(r["LAT"]), float(r["LON"])), "begin": r["BEGIN"], "end": r["END"]})
    return out


_days = {}
def station_days(sid, year, offset_h):
    """{local date: [hourly obs]} for one station-year (empty when NOAA has no file)."""
    key = (sid, year, offset_h)
    if key in _days:
        return _days[key]
    path = ISD / str(year) / f"{sid}.csv"
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        try:
            data = get(FILES.format(year=year, id=sid))
        except Exception:
            data = b""
        path.write_bytes(data if data.startswith(b'"STATION"') else b"")   # empty: no file for that year
    days = {}
    text = path.read_text(errors="replace")
    for r in csv.DictReader(io.StringIO(text)) if text else []:
        t = datetime.fromisoformat(r["DATE"]) + timedelta(hours=offset_h)
        days.setdefault(t.date().isoformat(), []).append(r)
    _days[key] = days
    return days


def summarize(obs):
    temps, winds, wet = [], [], 0
    for r in obs:
        v = (r.get("TMP") or "").split(",")
        if v[0] and v[0] not in ("+9999", "9999") and len(v) > 1 and v[1] in "01459AUPIMCR":
            temps.append(int(v[0]) / 10)
        w = (r.get("WND") or "").split(",")
        if len(w) > 3 and w[3] != "9999":
            winds.append(int(w[3]) / 10 * KN_PER_MS)
        mw = (r.get("MW1") or "").split(",")
        if mw[0].isdigit() and 50 <= int(mw[0]) <= 99:
            wet += 1
    f = lambda x: f"{x:.1f}" if x is not None else ""
    return {"isd_obs": len(obs), "isd_tmax_c": f(max(temps) if temps else None), "isd_tmin_c": f(min(temps) if temps else None),
            "isd_wind_mean_kn": f(sum(winds) / len(winds) if winds else None), "isd_wind_max_kn": f(max(winds) if winds else None),
            "isd_precip_reports": wet}


def era5(lat, lon, start, end):
    path = ERA5 / f"daily_{lat:.4f}_{lon:.4f}_{start}_{end}.json"
    if not path.exists():
        ERA5.mkdir(parents=True, exist_ok=True)
        q = urllib.parse.urlencode({"latitude": lat, "longitude": lon, "start_date": start, "end_date": end,
                                    "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
                                    "wind_speed_unit": "kn", "timezone": "auto"})
        path.write_bytes(get(OPEN_METEO + q))
    d = json.loads(path.read_text())["daily"]
    return {day: {"era5_tmax_c": d["temperature_2m_max"][i], "era5_tmin_c": d["temperature_2m_min"][i],
                  "era5_precip_mm": d["precipitation_sum"][i], "era5_wind_max_kn": d["wind_speed_10m_max"][i]}
            for i, day in enumerate(d["time"])}


def timeline(unit, part, rows, parts):
    """The rows that place `part` of `unit`, in order: its own rows while it existed (parts.csv
    from-to), its parent's before and after."""
    if part == "battalion":
        return [r for r in rows if r["unit"] == unit and r["part"] == "battalion"]
    p = parts[(unit, part)]
    up = timeline(unit, p["parent"], rows, parts)
    own = [r for r in rows if r["unit"] == unit and r["part"] == part and p["from"] <= r["date"] <= p["to"]]
    return [r for r in up if r["date"] < p["from"]] + own + [r for r in up if r["date"] >= p["to"]]


def stays(folder):
    """{(unit, place): set of local dates}, day by day. On each day the unit is wherever its active
    parts are (records/<folder>/parts.csv: each part's parent and dates; none, the whole unit):
    each active part with no active part of its own, and a parent that has rows of its own dated
    since its parts split off (the rest of it, somewhere else). A part is at its last row's place,
    except on the days after a row marked last_day, and in transit: the days a transport
    (KM_PER_DAY) would need to reach its next row's place."""
    places = {r["place"]: (float(r["lat"]), float(r["lon"])) for r in csv.DictReader((folder / "places.csv").open())
              if r["lat"] and r["lon"]}
    rows = sorted(csv.DictReader((folder / "stations.csv").open()), key=lambda r: r["date"])
    pfile = folder / "parts.csv"
    parts = {(r["unit"], r["part"]): r for r in csv.DictReader(pfile.open())} if pfile.exists() else {}
    out = {}

    def place_on(seq, day):
        before = [r for r in seq if r["date"] <= day]
        if not before:
            return None
        a = before[-1]
        if a.get("last_day") == "yes" and day > a["date"]:
            return None
        after = [r for r in seq if r["date"] > day and r["place"] != a["place"]]
        if after:
            b = after[0]
            travel = max(1, math.ceil(km(places[a["place"]], places[b["place"]]) / KM_PER_DAY))
            if day > (date.fromisoformat(b["date"]) - timedelta(days=travel)).isoformat():
                return None
        return a["place"]

    for unit in sorted({r["unit"] for r in rows}):
        urows = [r for r in rows if r["unit"] == unit and r["place"] in places]
        uparts = {p: v for (u, p), v in parts.items() if u == unit}
        d, last = date.fromisoformat(urows[0]["date"]), date.fromisoformat(urows[-1]["date"])
        while d <= last:
            day = d.isoformat()
            active = [p for p, v in uparts.items() if v["from"] <= day < v["to"]]
            children = {uparts[p]["parent"] for p in active}
            here = [timeline(unit, p, urows, parts) for p in active if p not in children] or [timeline(unit, "battalion", urows, parts)]
            for p in children - {"battalion"}:
                start = min(uparts[c]["from"] for c in active if uparts[c]["parent"] == p)
                own = [r for r in urows if r["part"] == p and start <= r["date"] <= day]
                if own:
                    here.append(own + [r for r in timeline(unit, p, urows, parts) if r["date"] > day])
            for seq in here:
                place = place_on(seq, day)
                if place:
                    out.setdefault((unit, place), set()).add(day)
            d += timedelta(days=1)
    return out, places


def main():
    folder = RECORDS / (sys.argv[1] if len(sys.argv) > 1 else "seabees")
    st = stations()
    by_place, places = stays(folder)
    rows = []
    for (unit, place), days in sorted(by_place.items()):
        at = places[place]
        offset = round(at[1] / 15)
        near = sorted(((km(at, s["at"]), s) for s in st), key=lambda x: x[0])
        near = [(d, s) for d, s in near if d <= MAX_KM]
        days = sorted(days)
        e5 = era5(*at, days[0], days[-1])
        for day in days:
            row = {"unit": unit, "place": place, "date": day, **{k: ("" if v is None else v) for k, v in e5.get(day, {}).items()}}
            for d, s in near:
                if not (s["begin"] <= day.replace("-", "") <= s["end"]):
                    continue
                obs = station_days(s["id"], int(day[:4]), offset).get(day, [])
                if len(obs) >= MIN_OBS:
                    row |= {"isd_station": s["id"], "isd_name": s["name"], "isd_km": f"{d:.0f}", **summarize(obs)}
                    break
            row["source"] = "era5" + (f"; isd:{row['isd_station']}/{day[:4]}" if row.get("isd_station") else "")
            rows.append(row)
    fields = ["unit", "place", "date", "era5_tmax_c", "era5_tmin_c", "era5_precip_mm", "era5_wind_max_kn", "isd_station",
              "isd_name", "isd_km", "isd_obs", "isd_tmax_c", "isd_tmin_c", "isd_wind_mean_kn", "isd_wind_max_kn",
              "isd_precip_reports", "source"]
    path = folder / "weather.csv"
    with path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        w.writerows(sorted(rows, key=lambda r: (r["unit"], r["date"], r["place"])))
    observed = sum(1 for r in rows if r.get("isd_station"))
    print(f"{len(rows)} place-days, {observed} with an observing station within {MAX_KM} km -> {rel(path)}")
    for (unit, place), days in sorted(by_place.items(), key=lambda x: min(x[1])):
        got = [r for r in rows if r["unit"] == unit and r["place"] == place and r.get("isd_station")]
        names = sorted({f"{r['isd_name']} ({r['isd_km']} km)" for r in got})
        print(f"  {unit} {place:16} {len(days):4d} days, observed {len(got):4d}: {'; '.join(names)[:110]}")


if __name__ == "__main__":
    main()
