"""Inspect the 2WikiMultiHopQA dev split (SCRUM-13).

AC1: prints the field list with types, the question count per type, and one
     complete example per question type.
AC2: over the full dev set, counts questions with a non-empty evidences_id per
     type; then draws a stratified random sample of 50 questions (fixed seed)
     and classifies how each evidence relation is expressed.

Usage:
    python scripts/inspect_2wiki.py              # AC1 + AC2
    python scripts/inspect_2wiki.py --wikidata   # also look up each relation
                                                 # label on Wikidata (network) and
                                                 # write docs/notes/2wiki-relation-map.json

Run scripts/download_2wiki.py first.
"""

import argparse
import json
import random
import re
import time
import urllib.error
from datetime import date
import urllib.parse
import urllib.request
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEV_PATH = ROOT / "data" / "raw" / "2wiki" / "dev.json"
RELATION_MAP_PATH = ROOT / "docs" / "notes" / "2wiki-relation-map.json"
WIKIDATA_API = "https://www.wikidata.org/w/api.php"

# Order used in the authors' README; the first two types get 13, the rest 12.
TYPES = ["comparison", "inference", "compositional", "bridge_comparison"]
SAMPLE_SIZES = {"comparison": 13, "inference": 13, "compositional": 12, "bridge_comparison": 12}
SEED = 694

# The README says comparison / bridge_comparison questions have evidences_id
# only when a relation is one of these.
COUNTRY_RELATIONS = {"country", "country of origin", "country of citizenship"}

PID = re.compile(r"^P\d+$")
QID = re.compile(r"^Q\d+$")


def describe(v):
    """Short type description of a JSON value; small mixed lists shown positionally."""
    if v is None:
        return "null"
    if isinstance(v, bool):
        return "bool"
    if isinstance(v, (int, float, str)):
        return type(v).__name__
    if isinstance(v, dict):
        return "dict"
    if isinstance(v, list):
        parts = [describe(e) for e in v]
        if not parts:
            return "list (empty)"
        if len(set(parts)) == 1:
            return f"list[{parts[0]}]"
        if len(parts) <= 4:
            return "[" + ", ".join(parts) + "]"
        return "list[" + " | ".join(sorted(set(parts))) + "]"
    return type(v).__name__


def print_fields(data):
    print("== Field list (types observed across all dev records) ==")
    fields = []
    for rec in data:
        for k in rec:
            if k not in fields:
                fields.append(k)
    for k in fields:
        present = sum(1 for r in data if k in r)
        kinds = Counter(describe(r[k]) for r in data if k in r)
        print(f"  {k}  (present in {present:,}/{len(data):,})")
        for kind, n in kinds.most_common():
            print(f"      {n:>6,}  {kind}")


def print_type_counts(data):
    print("\n== Questions per type ==")
    counts = Counter(r["type"] for r in data)
    for t in TYPES:
        print(f"  {t:<18} {counts[t]:>6,}")
    others = set(counts) - set(TYPES)
    for t in sorted(others):
        print(f"  {t:<18} {counts[t]:>6,}  (not in README)")
    print(f"  {'total':<18} {len(data):>6,}")


def print_examples(data):
    print("\n== One complete example per type (first occurrence in dev.json) ==")
    for t in TYPES:
        rec = next(r for r in data if r["type"] == t)
        print(f"\n--- {t} ---")
        print(json.dumps(rec, indent=2, ensure_ascii=False))


def relation_form(rel):
    return "P-id" if PID.match(rel) else "label"


def question_form(rec):
    """How relations are expressed across evidences and evidences_id of one question."""
    forms = {relation_form(r) for _, r, _ in rec["evidences"] + rec["evidences_id"]}
    if forms == {"P-id", "label"}:
        return "both"
    return forms.pop() if forms else "none"


def print_coverage(data):
    print("\n== evidences_id coverage, full dev set ==")
    print(f"  {'type':<18} {'total':>6} {'non-empty':>9} {'pct':>7}  "
          f"{'w/ country rel':>14} {'country rel, empty':>18} {'non-empty, no country rel':>25}")
    for t in TYPES:
        recs = [r for r in data if r["type"] == t]
        has = [r for r in recs if r["evidences_id"]]
        country = [r for r in recs if any(rel in COUNTRY_RELATIONS for _, rel, _ in r["evidences"])]
        country_empty = sum(1 for r in country if not r["evidences_id"])
        has_no_country = sum(1 for r in has
                             if not any(rel in COUNTRY_RELATIONS for _, rel, _ in r["evidences"]))
        print(f"  {t:<18} {len(recs):>6,} {len(has):>9,} {100 * len(has) / len(recs):>6.1f}%  "
              f"{len(country):>14,} {country_empty:>18,} {has_no_country:>25,}")

    print("\n  Consistency of non-empty evidences_id with evidences (full dev set):")
    has = [r for r in data if r["evidences_id"]]
    rel_mismatch = sum(1 for r in has
                       if [x[1] for x in r["evidences"]] != [x[1] for x in r["evidences_id"]])
    slots = Counter()
    for r in has:
        for s, _, o in r["evidences_id"]:
            slots["subject is QID" if QID.match(s) else f"subject = {s!r}"] += 1
            slots["object is QID" if QID.match(o) else f"object = {o!r}"] += 1
    print(f"    questions whose relation sequence differs: {rel_mismatch}")
    for k, n in slots.most_common():
        print(f"    {k}: {n:,}")

    all_rels = Counter(rel for r in data for _, rel, _ in r["evidences"] + r["evidences_id"])
    pids = sorted(r for r in all_rels if PID.match(r))
    print(f"\n  Distinct relation strings in full dev set: {len(all_rels)}; "
          f"matching ^P[0-9]+$: {len(pids)} {pids}")
    return all_rels


def print_extra_checks(data):
    """Checks that bear on ontology design, over the full dev set."""
    print("\n== Other checks, full dev set ==")
    print("  Evidence triples per question, by type:")
    for t in TYPES:
        n = Counter(len(r["evidences"]) for r in data if r["type"] == t)
        print(f"    {t:<18} " + ", ".join(f"{k} triples: {v:,}" for k, v in sorted(n.items())))

    subj_total = subj_title = 0
    for r in data:
        titles = {title for title, _ in r["context"]}
        for s, _, _ in r["evidences"]:
            subj_total += 1
            subj_title += s in titles
    print(f"  Evidence subjects equal to a context paragraph title: "
          f"{subj_title:,}/{subj_total:,} ({100 * subj_title / subj_total:.1f}%)")


def stratified_sample(data):
    rng = random.Random(SEED)
    sample = []
    for t in TYPES:
        pool = sorted((r for r in data if r["type"] == t), key=lambda r: r["_id"])
        sample.extend(rng.sample(pool, SAMPLE_SIZES[t]))
    return sample


def print_sample(sample):
    print(f"\n== Stratified sample: {len(sample)} questions, seed={SEED}, sizes={SAMPLE_SIZES} ==")
    for t in TYPES:
        recs = [r for r in sample if r["type"] == t]
        forms = Counter(question_form(r) for r in recs)
        triples = sum(len(r["evidences"]) for r in recs)
        id_triples = sum(len(r["evidences_id"]) for r in recs)
        with_id = sum(1 for r in recs if r["evidences_id"])
        rels = Counter(rel for r in recs for _, rel, _ in r["evidences"])
        print(f"\n  {t}  (n={len(recs)})")
        print(f"    relation form per question: "
              + ", ".join(f"{k}={forms.get(k, 0)}" for k in ("P-id", "label", "both")))
        print(f"    evidence triples: {triples}; evidences_id triples: {id_triples}; "
              f"questions with non-empty evidences_id: {with_id}/{len(recs)}")
        print(f"    distinct relations ({len(rels)}): "
              + ", ".join(f"{k} ({n})" for k, n in sorted(rels.items())))
    print("\n  Sampled _id values:")
    for t in TYPES:
        print(f"    {t}: " + " ".join(r["_id"] for r in sample if r["type"] == t))


def wikidata_search(label):
    q = urllib.parse.urlencode({"action": "wbsearchentities", "search": label,
                                "type": "property", "language": "en",
                                "limit": 20, "format": "json"})
    req = urllib.request.Request(f"{WIKIDATA_API}?{q}",
                                 headers={"User-Agent": "cmsi694-scrum13-inspect/0.1"})
    for attempt in range(5):
        try:
            with urllib.request.urlopen(req) as r:
                return json.load(r).get("search", [])
        except urllib.error.HTTPError as e:
            if e.code != 429 or attempt == 4:
                raise
            time.sleep(int(e.headers.get("Retry-After", 5)) + 1)


def wikidata_lookup(labels):
    """Exact English label/alias match of each relation string against Wikidata properties.

    Returns {relation: (pid, en_label, match, variant)} using label matches only:
    match is "exact_en" (English label), "en_variant" (label in an en-* variant
    only, named in variant), or "none". Aliases are printed but never mapped.
    """
    print("\n== Wikidata property lookup (network; wbsearchentities, type=property) ==")
    print("  'label' = relation string equals the property's English label;")
    print("  'alias' = equals one of its English aliases only. All exact matches listed;")
    print("  only English-variant matches count, and a variant other than 'en' is shown.")
    results = {}
    for label in sorted(labels):
        hits = wikidata_search(label)
        time.sleep(2)  # stay under Wikidata's anonymous rate limit
        exact = [h for h in hits
                 if h["match"]["text"].lower() == label.lower()
                 and h["match"]["type"] in ("label", "alias")
                 and h["match"].get("language", "").split("-")[0] == "en"]
        exact.sort(key=lambda h: (h["match"]["type"] != "label", h["match"]["language"] != "en"))
        if exact:
            matches = "; ".join(
                f"{h['id']} {h['match']['type']}"
                + (f"[{h['match']['language']}]" if h["match"]["language"] != "en" else "")
                + f" (en label={h.get('label')!r})"
                for h in exact)
            print(f"  {label:<24} {matches}")
        else:
            top = f"{hits[0]['id']} {hits[0].get('label')!r}" if hits else "no results"
            print(f"  {label:<24} none (top hit: {top})")

        labels_only = [h for h in exact
                       if h["match"]["type"] == "label" and h["match"]["text"] == label]
        if labels_only:
            h = labels_only[0]
            lang = h["match"]["language"]
            results[label] = (h["id"], h.get("label"),
                              "exact_en" if lang == "en" else "en_variant",
                              None if lang == "en" else lang)
        else:
            results[label] = (None, None, "none", None)
    return results


def write_relation_map(data, results):
    """Write docs/notes/2wiki-relation-map.json: one entry per relation in evidences."""
    types_by_rel = {}
    counts = Counter()
    for r in data:
        for _, rel, _ in r["evidences"]:
            counts[rel] += 1
            types_by_rel.setdefault(rel, set()).add(r["type"])
    entries = []
    for rel in sorted(counts):
        pid, en_label, match, variant = results[rel]
        entries.append({
            "relation": rel,
            "pid": pid,
            "wikidata_label": en_label,
            "match": match,
            "variant": variant,
            "types": [t for t in TYPES if t in types_by_rel[rel]],
            "count": counts[rel],
        })
    out = {
        "lookup_date": date.today().isoformat(),
        "endpoint": WIKIDATA_API,
        "query": {"action": "wbsearchentities", "type": "property", "language": "en"},
        "source": "data/raw/2wiki/dev.json",
        "notes": ("pid is set only when the relation string equals a property label in "
                  "English (match=exact_en) or an English variant (match=en_variant, "
                  "variant names it); alias-only matches are not mapped. count is the "
                  "number of triples in the evidences field across the full dev set."),
        "summary": dict(Counter(e["match"] for e in entries)),
        "relations": entries,
    }
    RELATION_MAP_PATH.write_text(json.dumps(out, indent=2, ensure_ascii=False) + "\n")
    print(f"\n  Wrote {RELATION_MAP_PATH.relative_to(RELATION_MAP_PATH.parents[2])}: "
          f"{len(entries)} relations, {out['summary']}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--wikidata", action="store_true",
                        help="look up each distinct relation label on Wikidata (network)")
    args = parser.parse_args()

    with open(DEV_PATH) as f:
        data = json.load(f)
    print(f"Loaded {DEV_PATH.relative_to(DEV_PATH.parents[3])}: {len(data):,} questions\n")

    # AC1
    print_fields(data)
    print_type_counts(data)
    print_examples(data)

    # AC2
    all_rels = print_coverage(data)
    print_extra_checks(data)
    print_sample(stratified_sample(data))
    if args.wikidata:
        write_relation_map(data, wikidata_lookup(all_rels))


if __name__ == "__main__":
    main()
