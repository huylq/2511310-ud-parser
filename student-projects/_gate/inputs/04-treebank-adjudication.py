"""Gate input loader for Project 4 (Treebank Curation & Adjudication).

Builds `(sent_id, system_a_tokens, system_b_tokens)` triples from the
PROVISIONAL gold seed (as "system A") and its deliberately-perturbed
counterpart (as "system B") -- see `tests/fixtures/treebank/PROVISIONAL.md`.
A minimal CoNLL-U reader is duplicated here (not imported from
`tests/test_fixture_gold_treebank_seed.py`) to keep this loader
self-contained and independent of the test suite's internal layout.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from vietnlp.interfaces.ud import UDToken  # noqa: E402

TREEBANK_DIR = REPO_ROOT / "tests" / "fixtures" / "treebank"


def _parse_conllu(path: Path) -> dict[str, list[UDToken]]:
    sentences: dict[str, list[UDToken]] = {}
    sent_id = None
    tokens: list[UDToken] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("# sent_id ="):
            sent_id = line.split("=", 1)[1].strip()
        elif line.startswith("#"):
            continue
        elif line.strip() == "":
            if sent_id is not None:
                sentences[sent_id] = tokens
            sent_id, tokens = None, []
        else:
            idx, form, _lemma, upos, _xpos, _feats, head, deprel, _deps, _misc = line.split("\t")
            tokens.append(UDToken(idx=int(idx) - 1, form=form, upos=upos, head=int(head), deprel=deprel))
    return sentences


def build_inputs() -> list[tuple[str, list[UDToken], list[UDToken]]]:
    system_a = _parse_conllu(TREEBANK_DIR / "gold_treebank_seed.conllu")
    system_b = _parse_conllu(TREEBANK_DIR / "system_b_perturbed.conllu")
    return [(sent_id, system_a[sent_id], system_b[sent_id]) for sent_id in system_a]
