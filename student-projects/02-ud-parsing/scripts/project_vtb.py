"""Measure VTB projection and replay the static oracle on projective train trees."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

from pandera.errors import SchemaError

from vietnlp.interfaces.ud import (
    DependencyParse, UDToken, is_single_rooted_tree, validate_dependency_parse,
)
from vietnlp.linguistics.ud_parser import (
    PROJECTION_VERSION, TRANSITION_VERSION,
    ParserState, ProjectedSentence, StaticOracle,
    _is_projective_tree, _punctuation_glue_targets,
    map_deprel, project_sentence, read_conllu,
)


def validate_projection(gold: ProjectedSentence) -> None:
    """Check every projected tree against the frozen schema and tree invariant."""
    tree = DependencyParse(
        sent_id=gold.metadata["sent_id"],
        tokens=tuple(
            UDToken(token.id - 1, token.form, token.upos, token.head, token.deprel)
            for token in gold.tokens
        ),
        source="real",
    )
    validate_dependency_parse(tree)
    if not is_single_rooted_tree(tree):
        raise ValueError("projected tree is not single-rooted and acyclic")


def replay_oracle(gold: ProjectedSentence) -> int:
    """Require exact reconstruction with n SHIFTs and n ARCs within 2n steps."""
    state = ParserState(tuple(token.form for token in gold.tokens))
    oracle = StaticOracle(gold)
    n = len(gold.tokens)
    shifts = 0
    for _ in range(2 * n):
        if state.is_terminal:
            raise ValueError("oracle terminated before 2n actions")
        action = oracle.next_action(state)
        state.apply(action)
        shifts += action.kind == "SHIFT"
    if not state.is_terminal or shifts != n:
        raise ValueError("oracle did not terminate with n SHIFTs and n ARCs")
    if state.heads != [None] + [token.head for token in gold.tokens]:
        raise ValueError("oracle heads differ from gold")
    if state.labels != [None] + [token.deprel for token in gold.tokens]:
        raise ValueError("oracle labels differ from gold")
    return 2 * n


def summarize(path: Path, *, run_oracle: bool) -> dict:
    """Project one split; keep oracle failures separate from train exclusions."""
    sentences = read_conllu(path.read_text(encoding="utf-8"))
    stats = {
        "sentences": len(sentences), "source_word_tokens": 0,
        "source_nonprojective_trees": 0, "projected_sentences": 0,
        "syllable_tokens": 0, "internal_dep_arcs": 0,
        "punctuation_glued": {"trailing": 0, "opening": 0},
        "punctuation_retained": 0, "source_punct_forms": {'"': 0, "(": 0},
        "invalid_projected_trees": [], "nonprojective_ids": [],
    }
    oracle_stats = {"attempted": 0, "passed": 0, "actions": 0, "failures": []}
    excluded = []
    seen_ids = set()
    for source in sentences:
        sent_id = source.metadata.get("sent_id")
        if not sent_id or sent_id in seen_ids:
            raise ValueError(f"{path.name}: missing or duplicate sent_id: {sent_id!r}")
        seen_ids.add(sent_id)
        stats["source_word_tokens"] += len(source.tokens)
        stats["source_nonprojective_trees"] += not _is_projective_tree(source.tokens)
        base_labels = {token.id: map_deprel(token.deprel) for token in source.tokens}
        for token in source.tokens:
            if base_labels[token.id] == "punct" and token.form in stats["source_punct_forms"]:
                stats["source_punct_forms"][token.form] += 1
        try:
            gold = project_sentence(source)
            validate_projection(gold)
        except (ValueError, SchemaError) as exc:
            entry = {"sent_id": sent_id, "reason": "invalid_projection",
                     "error_type": type(exc).__name__}
            stats["invalid_projected_trees"].append(entry)
            if run_oracle:
                excluded.append(entry)
            print(f"{sent_id}: invalid projection: {exc}", file=sys.stderr)
            continue

        targets = _punctuation_glue_targets(source, base_labels)
        deleted = {word for word, ids in gold.word_to_syllables.items() if not ids}
        if set(targets) != deleted:
            raise ValueError(f"{sent_id}: punctuation targets disagree with projection")
        internal = sum(max(0, len(ids) - 1) for ids in gold.word_to_syllables.values())
        if len(gold.tokens) != len(source.tokens) - len(deleted) + internal:
            raise ValueError(f"{sent_id}: projected token accounting failed")
        stats["projected_sentences"] += 1
        stats["syllable_tokens"] += len(gold.tokens)
        stats["internal_dep_arcs"] += internal
        for word, target in targets.items():
            direction = "opening" if target > word else "trailing"
            stats["punctuation_glued"][direction] += 1
        stats["punctuation_retained"] += sum(
            base_labels[token.id] == "punct" and token.id not in deleted
            for token in source.tokens
        )
        if not gold.is_projective:
            stats["nonprojective_ids"].append(sent_id)
            if run_oracle:
                excluded.append({"sent_id": sent_id, "reason": "nonprojective_after_projection"})
            continue
        if run_oracle:
            oracle_stats["attempted"] += 1
            try:
                oracle_stats["actions"] += replay_oracle(gold)
            except ValueError as exc:
                oracle_stats["failures"].append(
                    {"sent_id": sent_id, "reason": "oracle_replay_failed",
                     "error_type": type(exc).__name__}
                )
                print(f"{sent_id}: oracle failure: {exc}", file=sys.stderr)
            else:
                oracle_stats["passed"] += 1
    if run_oracle:
        stats["train_excluded"] = excluded
        stats["oracle"] = oracle_stats
    return stats


def write_reports(output_dir: Path, report: dict) -> None:
    """Write reproducible aggregate counts and excluded sentence IDs."""
    output_dir.mkdir(parents=True, exist_ok=True)
    (output_dir / "PROJECTION_COUNTS.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    lines = [
        "# VTB projection measurements", "",
        f"VTB commit: `{report['commit']}`.",
        f"Projection: `{report['projection_version']}`.",
        f"Transitions: `{report['transition_version']}`.", "",
        "Generated by [project_vtb.py](../scripts/project_vtb.py). File SHA-256 values",
        "are verified against the pinned [source inventory](VTB_COUNTS.json).",
        "These are deterministic data-preparation measurements, not model scores.", "",
        "## Counts after projection", "",
        "| Split | Sentences | Syllable tokens | Internal dep arcs | Trailing glued | Opening glued | Punct retained | Invalid trees | Nonprojective trees |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for split in ("train", "dev", "test"):
        stats = report["splits"][split]
        glued = stats["punctuation_glued"]
        lines.append(
            f"| {split} | {stats['sentences']:,} | {stats['syllable_tokens']:,} | "
            f"{stats['internal_dep_arcs']:,} | {glued['trailing']:,} | {glued['opening']:,} | "
            f"{stats['punctuation_retained']:,} | {len(stats['invalid_projected_trees'])} | "
            f"{len(stats['nonprojective_ids'])} |"
        )
    train = report["splits"]["train"]
    oracle = train["oracle"]
    lines += [
        "", "Counts include every successfully projected tree, including non-projective",
        "trees. Internal `dep` arcs count later syllables attached to their word anchor;",
        "they exclude source `dep` relations. Trailing/opening counts mean punctuation",
        "glued backward/forward respectively, including alternating straight quotes.",
        "Retained punctuation includes roots and marks without a target on their chosen side.",
        "Every projected tree is checked against the frozen schema and single-rooted-tree",
        "validator. Projectivity includes the artificial ROOT arc.", "",
        "## Source punctuation check", "",
        "Exact word FORMs with base label `punct`, before projection:", "",
        '| Split | Straight double quote (`"`) | Opening parenthesis (`(`) |',
        "|---|---:|---:|",
    ]
    for split in ("train", "dev", "test"):
        forms = report["splits"][split]["source_punct_forms"]
        lines.append('| {} | {} | {} |'.format(split, forms['"'], forms['(']))
    lines += [
        "", "## Train exclusions and oracle replay", "",
        f"Excluded train sentences: **{len(train['train_excluded'])}**.",
        f"Oracle attempted: **{oracle['attempted']:,}**; passed: **{oracle['passed']:,}**; "
        f"failures: **{len(oracle['failures'])}**; actions: **{oracle['actions']:,}**.", "",
        "Replay requires exact gold heads and labels, legal transitions and exactly",
        "n SHIFTs plus n ARCs per sentence. Oracle failures are bugs, never exclusions.",
        "Dev/test sentences remain available for later evaluation, including non-projective trees.", "",
        "| Excluded train sent_id | Reason |", "|---|---|",
    ]
    for entry in train["train_excluded"]:
        lines.append(f"| `{entry['sent_id']}` | `{entry['reason']}` |")
    lines += [
        "", "All non-projective IDs, invalid-tree diagnostics and file hashes are in",
        "[PROJECTION_COUNTS.json](PROJECTION_COUNTS.json). No corpus rows are included.", "",
        "## Reproduce", "", "From the repository root with `src` on `PYTHONPATH`:", "",
        "```text",
        "python student-projects/02-ud-parsing/scripts/project_vtb.py --data-dir <VTB_DIR> --output-dir student-projects/02-ud-parsing/analysis",
        "```", "",
    ]
    (output_dir / "PROJECTION_COUNTS.md").write_text(
        "\n".join(lines), encoding="utf-8", newline="\n",
    )


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    inventory_path = Path(__file__).resolve().parents[1] / "analysis/VTB_COUNTS.json"
    inventory = json.loads(inventory_path.read_text(encoding="utf-8"))
    report = {
        "commit": inventory["commit"], "source": inventory["source"],
        "projection_version": PROJECTION_VERSION, "transition_version": TRANSITION_VERSION,
        "sha256": {}, "splits": {},
    }
    for split in ("train", "dev", "test"):
        path = args.data_dir / f"vi_vtb-ud-{split}.conllu"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != inventory["sha256"][path.name]:
            raise ValueError(f"SHA-256 mismatch: {path.name}")
        report["sha256"][path.name] = digest
        stats = summarize(path, run_oracle=split == "train")
        report["splits"][split] = stats
        print(
            f"{split}: {stats['sentences']} sentences, {stats['syllable_tokens']} syllables, "
            f"{len(stats['invalid_projected_trees'])} invalid, "
            f"{len(stats['nonprojective_ids'])} nonprojective", flush=True,
        )
    write_reports(args.output_dir, report)
    oracle = report["splits"]["train"]["oracle"]
    print(f"Train oracle: {oracle['passed']}/{oracle['attempted']} passed, "
          f"{len(oracle['failures'])} failures")
    return int(
        bool(oracle["failures"])
        or any(stats["invalid_projected_trees"] for stats in report["splits"].values())
    )


if __name__ == "__main__":
    raise SystemExit(main())
