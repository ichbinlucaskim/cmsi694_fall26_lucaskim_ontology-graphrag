"""Cached, rate-limited reads from the Wikidata API (SCRUM-17).

Every response is stored under data/raw/wikidata/ (git-ignored) as
    {"fetched_at": "YYYY-MM-DD", "url": ..., "response": ...}
and served from there on later calls, so a rerun makes no network calls.
With offline=True a cache miss raises instead of fetching.

Rate-limit handling follows scripts/inspect_2wiki.py: a User-Agent header, a
2 s pause after every network request, and up to five attempts on HTTP 429,
waiting Retry-After + 1 s.

Standard library only.
"""

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CACHE_DIR = ROOT / "data" / "raw" / "wikidata"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"
USER_AGENT = "cmsi694-scrum17-ontology/0.1"
PAUSE_S = 2
BATCH = 50  # wbgetentities accepts up to 50 IDs per request


class CacheMiss(RuntimeError):
    pass


def _get(params: dict) -> tuple[str, dict]:
    url = f"{WIKIDATA_API}?{urllib.parse.urlencode({**params, 'format': 'json'})}"
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                body = json.load(r)
            time.sleep(PAUSE_S)  # stay under Wikidata's anonymous rate limit
            if "error" in body:
                raise RuntimeError(f"Wikidata API error for {url}: {body['error']}")
            return url, body
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(int(e.headers.get("Retry-After", 5)) + 1)
    raise AssertionError("unreachable")


def _path(kind: str, item_id: str) -> Path:
    return CACHE_DIR / kind / f"{item_id}.json"


def _read(kind: str, item_id: str) -> dict | None:
    path = _path(kind, item_id)
    return json.loads(path.read_text(encoding="utf-8")) if path.exists() else None


def _write(kind: str, item_id: str, url: str, response: dict) -> dict:
    record = {"fetched_at": date.today().isoformat(), "url": url, "response": response}
    path = _path(kind, item_id)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(record, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                    encoding="utf-8")
    return record


# wbgetentities props per cache kind: "entities" keeps claims (for properties,
# whose constraints we read); "labels" keeps only labels and descriptions (for
# classes, whose full claims can be large).
ENTITY_PROPS = {"entities": "labels|descriptions|claims", "labels": "labels|descriptions"}


def get_entities(ids, kind: str = "entities", offline: bool = False) -> dict[str, dict]:
    """Cached wbgetentities records, one cache file per ID; returns {id: record}.

    A batch response is split so that each file holds {"entities": {id: ...}},
    the shape a single-ID request returns.
    """
    ids = sorted(set(ids))
    missing = [i for i in ids if _read(kind, i) is None]
    if missing and offline:
        raise CacheMiss(f"{kind}: {len(missing)} IDs not cached, e.g. {missing[:5]}")
    for start in range(0, len(missing), BATCH):
        chunk = missing[start:start + BATCH]
        url, body = _get({"action": "wbgetentities", "ids": "|".join(chunk),
                          "props": ENTITY_PROPS[kind], "languages": "en"})
        for item_id in chunk:
            _write(kind, item_id, url, {"entities": {item_id: body["entities"][item_id]}})
    return {i: _read(kind, i) for i in ids}


def get_claims(qids, pid: str, offline: bool = False) -> dict[str, dict]:
    """Cached wbgetclaims responses for one property; returns {qid: record}.

    Cached under claims_<pid>/, e.g. claims_P31/ for instance of.
    """
    kind = f"claims_{pid}"
    out = {}
    for qid in sorted(set(qids)):
        record = _read(kind, qid)
        if record is None:
            if offline:
                raise CacheMiss(f"{kind}: {qid} not cached")
            url, body = _get({"action": "wbgetclaims", "entity": qid, "property": pid})
            record = _write(kind, qid, url, body)
        out[qid] = record
    return out


def claim_targets(record: dict, pid: str) -> list[str]:
    """Item IDs that a cached wbgetclaims record gives as values, skipping deprecated ones."""
    return sorted({
        c["mainsnak"]["datavalue"]["value"]["id"]
        for c in record["response"].get("claims", {}).get(pid, [])
        if c.get("rank") != "deprecated" and "datavalue" in c["mainsnak"]
    })


def fetched_dates(kinds=None) -> list[str]:
    """Sorted distinct fetched_at dates over the cache (or the given cache kinds)."""
    dirs = [CACHE_DIR / k for k in kinds] if kinds else [d for d in CACHE_DIR.iterdir() if d.is_dir()]
    return sorted({json.loads(f.read_text(encoding="utf-8"))["fetched_at"]
                   for d in dirs if d.exists() for f in d.glob("*.json")})


def entity(record: dict) -> dict:
    """The single entity inside a cached wbgetentities record."""
    (value,) = record["response"]["entities"].values()
    return value


def label(record: dict) -> str | None:
    return entity(record).get("labels", {}).get("en", {}).get("value")


def description(record: dict) -> str | None:
    return entity(record).get("descriptions", {}).get("en", {}).get("value")
