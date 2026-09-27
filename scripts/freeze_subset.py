"""Freeze the type-balanced 2WikiMultiHopQA question subsets and corpora (SCRUM-15).

Orders the dev split deterministically, takes the first 10 and 20 questions
(smoke10, smoke20) and the first 50 (study50), and writes each subset's questions and its
deduplicated paragraph corpus as JSON Lines under data/processed/2wiki_subset/.
The committed manifest, data/subsets/manifest.json, records the question ID
lists, counts, and the sha256 of every processed file; it holds no question or
paragraph text.

Ordering:
  1. Group questions by type and sort each group by _id.
  2. With one random.Random(SEED), shuffle the groups in TYPE_ORDER.
  3. Interleave round-robin in TYPE_ORDER, one question per type per round;
     types that run out drop out of the rotation.
Every prefix is therefore as balanced as possible, and each smaller subset is a
prefix of every larger one.

Usage:
    python scripts/freeze_subset.py           # write data/processed and manifest
    python scripts/freeze_subset.py --check   # regenerate in a temp dir, compare

Run scripts/download_2wiki.py first. Standard library only.
"""

import argparse
import hashlib
import json
import random
import re
import sys
import tempfile
from collections import Counter, defaultdict
from pathlib import Path

from download_2wiki import EXPECTED_SHA256

ROOT = Path(__file__).resolve().parent.parent
DEV_PATH = ROOT / "data" / "raw" / "2wiki" / "dev.json"
PROCESSED_DIR = ROOT / "data" / "processed" / "2wiki_subset"
MANIFEST_PATH = ROOT / "data" / "subsets" / "manifest.json"

SEED = 694
TYPE_ORDER = ["inference", "compositional", "comparison", "bridge_comparison"]
SUBSETS = {
    "smoke10": {
        "size": 10,
        "counts": {"inference": 3, "compositional": 3, "comparison": 2, "bridge_comparison": 2},
    },
    "smoke20": {
        "size": 20,
        "counts": {"inference": 5, "compositional": 5, "comparison": 5, "bridge_comparison": 5},
    },
    "study50": {
        "size": 50,
        "counts": {"inference": 13, "compositional": 13, "comparison": 12, "bridge_comparison": 12},
    },
}
FILE_NAMES = {
    "smoke10": ("questions_smoke10.jsonl", "corpus_smoke10.jsonl"),
    "smoke20": ("questions_smoke20.jsonl", "corpus_smoke20.jsonl"),
    "study50": ("questions_50.jsonl", "corpus_50.jsonl"),
}
# Sentences in dev.json carry no leading or trailing whitespace.
JOIN_RULE = 'text = " ".join(sentences)'
ID_SCHEME = 'id = "p_" + sha1(title + "\\x1f" + text).hexdigest()[:16], UTF-8'
PARAGRAPH_ID = re.compile(r"^p_[0-9a-f]{16}$")


def sha256_of(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def paragraph_id(title: str, text: str) -> str:
    return "p_" + hashlib.sha1(f"{title}\x1f{text}".encode("utf-8")).hexdigest()[:16]


def order_questions(dev: list[dict]) -> list[dict]:
    groups = defaultdict(list)
    for question in dev:
        groups[question["type"]].append(question)
    if set(groups) != set(TYPE_ORDER):
        raise SystemExit(f"Unexpected question types: {sorted(groups)}")
    rng = random.Random(SEED)
    for qtype in TYPE_ORDER:
        groups[qtype].sort(key=lambda q: q["_id"])
        rng.shuffle(groups[qtype])
    ordered, position = [], 0
    while len(ordered) < len(dev):
        for qtype in TYPE_ORDER:
            if position < len(groups[qtype]):
                ordered.append(groups[qtype][position])
        position += 1
    return ordered


def build_paragraph_index(dev: list[dict]) -> dict[str, tuple[str, str]]:
    """Map every paragraph ID in dev.json to (title, text); fail on collision."""
    index = {}
    for question in dev:
        for title, sentences in question["context"]:
            text = " ".join(sentences)
            pid = paragraph_id(title, text)
            if index.setdefault(pid, (title, text)) != (title, text):
                raise SystemExit(f"Paragraph ID collision: {pid}")
    return index


def build_subset(questions: list[dict]) -> tuple[list[dict], list[dict], list[str]]:
    """Return question records, the corpus in first-seen order, and problems."""
    records, corpus, seen, problems = [], [], set(), []
    for q in questions:
        context_ids, by_title = [], defaultdict(list)
        for title, sentences in q["context"]:
            text = " ".join(sentences)
            pid = paragraph_id(title, text)
            context_ids.append(pid)
            by_title[title].append(pid)
            if pid not in seen:
                seen.add(pid)
                corpus.append({"id": pid, "title": title, "text": text})
        gold_ids = []
        for title in dict.fromkeys(t for t, _ in q["supporting_facts"]):
            matches = list(dict.fromkeys(by_title.get(title, [])))
            if not matches:
                problems.append(f"{q['_id']}: supporting title not in context: {title!r}")
            elif len(matches) > 1:
                problems.append(f"{q['_id']}: supporting title matches {len(matches)} paragraphs: {title!r}")
            gold_ids.extend(pid for pid in matches if pid not in gold_ids)
        records.append({
            "_id": q["_id"],
            "type": q["type"],
            "question": q["question"],
            "answer": q["answer"],
            "answer_id": q["answer_id"],
            "context_paragraph_ids": list(dict.fromkeys(context_ids)),
            "gold_paragraph_ids": gold_ids,
        })
    return records, corpus, problems


def write_jsonl(path: Path, rows: list[dict]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def generate(out_dir: Path) -> tuple[dict, dict]:
    """Write processed files into out_dir; return the manifest and a report."""
    dev_sha = sha256_of(DEV_PATH)
    if dev_sha != EXPECTED_SHA256["dev.json"]:
        raise SystemExit(f"dev.json sha256 {dev_sha} does not match the recorded value.")
    dev = json.loads(DEV_PATH.read_text(encoding="utf-8"))

    index = build_paragraph_index(dev)
    ordered = order_questions(dev)
    out_dir.mkdir(parents=True, exist_ok=True)

    manifest = {
        "dataset": "2WikiMultiHopQA dev (data_ids_april7)",
        "dev_json_sha256": dev_sha,
        "seed": SEED,
        "type_rotation_order": TYPE_ORDER,
        "ordering": (
            "group by type; sort each group by _id; shuffle groups in rotation "
            "order with one random.Random(seed); interleave round-robin"
        ),
        "paragraph_join_rule": JOIN_RULE,
        "paragraph_id_scheme": ID_SCHEME,
        "subsets": {},
    }
    report = {"problems": [], "corpora": {}}
    for name, spec in SUBSETS.items():
        questions = ordered[: spec["size"]]
        counts = Counter(q["type"] for q in questions)
        assert dict(counts) == spec["counts"], (name, dict(counts))
        records, corpus, problems = build_subset(questions)
        assert all(PARAGRAPH_ID.match(p["id"]) for p in corpus)
        report["problems"] += [f"{name}: {p}" for p in problems]
        report["corpora"][name] = corpus

        q_file, c_file = FILE_NAMES[name]
        write_jsonl(out_dir / q_file, records)
        write_jsonl(out_dir / c_file, corpus)
        manifest["subsets"][name] = {
            "question_ids": [q["_id"] for q in questions],
            "type_counts": {t: counts[t] for t in TYPE_ORDER},
            "paragraph_count": len(corpus),
            "gold_paragraph_count": len({p for r in records for p in r["gold_paragraph_ids"]}),
            "files": {
                q_file: sha256_of(out_dir / q_file),
                c_file: sha256_of(out_dir / c_file),
            },
        }

    # Each smaller subset is a prefix of every larger one, in questions and corpus.
    names = sorted(SUBSETS, key=lambda n: SUBSETS[n]["size"])
    for i, small in enumerate(names):
        for large in names[i + 1:]:
            small_q = manifest["subsets"][small]["question_ids"]
            assert manifest["subsets"][large]["question_ids"][: len(small_q)] == small_q
            small_c = [p["id"] for p in report["corpora"][small]]
            large_c = [p["id"] for p in report["corpora"][large]]
            assert large_c[: len(small_c)] == small_c

    report["dev_paragraphs"] = len(index)
    titles = defaultdict(set)
    for title, text in index.values():
        titles[title].add(text)
    report["dev_titles_multi_text"] = sum(len(t) > 1 for t in titles.values())
    for name, corpus in report["corpora"].items():
        counts = Counter(p["title"] for p in corpus)
        report[f"{name}_titles_multi_text"] = sorted(t for t, n in counts.items() if n > 1)
    return manifest, report


def dump_manifest(manifest: dict) -> str:
    return json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"


def print_report(manifest: dict, report: dict) -> None:
    print(f"dev.json sha256 OK: {manifest['dev_json_sha256']}")
    print(f"dev.json: {report['dev_paragraphs']} unique paragraphs, no ID collisions")
    print(f"dev.json: {report['dev_titles_multi_text']} titles map to more than one distinct text")
    for name, subset in manifest["subsets"].items():
        corpus = report["corpora"][name]
        words = sum(len(p["text"].split()) for p in corpus) / len(corpus)
        print(
            f"{name}: {len(subset['question_ids'])} questions {subset['type_counts']}, "
            f"{subset['paragraph_count']} paragraphs (mean {words:.1f} words), "
            f"{subset['gold_paragraph_count']} gold paragraphs"
        )
        print(f"{name}: titles with more than one distinct text: {report[name + '_titles_multi_text']}")
    print(f"Gold mapping problems: {len(report['problems'])}")
    for problem in report["problems"]:
        print(f"  {problem}")


def check() -> int:
    committed = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory() as tmp:
        manifest, report = generate(Path(tmp))
    print_report(manifest, report)
    failures = []
    if dump_manifest(manifest) != dump_manifest(committed):
        for key in manifest:
            if manifest[key] != committed.get(key):
                failures.append(f"manifest field differs: {key}")
        failures += [f"manifest field missing now: {k}" for k in committed if k not in manifest]
    for name, subset in committed["subsets"].items():
        for file_name, digest in subset["files"].items():
            on_disk = PROCESSED_DIR / file_name
            if not on_disk.exists():
                failures.append(f"missing {on_disk.relative_to(ROOT)}")
            elif sha256_of(on_disk) != digest:
                failures.append(f"{on_disk.relative_to(ROOT)} differs from manifest")
    print()
    for name, subset in committed["subsets"].items():
        regenerated = manifest["subsets"].get(name, {})
        same_ids = regenerated.get("question_ids") == subset["question_ids"]
        print(f"{name}: question IDs {'match' if same_ids else 'DIFFER'}")
        for file_name, digest in subset["files"].items():
            same = regenerated.get("files", {}).get(file_name) == digest
            print(f"{name}: {file_name} sha256 {'match' if same else 'DIFFERS'} ({digest})")
    if failures:
        print("\nCHECK FAILED")
        for failure in failures:
            print(f"  {failure}")
        return 1
    print("\nCHECK PASSED: regenerated output and data/processed match the manifest")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="regenerate in a temp dir and compare")
    args = parser.parse_args()
    if args.check:
        return check()
    manifest, report = generate(PROCESSED_DIR)
    MANIFEST_PATH.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_PATH.write_text(dump_manifest(manifest), encoding="utf-8")
    print_report(manifest, report)
    print(f"\nWrote {PROCESSED_DIR.relative_to(ROOT)}/ and {MANIFEST_PATH.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
