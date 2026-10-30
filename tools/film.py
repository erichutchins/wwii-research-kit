"""Find film of a place and time: the US National Archives' moving images, and YouTube uploads by the archives
listed in records/film/channels.yml. A find is a candidate for records/film/clips.csv, not a row
(records/film/README.md says how a clip is checked and cited).

Commands:
  python3 tools/film.py nara "Palermo 1943" [...]     the National Archives' moving images: catalogue ID, film number,
                                                      production date, title (cite as nara-film:<catalogue ID>)
  python3 tools/film.py shots 75826 [...]              one catalogue item's shot list, date and MP4 link
  python3 tools/film.py search "Palermo 1943" [...]   YouTube search, kept to the listed channels; uploads before 2024
                                                      with the API key (--channel: search each listed channel; --all:
                                                      every result via yt-dlp, unlisted marked "-"); --n 40 per query
  python3 tools/film.py index [--units 3500] [--only CHANNEL_ID]  save every listed channel's uploads (title, date, description) to
                                                      sources/film/index/<channel>.jsonl; 1 unit per 50 videos; resumable
  python3 tools/film.py find "Palermo" "harbor" [--before 1946] [--after 1941] [--tier archive]
                                                      search that saved index locally (all words must appear); free
  python3 tools/film.py meta N5q3UAIkc-o [...]         an upload's description, archive number and captions, cached in
                                                      sources/film/<id>/ (info.json, *.vtt, transcript.txt)

YouTube: with YOUTUBE_API_KEY (environment or the git-ignored .env, as gbooks.py's key) searches and video details go
through the YouTube Data API v3 (10,000 units a day: a search costs 100, a video's details 1); `search --channel` keeps
each query to one listed channel at a time. Captions only come through yt-dlp (`uvx yt-dlp`; the API gives them only
to a video's owner), which YouTube may stop with a bot check: don't get around it; a silent film's shot list is in
its description anyway.
"""
import html
import json
import os
import re
import subprocess
import sys
import urllib.parse
import urllib.request

from records import CACHE, KIT, RECORDS

API = "https://catalog.archives.gov/proxy/v3/records/search"
FILM = CACHE / "film"
ARCHIVE_ID = re.compile(r"FILM ID:\s*[\d.]+|[Ss]tory (?:[Nn]umber|No\.?)\s*[\d/]+|\b\d{2,3}-[A-Z]{2,5}-\d+\b|\bIWM \w+ \d+")


def channels():
    """records/film/channels.yml, read without PyYAML: channel_id -> (name, tier)."""
    out, cur = {}, {}
    for line in (RECORDS / "film" / "channels.yml").read_text(encoding="utf-8").splitlines():
        m = re.match(r"\s*-?\s*(name|channel_id|tier):\s*(.+)$", line)
        if not m:
            continue
        if line.lstrip().startswith("- "):
            cur = {}
        cur[m.group(1)] = m.group(2).strip()
        if "channel_id" in cur and "tier" in cur:
            out[cur["channel_id"]] = (cur.get("name", ""), cur["tier"])
    return out


def nara_get(params):
    url = API + "?" + urllib.parse.urlencode(params)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (wwii-research-kit)"})
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.load(r)["body"]["hits"]["hits"]


def date_of(rec):
    d = (rec.get("productionDates") or [{}])[0]
    return d.get("logicalDate") or str(d.get("year", ""))


def cmd_nara(queries):
    for q in queries:
        hits = nara_get({"q": q, "rows": 50, "typeOfMaterials": "Moving Images"})
        print(f"== {q}: {len(hits)}")
        for h in hits:
            r = h["_source"]["record"]
            print(f"  {r.get('naId'):>9}  {r.get('localIdentifier', ''):<16} {date_of(r):<10}  {r.get('title', '')[:110]}")


def cmd_shots(ids):
    for i in ids:
        r = nara_get({"naId": i})[0]["_source"]["record"]
        objs = [o.get("objectUrl") for o in r.get("digitalObjects") or []]
        print(f"== nara-film:{i}  {r.get('localIdentifier')}  {date_of(r)}\n  {r.get('title')}")
        for shot in re.split(r"(?<=\.)\s*(?=\d+\))", r.get("shotList") or r.get("scopeAndContentNote") or "(no shot list)"):
            print("   ", shot.strip())
        print("  film:", ", ".join(objs) or "not online", "\n  https://catalog.archives.gov/id/" + str(i))


def yt_key():
    key = os.environ.get("YOUTUBE_API_KEY")
    for env in (KIT / ".env", KIT.parent / ".env"):
        if not key and env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                name, _, value = line.partition("=")
                if name.strip() == "YOUTUBE_API_KEY":
                    key = value.strip()
    return key


def yt_api(endpoint, **params):
    url = f"https://www.googleapis.com/youtube/v3/{endpoint}?" + urllib.parse.urlencode({**params, "key": yt_key()})
    with urllib.request.urlopen(urllib.request.Request(url), timeout=60) as r:
        return json.load(r)


def api_search(queries, n, by_channel):
    listed = channels()
    for q in queries:
        found = []
        for cid in (listed if by_channel else [None]):
            params = dict(part="snippet", q=q, type="video", maxResults=min(n, 50), publishedBefore="2024-01-01T00:00:00Z")
            if cid:
                params["channelId"] = cid
            found += yt_api("search", **params).get("items", [])
        kept = [i for i in found if i["snippet"]["channelId"] in listed]
        print(f"== {q}: {len(kept)} of {len(found)} from listed channels")
        for i in kept:
            sn = i["snippet"]
            name, tier = listed[sn["channelId"]]
            print(f"  {tier:<11} {i['id']['videoId']}  {sn['publishedAt'][:10]}  {name[:22]:<22}  {html.unescape(sn['title'])[:90]}")


def ytdlp(*args):
    return subprocess.run(["uvx", "-q", "yt-dlp", *args], capture_output=True, text=True)


def cmd_search(queries, n=40, show_all=False):
    listed = channels()
    for q in queries:
        p = ytdlp("--flat-playlist", "-J", f"ytsearch{n}:{q}")
        if p.returncode:
            print(f"== {q}: yt-dlp failed\n{p.stderr[-400:]}")
            continue
        entries = json.loads(p.stdout).get("entries") or []
        kept = [e for e in entries if show_all or e.get("channel_id") in listed]
        print(f"== {q}: {len(kept)} of {len(entries)} from listed channels" if not show_all else f"== {q}: {len(entries)}")
        for e in kept:
            name, tier = listed.get(e.get("channel_id"), (e.get("channel", ""), "-"))
            dur = e.get("duration") or 0
            print(f"  {tier:<11} {e['id']}  {int(dur) // 60:>3}:{int(dur) % 60:02d}  {name[:22]:<22}  {(e.get('title') or '')[:90]}")


def vtt_text(path):
    out, stamp, last = [], None, ""
    for line in path.read_text(encoding="utf-8").splitlines():
        m = re.match(r"(\d\d:\d\d:\d\d)\.\d+ -->", line)
        if m:
            stamp = m.group(1)
            continue
        if not line.strip() or line.startswith(("WEBVTT", "Kind:", "Language:")) or "<c>" in line:
            continue
        t = re.sub(r"<[^>]+>", "", line).strip()
        if t and t != last:
            out.append(f"{stamp} {t}")
            last = t
    return "\n".join(out)


def cmd_meta(ids):
    listed = channels()
    for vid in ids:
        d = FILM / vid
        d.mkdir(parents=True, exist_ok=True)
        info = d / f"{vid}.info.json"
        if not info.exists() and yt_key():
            items = yt_api("videos", part="snippet,contentDetails", id=vid).get("items", [])
            if items:
                sn = items[0]["snippet"]
                info.write_text(json.dumps({"id": vid, "title": html.unescape(sn["title"]), "channel": sn["channelTitle"], "channel_id": sn["channelId"],
                                            "upload_date": sn["publishedAt"][:10].replace("-", ""), "duration": items[0]["contentDetails"]["duration"],
                                            "description": sn.get("description", ""), "via": "YouTube Data API"}, indent=1), encoding="utf-8")
                ytdlp("--skip-download", "--write-auto-subs", "--write-subs", "--sub-langs", "en-orig,en", "--sub-format", "vtt",
                      "-o", str(d / "%(id)s.%(ext)s"), f"https://youtu.be/{vid}")      # captions, if YouTube allows
        if not info.exists():
            p = ytdlp("--skip-download", "--write-info-json", "--write-auto-subs", "--write-subs", "--sub-langs", "en-orig,en",
                      "--sub-format", "vtt", "-o", str(d / "%(id)s.%(ext)s"), f"https://youtu.be/{vid}")
            if not info.exists():
                print(f"== {vid}: yt-dlp failed\n{p.stderr[-400:]}")
                continue
        j = json.loads(info.read_text(encoding="utf-8"))
        name, tier = listed.get(j.get("channel_id"), (j.get("channel"), "not listed: not a source"))
        desc = j.get("description") or ""
        print(f"== {vid}  {j.get('title')}\n  {name} ({tier}); uploaded {j.get('upload_date')}; {j.get('duration')} s")
        print("  archive number:", ", ".join(sorted(set(ARCHIVE_ID.findall(desc)))) or "none found in the description")
        print("  " + desc.strip().replace("\n", "\n  ")[:3000])
        vtts = sorted(d.glob("*.vtt"))
        if vtts:
            text = vtt_text(vtts[0])
            (d / "transcript.txt").write_text(text, encoding="utf-8")
            print(f"  captions ({vtts[0].name}; automatic captions guess at names):\n    " + text.replace("\n", "\n    "))
        else:
            print("  no captions (a silent film: the shot list is the text)")


def cmd_index(units, only=None):
    """Each listed channel's uploads playlist (UU + the channel ID's tail) into sources/film/index/<channel>.jsonl,
    50 videos a page at 1 unit a page. <channel>.state holds the next page token, so a stopped run resumes."""
    listed = channels()
    d = FILM / "index"
    d.mkdir(parents=True, exist_ok=True)
    spent = 0
    for cid, (name, tier) in listed.items():
        if only and cid != only:
            continue
        out, state = d / f"{cid}.jsonl", d / f"{cid}.state"
        token = state.read_text().strip() if state.exists() else ""
        if state.exists() and not token:
            print(f"{name}: indexed already ({sum(1 for _ in out.open(encoding='utf-8'))} uploads)")
            continue
        n = 0
        with out.open("a", encoding="utf-8") as f:
            while spent < units:
                params = dict(part="snippet,contentDetails", playlistId="UU" + cid[2:], maxResults=50)
                if token:
                    params["pageToken"] = token
                r = yt_api("playlistItems", **params)
                spent += 1
                for it in r.get("items", []):
                    sn, cd = it["snippet"], it["contentDetails"]
                    f.write(json.dumps({"id": cd["videoId"], "date": (cd.get("videoPublishedAt") or sn["publishedAt"])[:10],
                                        "title": html.unescape(sn["title"]), "description": sn.get("description", ""),
                                        "channel_id": cid}, ensure_ascii=False) + "\n")
                    n += 1
                token = r.get("nextPageToken", "")
                state.write_text(token)
                if not token:
                    break
        print(f"{name} ({tier}): +{n} uploads; {'done' if not token else 'stopped at the unit limit'}")
        if spent >= units:
            break
    print(f"{spent} units spent")


def cmd_find(words, before, after, tier):
    listed = channels()
    shown, seen = 0, set()
    for jl in sorted((FILM / "index").glob("*.jsonl")):
        name, t = listed.get(jl.stem, (jl.stem, "-"))
        if tier and t != tier:
            continue
        for line in jl.open(encoding="utf-8"):
            v = json.loads(line)
            if v["id"] in seen:
                continue
            seen.add(v["id"])
            text = (v["title"] + " " + v["description"]).lower()
            if all(w.lower() in text for w in words) and (not before or v["date"][:4] < before) and (not after or v["date"][:4] >= after):
                num = ", ".join(sorted(set(ARCHIVE_ID.findall(v["description"]))))[:40]
                print(f"  {t:<11} {v['id']}  {v['date']}  {name[:16]:<16} {v['title'][:80]}  [{num}]")
                shown += 1
    print(f"{shown} match(es)")


def main(argv):
    if len(argv) < 2 or argv[0] not in ("nara", "shots", "search", "meta", "index", "find"):
        sys.exit(__doc__)
    cmd, rest = argv[0], argv[1:]
    n = 40
    if "--n" in rest:
        i = rest.index("--n")
        n = int(rest[i + 1])
        del rest[i:i + 2]
    opts = {}
    for flag in ("--units", "--before", "--after", "--tier", "--only"):
        if flag in rest:
            i = rest.index(flag)
            opts[flag] = rest[i + 1]
            del rest[i:i + 2]
    if cmd == "index":
        return cmd_index(int(opts.get("--units", 3500)), opts.get("--only"))
    if cmd == "find":
        return cmd_find(rest, opts.get("--before"), opts.get("--after"), opts.get("--tier"))
    show_all, by_channel = "--all" in rest, "--channel" in rest
    rest = [a for a in rest if a not in ("--all", "--channel")]
    if cmd == "search" and yt_key() and not show_all:
        return api_search(rest, n, by_channel)
    {"nara": cmd_nara, "shots": cmd_shots, "meta": cmd_meta}.get(cmd, lambda q: cmd_search(q, n, show_all))(rest)


if __name__ == "__main__":
    main(sys.argv[1:])
