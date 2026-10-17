"""Read the pinned VTB release and write aggregate, reproducible statistics.

This is an analysis script, not a parser/trainer or annotation tool. It never
changes the corpus, emits example sentences, or predicts annotations.
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
import hashlib
import json
from pathlib import Path


# Query forms named in the teacher's spec and Week 2 task, not a parser lexicon.
QUERY_FORMS = (
    "cái", "con", "chiếc", "cuốn", "và", "hoặc", "hay", "đi",
    "ra", "vào", "lên", "xuống", "về", "của", "à", "nhé", "đấy", "nha", "đó",
)
DIRECTION_FORMS = frozenset(("ra", "vào", "lên", "xuống", "về"))


def read_basic_sentences(path: Path):
    """Read integer-ID basic dependency nodes; retain IDs for error reports."""
    sentence, sent_id = [], None
    skipped = Counter()
    for line_no, line in enumerate(path.read_text(encoding="utf-8").splitlines() + [""], 1):
        if not line.strip():
            if sentence:
                if not sent_id:
                    raise ValueError(f"{path.name}:{line_no}: missing sent_id")
                yield sent_id, sentence, dict(skipped)
            sentence, sent_id, skipped = [], None, Counter()
        elif line.startswith("#"):
            if line.startswith("# sent_id = "):
                sent_id = line.split(" = ", 1)[1]
        else:
            cols = line.split("\t")
            if len(cols) != 10:
                raise ValueError(f"{path.name}:{line_no}: expected 10 columns")
            if "-" in cols[0] or "." in cols[0]:
                skipped["multiword" if "-" in cols[0] else "empty_node"] += 1
                continue
            sentence.append({"id": int(cols[0]), "form": cols[1], "upos": cols[3],
                             "head": int(cols[6]), "deprel": cols[7]})


def tree_errors(nodes):
    ids = [n["id"] for n in nodes]
    if ids != list(range(1, len(nodes) + 1)):
        return ["nonconsecutive_ids"]
    by_id = {n["id"]: n for n in nodes}
    errors = set()
    if sum(n["head"] == 0 for n in nodes) != 1:
        errors.add("root_count")
    for node in nodes:
        if (node["head"] == 0) != (node["deprel"] == "root"):
            errors.add("root_label")
        seen, cur = set(), node["id"]
        while cur:
            if cur not in by_id:
                errors.add("invalid_head")
                break
            if cur in seen:
                errors.add("cycle")
                break
            seen.add(cur)
            cur = by_id[cur]["head"]
    return sorted(errors)


def projective_by_crossings(nodes):
    # Include the artificial ROOT edge: an arc spanning the sentence root
    # can violate projectivity even without another crossing non-ROOT edge.
    arcs = [sorted((n["id"], n["head"])) for n in nodes]
    return not any(a < c < b < d or c < a < d < b
                   for i, (a, b) in enumerate(arcs)
                   for c, d in arcs[i + 1:])


def projective_by_descendants(nodes):
    by_id = {n["id"]: n for n in nodes}
    for node in nodes:
        head, dep = node["head"], node["id"]
        for between in range(min(head, dep) + 1, max(head, dep)):
            cur = between
            while cur not in (0, head):
                cur = by_id[cur]["head"]
            if cur != head:
                return False
    return True


def allowed_labels(repo: Path):
    """Read the frozen constant without importing application dependencies."""
    source = repo / "src/vietnlp/interfaces/_common.py"
    for node in ast.parse(source.read_text(encoding="utf-8")).body:
        if isinstance(node, ast.Assign) and any(
            isinstance(t, ast.Name) and t.id == "UD_DEPREL" for t in node.targets
        ):
            return frozenset(ast.literal_eval(node.value.args[0].func.value).split())
    raise ValueError("UD_DEPREL constant not found")


def summarize(path: Path, allowed):
    labels, upos, syllable_lengths, skipped_rows = Counter(), Counter(), Counter(), Counter()
    focus = {word: {"deprel": Counter(), "upos": Counter(),
                    "head_upos": Counter(), "head_deprel": Counter()} for word in QUERY_FORMS}
    nonprojective, invalid, seen_ids = [], [], set()
    di_verbs, di_adjacent, direction, direction_verbs, compound_order = (Counter() for _ in range(5))
    head_pos_pairs, poss_markers, fronted_objects = Counter(), Counter(), Counter()
    adjacent_di_direction = Counter()
    emoticon_count = 0
    compound_reverse_ids = []
    sentence_count, token_count = 0, 0
    for sent_id, nodes, skipped in read_basic_sentences(path):
        if sent_id in seen_ids:
            raise ValueError(f"duplicate sent_id: {sent_id}")
        seen_ids.add(sent_id)
        sentence_count += 1
        token_count += len(nodes)
        skipped_rows.update(skipped)
        errors = tree_errors(nodes)
        if errors:
            invalid.append({"sent_id": sent_id, "reasons": errors})
        else:
            cross = projective_by_crossings(nodes)
            descendants = projective_by_descendants(nodes)
            if cross != descendants:
                raise AssertionError(f"projectivity definitions disagree: {sent_id}")
            if not cross:
                nonprojective.append(sent_id)
        by_id = {n["id"]: n for n in nodes}
        for node in nodes:
            rel, form = node["deprel"], node["form"].lower()
            emoticon_count += node["form"] == ":))"
            following = by_id.get(node["id"] + 1)
            if form == "đi" and following and following["upos"] == "VERB":
                if following["head"] == node["id"]:
                    adjacent_di_direction["di_is_head"] += 1
                elif node["head"] == following["id"]:
                    adjacent_di_direction["following_verb_is_head"] += 1
                else:
                    adjacent_di_direction["no_direct_arc"] += 1
            if rel.split(":", 1)[0] not in allowed:
                raise ValueError(f"unmapped label: {rel}")
            labels[rel] += 1
            upos[node["upos"]] += 1
            syllable_lengths[len(node["form"].split())] += 1
            head = by_id.get(node["head"])
            if form in focus:
                entry = focus[form]
                entry["deprel"][rel] += 1
                entry["upos"][node["upos"]] += 1
                entry["head_upos"][head["upos"] if head else "ROOT"] += 1
                entry["head_deprel"][head["deprel"] if head else "ROOT"] += 1
            if form in DIRECTION_FORMS:
                direction[rel] += 1
                if node["upos"] == "VERB":
                    direction_verbs[rel] += 1
            if head and head["form"].lower() == "đi" and node["upos"] == "VERB" and node["id"] > head["id"]:
                di_verbs[rel] += 1
                if node["id"] == head["id"] + 1:
                    di_adjacent[rel] += 1
            if rel in ("compound:svc", "compound:dir"):
                compound_order[f"{rel}:head_{'left' if node['head'] < node['id'] else 'right'}"] += 1
                if node["head"] > node["id"]:
                    compound_reverse_ids.append({"sent_id": sent_id, "dependent_id": node["id"], "label": rel})
            if head and rel in ("clf", "clf:det"):
                head_pos_pairs[f"{rel}:{head['upos']}->{node['upos']}"] += 1
            if rel == "nmod:poss":
                marked = any(c["head"] == node["id"] and c["form"].lower() == "của"
                             and c["deprel"] == "case" for c in nodes)
                poss_markers["with_cua_case" if marked else "without_cua_case"] += 1
            if head and rel.split(":", 1)[0] == "obj":
                fronted_objects["before_head" if node["id"] < node["head"] else "after_head"] += 1
    return {"sentences": sentence_count, "tokens": token_count,
            "invalid_trees": invalid, "nonprojective_ids": nonprojective,
            "deprels": dict(labels), "upos": dict(upos),
            "form_syllable_lengths": dict(syllable_lengths), "skipped_rows": dict(skipped_rows),
            "focus_forms": focus, "di_forward_verb_children": dict(di_verbs),
            "di_adjacent_verb_children": dict(di_adjacent),
            "di_adjacent_verb_pair_direction": dict(adjacent_di_direction),
            "task_emoticon_occurrences": emoticon_count,
            "direction_forms_deprels": dict(direction), "direction_verb_deprels": dict(direction_verbs),
            "compound_head_order": dict(compound_order), "compound_reverse_ids": compound_reverse_ids,
            "classifier_upos_pairs": dict(head_pos_pairs), "possessive_cua_marker": dict(poss_markers),
            "object_position": dict(fronted_objects)}


def compact(counter):
    return "; ".join(f"`{key}`: {value}" for key, value in sorted(counter.items())) or "0"


def write_reports(out: Path, report):
    out.mkdir(parents=True, exist_ok=True)
    (out / "VTB_COUNTS.json").write_text(
        json.dumps(report, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8")
    splits = report["splits"]
    lines = ["# VTB statistics for the Week 2 design", "", f"VTB commit: `{report['commit']}`.", "",
             "Generated by the [analysis script](../scripts/analyze_vtb.py). These are source-corpus",
             "statistics: no model is run and no annotation is created or changed. Inspecting the",
             "test split here is a corpus inventory required by the task, not model evaluation.", "",
             "## Corpus size and projectivity before projection", "",
             "| Split | Sentences | Word tokens | Invalid trees | Nonprojective trees | Multisyllabic tokens |",
             "|---|---:|---:|---:|---:|---:|"]
    for split, stats in splits.items():
        multi = sum(v for k, v in stats["form_syllable_lengths"].items() if int(k) > 1)
        lines.append(f"| {split} | {stats['sentences']} | {stats['tokens']} | {len(stats['invalid_trees'])} | {len(stats['nonprojective_ids'])} | {multi} |")
    lines += ["", "Projectivity is cross-checked using two definitions: no crossing arcs (including",
              "the artificial ROOT arc), and every token inside an arc is a descendant of its head.",
              "Nonprojective sentence IDs, file hashes and detailed counts are recorded in the",
              "[JSON report](VTB_COUNTS.json). Post-projection trees have not been measured yet.", "",
              "## Forms requested by the task and specification", "",
              "Match each entire word-level FORM case-insensitively. These are statistical",
              "queries, not a lexicon or rules for automatically identifying word senses.", "",
              "| FORM | Train labels and counts | Dev labels and counts | Test labels and counts | Total |",
              "|---|---|---|---|---:|"]
    for word in QUERY_FORMS:
        values = [s["focus_forms"][word]["deprel"] for s in splits.values()]
        total = sum(sum(v.values()) for v in values)
        lines.append(f"| `{word}` | " + " | ".join(compact(v) for v in values) + f" | {total} |")
    lines += ["", "## Serial-verb labels and head direction", "",
              "`đi → VERB` counts only direct dependents with source UPOS VERB that follow",
              "a head whose FORM is đi. It does not count every later verb as a dependent.", "",
              "| Split | đi → later VERB | Labels of ra/vào/lên/xuống/về | Head order of the two compound subtypes |",
              "|---|---|---|---|"]
    for split, stats in splits.items():
        lines.append(f"| {split} | {compact(stats['di_forward_verb_children'])} | {compact(stats['direction_forms_deprels'])} | {compact(stats['compound_head_order'])} |")
    lines += ["", "### Restricted queries reproducing the task counts", "",
              "The following table counts VERB dependents immediately after đi. Directional",
              "forms are restricted to source UPOS VERB. These queries differ from the broader table above.", "",
              "| Split | đi → adjacent VERB | Attachment direction of adjacent đi + VERB | Directional forms with UPOS VERB |",
              "|---|---|---|---|"]
    for split, stats in splits.items():
        lines.append(f"| {split} | {compact(stats['di_adjacent_verb_children'])} | {compact(stats['di_adjacent_verb_pair_direction'])} | {compact(stats['direction_verb_deprels'])} |")
    lines += ["", "### Possessives and object position", "",
              "| Split | nmod:poss with/without a direct của case dependent | obj before/after its head |",
              "|---|---|---|"]
    for split, stats in splits.items():
        lines.append(f"| {split} | {compact(stats['possessive_cua_marker'])} | {compact(stats['object_position'])} |")
    lines += ["", "An obj before its head is a positional observation, not automatically a topic.", "",
              "Occurrences of the exact FORM :)) in VTB: " +
              ", ".join(f"{sp}={s['task_emoticon_occurrences']}" for sp, s in splits.items()) + ".", "",
              "Source UPOS is read only for analysis; it is not a parser feature.", "",
              "Label counts alone do not identify word senses or attachment scope.",
              "Sources, decisions and limitations are documented in [DESIGN.md](../DESIGN.md).", ""]
    (out / "VTB_COUNTS.md").write_text("\n".join(lines), encoding="utf-8", newline="\n")
    labels = sorted({label for stats in splits.values() for label in stats["deprels"]})
    mapping = ["# Mapping VTB labels to UD_DEPREL", "", f"VTB commit: `{report['commit']}`.", "",
               "Inventory of every label observed in train/dev/test before projection.",
               "Take the part before the first colon; every target label is checked against",
               "the interface's UD_DEPREL. A label absent from VTB is not invalid merely",
               "because it is unobserved if the interface still permits it.", "",
               "| VTB label | Output label | Train | Dev | Test | Total |",
               "|---|---|---:|---:|---:|---:|"]
    for label in labels:
        counts = [s["deprels"].get(label, 0) for s in splits.values()]
        mapping.append(f"| `{label}` | `{label.split(':', 1)[0]}` | " + " | ".join(map(str, counts)) + f" | {sum(counts)} |")
    mapping += ["", "Projection adds within-word `dep` arcs; those added arcs are not included",
                "in the source-label counts. Base-label model predictions are not expanded",
                "back into VTB subtypes when producing output.", ""]
    (out / "LABEL_MAPPING.md").write_text("\n".join(mapping), encoding="utf-8", newline="\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads((args.data_dir / "SOURCE.json").read_text(encoding="utf-8-sig"))
    expected = {f["file"]: f["sha256"] for f in manifest["files"]}
    repo = Path(__file__).resolve().parents[3]
    allowed = allowed_labels(repo)
    report = {"commit": manifest["commit"], "source": manifest["repository"], "sha256": {}, "splits": {}}
    for split in ("train", "dev", "test"):
        path = args.data_dir / f"vi_vtb-ud-{split}.conllu"
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if digest != expected[path.name]:
            raise ValueError(f"SHA256 mismatch: {path.name}")
        report["sha256"][path.name] = digest
        stats = summarize(path, allowed)
        report["splits"][split] = stats
        print(f"{split}: {stats['sentences']} sentences, {stats['tokens']} tokens, "
              f"{len(stats['invalid_trees'])} invalid, {len(stats['nonprojective_ids'])} nonprojective")
    write_reports(args.output_dir, report)
    print(f"Reports written to {args.output_dir}")


if __name__ == "__main__":
    main()
