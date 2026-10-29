"""Score one run's results (SCRUM-19, SCRUM-33).

    python scripts/score.py --run-dir runs/ontology-v2/smoke10
    python scripts/score.py --run-dir runs/ontology-v2/study50 --results-tag r2
    python scripts/score.py --condition baseline --subset smoke10

--condition C --subset S is shorthand for --run-dir runs/C/S. In a run
directory <run>/<subset>, score.py reads results.jsonl (or, with
--results-tag TAG, results-<TAG>.jsonl) and writes
    <run>/<subset>/scores.json                  per-question scores and aggregates
                                                (scores-<TAG>.json with a tag)
    docs/results/<run>-<subset>-scores.md       short summary
                                                (<run>-<subset>-<TAG>-scores.md)
for example docs/results/ontology-v2-smoke10-scores.md. --out-dir DIR writes
both files, under the same names, into DIR instead. If either file exists,
score.py refuses and names it, unless --overwrite is given.

The results file must match the sha256 of the last completed query run in the
run manifest that has the same results tag (no tag when the record has none),
or of a later renormalize run of that file.

Answer metrics follow the authors' official evaluation script,
2wikimultihop_evaluate_v1.1.py in https://github.com/Alab-NII/2wikimultihop
(commit 13800e5be57df1b4040b9b1588c6c811779e69e9): normalize_answer,
f1_score, exact_match_score, and the alias handling in update_answer and eval,
which take the best score over the gold answer and the aliases and demonyms of
its answer_id from id_aliases.json. The official script reports only the
alias-aware scores; em and f1 here are the same functions against the gold
answer alone, and em_alias and f1_alias are the official scores.

The scored answer is predicted_answer, the normalized model output. A row
"relied on the fallback" when predicted_answer differs from
predicted_answer_raw with surrounding whitespace stripped.

Retrieval recall is the share of a question's gold paragraphs (from
supporting_facts) that appear in retrieved_paragraph_ids.

Confidence intervals are percentile bootstrap intervals over questions: 1,000
resamples with replacement, random.Random(694) seeded afresh for each group,
bounds at sorted means [25] and [974].

Standard library only.
"""

import argparse
import hashlib
import json
import random
import re
import string
import subprocess
import sys
from collections import Counter
from pathlib import Path

import freeze_subset

ROOT = Path(__file__).resolve().parent.parent
RUNS_DIR = ROOT / "runs"
RESULTS_DOCS_DIR = ROOT / "docs" / "results"
ALIASES_PATH = ROOT / "data" / "raw" / "2wiki" / "id_aliases.json"
OFFICIAL_SCRIPT = (
    "https://github.com/Alab-NII/2wikimultihop/blob/"
    "13800e5be57df1b4040b9b1588c6c811779e69e9/2wikimultihop_evaluate_v1.1.py"
)
METRICS = ["em", "em_alias", "f1", "f1_alias", "retrieval_recall"]
# The characters allowed in --results-tag, as in run_condition.py.
LABEL = re.compile(r"[a-z0-9-]+")
BOOTSTRAP_RESAMPLES = 1000
BOOTSTRAP_SEED = 694
TYPES = ["inference", "compositional", "comparison", "bridge_comparison"]


# ------------------------------------------- official v1.1 answer metrics


def normalize_answer(s: str) -> str:
    """Official normalize_answer: lower, drop punctuation, articles, extra spaces."""

    def remove_articles(text):
        return re.sub(r"\b(a|an|the)\b", " ", text)

    def white_space_fix(text):
        return " ".join(text.split())

    def remove_punc(text):
        exclude = set(string.punctuation)
        return "".join(ch for ch in text if ch not in exclude)

    return white_space_fix(remove_articles(remove_punc(s.lower())))


def f1_score(prediction: str, ground_truth: str) -> float:
    """Official f1_score, returning F1 only."""
    normalized_prediction = normalize_answer(prediction)
    normalized_ground_truth = normalize_answer(ground_truth)
    special = ["yes", "no", "noanswer"]
    if normalized_prediction in special and normalized_prediction != normalized_ground_truth:
        return 0.0
    if normalized_ground_truth in special and normalized_prediction != normalized_ground_truth:
        return 0.0
    prediction_tokens = normalized_prediction.split()
    ground_truth_tokens = normalized_ground_truth.split()
    common = Counter(prediction_tokens) & Counter(ground_truth_tokens)
    num_same = sum(common.values())
    if num_same == 0:
        return 0.0
    precision = num_same / len(prediction_tokens)
    recall = num_same / len(ground_truth_tokens)
    return (2 * precision * recall) / (precision + recall)


def exact_match_score(prediction: str, ground_truth: str) -> float:
    return float(normalize_answer(prediction) == normalize_answer(ground_truth))


def best(metric, prediction: str, golds) -> float:
    """Best score over several gold strings, as in the official update_answer."""
    return max(metric(prediction, gold) for gold in golds)


# ------------------------------------------------------------------ inputs


def sha256_of(path: Path) -> str:
    return freeze_subset.sha256_of(path)


def load_question_meta() -> dict[str, dict]:
    """answer and answer_id for every frozen question, keyed by _id."""
    meta = {}
    for q_file, _ in freeze_subset.FILE_NAMES.values():
        with (freeze_subset.PROCESSED_DIR / q_file).open(encoding="utf-8") as f:
            for line in f:
                q = json.loads(line)
                meta[q["_id"]] = {"answer": q["answer"], "answer_id": q["answer_id"]}
    return meta


def load_aliases(path: Path, wanted: set[str]) -> dict[str, list[str]]:
    """Aliases plus demonyms for the wanted Q_ids, as the official eval reads them."""
    aliases = {}
    with path.open(encoding="utf-8") as f:
        for line in f:
            entry = json.loads(line)
            if entry["Q_id"] in wanted:
                aliases[entry["Q_id"]] = sorted(set(entry["aliases"] + entry["demonyms"]))
    return aliases


def label(value: str) -> str:
    """argparse type for --results-tag."""
    if not LABEL.fullmatch(value):
        raise argparse.ArgumentTypeError(
            f"{value!r}: use lowercase letters, digits and hyphens only"
        )
    return value


def suffix(results_tag: str | None) -> str:
    return "" if results_tag is None else f"-{results_tag}"


def output_paths(run_dir: Path, results_tag: str | None = None,
                 out_dir: Path | None = None) -> dict[str, Path]:
    """Results file read, and scores and summary files written, for one run."""
    tag = suffix(results_tag)
    scores_dir = run_dir if out_dir is None else out_dir
    docs_dir = RESULTS_DOCS_DIR if out_dir is None else out_dir
    return {
        "results": run_dir / f"results{tag}.jsonl",
        "scores": scores_dir / f"scores{tag}.json",
        "summary": docs_dir / f"{run_dir.parent.name}-{run_dir.name}{tag}-scores.md",
    }


def refuse_existing(paths: list[Path], overwrite: bool) -> None:
    existing = [path for path in paths if path.exists()]
    if existing and not overwrite:
        raise SystemExit(
            "Refusing to overwrite " + ", ".join(display(path) for path in existing)
            + "; pass --overwrite to replace, or --out-dir to write elsewhere."
        )


def display(path: Path) -> str:
    """A path relative to the repo when it is inside it, else absolute."""
    path = path.resolve()
    return str(path.relative_to(ROOT)) if path.is_relative_to(ROOT) else str(path)


def expected_sha256(manifest: dict, results_tag: str | None) -> tuple[dict, str]:
    """The last completed query run for this results tag, and the sha256 its file should have."""
    def same_tag(record: dict) -> bool:
        return record.get("status") == "completed" and record.get("results_tag") == results_tag

    query_runs = [r for r in manifest.get("query", []) if same_tag(r)]
    if not query_runs:
        raise SystemExit(f"The run manifest has no completed query run with results tag {results_tag}")
    query_run = query_runs[-1]
    expected = query_run["results_sha256"]
    renormalized = [r for r in manifest.get("renormalize", []) if same_tag(r)]
    if renormalized and renormalized[-1]["started_at"] > query_run["started_at"]:
        expected = renormalized[-1]["results_sha256_after"]
    return query_run, expected


# ----------------------------------------------------------------- scoring


def score_row(row: dict, gold_answer: str, aliases: list[str]) -> dict:
    prediction = row["predicted_answer"]
    golds = [gold_answer, *aliases]
    gold_ids = set(row["gold_paragraph_ids"])
    if not gold_ids:
        raise ValueError(f"{row['question_id']}: no gold paragraphs")
    retrieved = row["retrieved_paragraph_ids"]
    return {
        "question_id": row["question_id"],
        "type": row["type"],
        "predicted_answer": prediction,
        "gold_answer": gold_answer,
        "em": exact_match_score(prediction, gold_answer),
        "em_alias": best(exact_match_score, prediction, golds),
        "f1": f1_score(prediction, gold_answer),
        "f1_alias": best(f1_score, prediction, golds),
        "retrieval_recall": len(gold_ids & set(retrieved)) / len(gold_ids),
        "paragraphs_retrieved": len(retrieved),
        "fallback_used": prediction != row["predicted_answer_raw"].strip(),
    }


def mean(values: list[float]) -> float:
    return sum(values) / len(values)


def bootstrap_ci(values: list[float]) -> list[float]:
    """Percentile bootstrap 95% interval of the mean; see the module docstring."""
    rng = random.Random(BOOTSTRAP_SEED)
    n = len(values)
    means = sorted(
        mean([values[rng.randrange(n)] for _ in range(n)]) for _ in range(BOOTSTRAP_RESAMPLES)
    )
    return [means[int(0.025 * BOOTSTRAP_RESAMPLES)], means[int(0.975 * BOOTSTRAP_RESAMPLES) - 1]]


def aggregate(scores: list[dict]) -> dict:
    out = {"n": len(scores)}
    for metric in METRICS:
        values = [s[metric] for s in scores]
        out[metric] = {"mean": mean(values), "ci95": bootstrap_ci(values)}
    out["mean_paragraphs_retrieved"] = mean([s["paragraphs_retrieved"] for s in scores])
    out["fallback_rows"] = sum(s["fallback_used"] for s in scores)
    return out


def score_rows(rows: list[dict], meta: dict[str, dict], aliases: dict[str, list[str]]) -> dict:
    scores = []
    for row in rows:
        q = meta[row["question_id"]]
        if q["answer"] != row["gold_answer"]:
            raise ValueError(f"{row['question_id']}: gold answer differs from the subset file")
        scores.append(score_row(row, q["answer"], aliases.get(q["answer_id"], [])))
    types = [t for t in TYPES if any(s["type"] == t for s in scores)]
    types += sorted({s["type"] for s in scores} - set(types))
    return {
        "overall": aggregate(scores),
        "by_type": {t: aggregate([s for s in scores if s["type"] == t]) for t in types},
        "fallback_question_ids": [s["question_id"] for s in scores if s["fallback_used"]],
        "per_question": scores,
    }


# ------------------------------------------------------------------ output


def git_commit() -> dict:
    def git(*args: str) -> str:
        return subprocess.run(
            ["git", *args], cwd=ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()

    return {"commit": git("rev-parse", "HEAD"), "dirty": bool(git("status", "--porcelain"))}


def pct(value: float) -> str:
    return f"{100 * value:.1f}"


def markdown(report: dict) -> str:
    p = report["provenance"]
    lines = [
        f"# Scores: {report['run']}, {report['subset']}"
        + (f", results tag {report['results_tag']}" if report["results_tag"] else ""),
        "",
        "Written by `scripts/score.py`; full per-question scores are in "
        f"`{p['scores_file']}` (git-ignored).",
        "",
        "| Item | Value |",
        "|---|---|",
        f"| Results file | `{p['results_file']}` |",
        f"| Results sha256 | `{p['results_sha256']}` |",
        f"| Query run | commit `{p['query_run']['commit']}`, ended {p['query_run']['ended_at']} |",
        f"| Aliases | `{p['aliases_file']}`, sha256 `{p['aliases_sha256']}` |",
        f"| Scorer commit | `{p['scorer_git']['commit']}`"
        + (" (dirty)" if p["scorer_git"]["dirty"] else "") + " |",
        f"| Answer metrics | official 2WikiMultiHopQA v1.1 evaluation ([script]({OFFICIAL_SCRIPT})) |",
        "",
        "Scores are percentages. Brackets give the bootstrap 95% confidence interval "
        f"({BOOTSTRAP_RESAMPLES:,} resamples, seed {BOOTSTRAP_SEED}). EM and F1 compare "
        "with the gold answer only; the alias columns also accept the aliases and "
        "demonyms of the answer entity, as the official script does.",
        "",
        "| Group | n | EM | EM (aliases) | F1 | F1 (aliases) | Retrieval recall |",
        "|---|---|---|---|---|---|---|",
    ]
    groups = [("overall", report["overall"])] + list(report["by_type"].items())
    for name, agg in groups:
        cells = [
            f"{pct(agg[m]['mean'])} [{pct(agg[m]['ci95'][0])}, {pct(agg[m]['ci95'][1])}]"
            for m in METRICS
        ]
        lines.append(f"| {name} | {agg['n']} | " + " | ".join(cells) + " |")
    o = report["overall"]
    lines += [
        "",
        f"Mean paragraphs retrieved per question: {o['mean_paragraphs_retrieved']:.1f}.",
        "",
        f"Rows that relied on the answer-normalization fallback: {o['fallback_rows']} of {o['n']}"
        + (
            " (" + ", ".join(f"`{q}`" for q in report["fallback_question_ids"]) + ")."
            if report["fallback_question_ids"] else "."
        ),
        "",
        "## Per question",
        "",
        "| # | Question ID | Type | Predicted | Gold | EM | EM (aliases) | F1 | F1 (aliases) | Recall | Retrieved |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for n, s in enumerate(report["per_question"], start=1):
        lines.append(
            f"| {n} | `{s['question_id']}` | {s['type']} | {s['predicted_answer']} | "
            f"{s['gold_answer']} | {s['em']:.0f} | {s['em_alias']:.0f} | {s['f1']:.2f} | "
            f"{s['f1_alias']:.2f} | {s['retrieval_recall']:.2f} | {s['paragraphs_retrieved']} |"
        )
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--run-dir", type=Path, help="the run directory, e.g. runs/ontology-v2/smoke10")
    parser.add_argument("--condition", help="with --subset: shorthand for --run-dir runs/<condition>/<subset>")
    parser.add_argument("--subset")
    parser.add_argument("--results-tag", type=label, default=None,
                        help="score results-<TAG>.jsonl instead of results.jsonl")
    parser.add_argument("--out-dir", type=Path, default=None,
                        help="write the scores and summary files into this directory instead")
    parser.add_argument("--overwrite", action="store_true", help="replace existing output files")
    args = parser.parse_args(argv)
    if args.run_dir is not None and (args.condition or args.subset):
        parser.error("give either --run-dir or --condition and --subset, not both")
    if args.run_dir is None and not (args.condition and args.subset):
        parser.error("give --run-dir, or both --condition and --subset")

    run_dir = (args.run_dir if args.run_dir is not None else RUNS_DIR / args.condition / args.subset)
    run_dir = run_dir.resolve()
    paths = output_paths(run_dir, args.results_tag, args.out_dir and args.out_dir.resolve())
    results_path, scores_path, md_path = paths["results"], paths["scores"], paths["summary"]
    manifest_path = run_dir / "run_manifest.json"
    if not results_path.exists():
        raise SystemExit(f"No results: {display(results_path)}")
    refuse_existing([scores_path, md_path], args.overwrite)
    results_sha256 = sha256_of(results_path)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    query_run, expected = expected_sha256(manifest, args.results_tag)
    if results_sha256 != expected:
        raise SystemExit(f"{display(results_path)} does not match the sha256 recorded in the run manifest")

    with results_path.open(encoding="utf-8") as f:
        rows = [json.loads(line) for line in f]
    meta = load_question_meta()
    aliases = load_aliases(ALIASES_PATH, {meta[r["question_id"]]["answer_id"] for r in rows})
    scored = score_rows(rows, meta, aliases)

    report = {
        "condition": manifest.get("condition", args.condition),
        "subset": manifest.get("subset", run_dir.name),
        "run": run_dir.parent.name,
        "run_dir": display(run_dir),
        "results_tag": args.results_tag,
        "provenance": {
            "results_file": display(results_path),
            "results_sha256": results_sha256,
            "scores_file": display(scores_path),
            "query_run": {
                "started_at": query_run["started_at"],
                "ended_at": query_run["ended_at"],
                "commit": query_run["git"]["commit"],
                "config_sha256": query_run["config_sha256"],
            },
            "aliases_file": display(ALIASES_PATH),
            "aliases_sha256": sha256_of(ALIASES_PATH),
            "official_script": OFFICIAL_SCRIPT,
            "bootstrap": {"resamples": BOOTSTRAP_RESAMPLES, "seed": BOOTSTRAP_SEED,
                          "bounds": "sorted resample means [25] and [974]"},
            "scorer_git": git_commit(),
        },
        **scored,
    }
    scores_path.parent.mkdir(parents=True, exist_ok=True)
    md_path.parent.mkdir(parents=True, exist_ok=True)
    scores_path.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    md_path.write_text(markdown(report), encoding="utf-8")
    print(f"Wrote {display(scores_path)} and {display(md_path)}")
    o = report["overall"]
    print("  ".join(f"{m} {pct(o[m]['mean'])}" for m in METRICS), f"fallback {o['fallback_rows']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
